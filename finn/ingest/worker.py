"""Drain the ledger one step at a time: plan the step's runs, claim them under a lease, work outside the
claim (4 at a time; read in batches of 20), and complete each run only if its lease still holds.

Statuses: done, pending, superseded (a newer revision of the filing replaced it), parked (no_key, quota, terms), blocked (can't tell whether it applies while an
input is parked), not_yet (XBRL lags; dead as no_xbrl 60 days after the filing), degraded (a fallback model answered:
re-asked fresh with a key, an hour apart, at most twice), dead (not_pdf and too_large at once; anything else after 5
tries, counted at claim, so a worker that crashes counts too). A model step checks for a key before it fetches anything.

Planning reads only events whose inputs were written since the step last planned them; a change to the step's own
code (its version, prompt, schema or model) plans every event again.

A run is worked only against the inputs it was planned for. If one has moved since (another drain is re-asking a
degraded read), the claim is given back and the run waits a minute: worked now, tier would say "not read", and when the
re-ask answered the same nothing would run it again.
A batch whose reply can't be read is split in halves until the filing that breaks it is alone, so only that filing
counts the try; the other 19 are read.
"""
import datetime as dt, json, time
from concurrent.futures import ThreadPoolExecutor
from .. import classify, llm
from ..sources import pdf
from . import steps, store

MAX_ATTEMPTS, QUOTA_WAIT, NO_XBRL_DAYS, MAX_REASKS = store.MAX_ATTEMPTS, 3600, 60, 2
MOVED_WAIT = 60   # a run whose inputs moved under it is looked at again after this
WAITING_WAIT = 600   # sizing waiting on an earlier quarter's results looks again after this
NOT_YET_WAIT = (900, 6 * 3600)   # a lagging filing is read again after a quarter of its age, 15 minutes to 6 hours
PLANNED = {"events": 0}   # events read by plan, for the eval: a quiet drain should read none

class Missing(Exception):
    code = "missing_from_batch"

def plan(db, step):
    """Create, or reset after a fingerprint change, this step's run for every event whose inputs are settled."""
    n, code = 0, step.code()
    full = store.meta(db, f"code:{step.name}") != code
    evs = store.latest(db) if full else store.changed(db, step.name, step.inputs)
    PLANNED["events"] += len(evs)
    for ev in evs:
        outs = store.runs_of(db, ev)
        if any(i not in outs or outs[i]["status"] == "pending" for i in step.inputs):
            continue
        a = step.applies(json.loads(ev["payload"]), outs)
        fp = step.fp(outs, a)
        if step.name in outs and outs[step.name]["fp"] == fp:
            if any(outs[i]["seq"] > outs[step.name]["seq"] for i in step.inputs):
                store.touch(db, ev, step.name)   # an input was rewritten the same: don't read this event again
            continue
        store.set_run(db, ev, step.name, fp, "blocked" if a is None else "pending" if a else "done")
        n += 1
    store.meta(db, f"code:{step.name}", code)
    return n

def unpark(db, now):
    if llm.has_key():
        db.execute("UPDATE runs SET status='pending' WHERE status='parked' AND error='no_key'")
        db.execute("UPDATE runs SET status='pending', error='degraded' WHERE status='degraded' AND attempts<=? AND not_before<=?",
                   (MAX_REASKS, now))   # re-asked fresh; the first run was attempt 1
        if llm.paid_terms():
            db.execute("UPDATE runs SET status='pending' WHERE status='parked' AND error='terms'")
    db.execute("UPDATE runs SET status='pending' WHERE status='parked' AND error='quota' AND not_before<=?", (now,))
    db.execute("UPDATE runs SET status='pending' WHERE status='not_yet' AND not_before<=?", (now,))   # error stays not_yet: the retry skips NSE's cache

def outcome(e, r, x, now):
    code = getattr(e, "code", None) or type(e).__name__
    if isinstance(e, steps.NotYet):
        filed = dt.date.fromisoformat(str(e))
        late = dt.date.fromtimestamp(now) > filed + dt.timedelta(days=NO_XBRL_DAYS)
        age = now - dt.datetime.combine(filed, dt.time()).timestamp()
        wait = min(NOT_YET_WAIT[1], max(NOT_YET_WAIT[0], age / 4))   # about 250 reads over 60 days, not one every drain
        return dict(status="dead", error="no_xbrl") if late else dict(status="not_yet", error="not_yet", refund=True, not_before=now + wait)
    if isinstance(e, steps.Waiting):   # an earlier quarter's results are still being read: no try counted
        return dict(status="pending", error="waiting", refund=True, not_before=now + WAITING_WAIT)
    if isinstance(e, llm.LLMError) and code in ("no_key", "quota", "terms"):
        return dict(status="parked", error=code, refund=True, not_before=now + QUOTA_WAIT if code == "quota" else 0)
    if isinstance(e, pdf.FetchError) and code in ("not_pdf", "too_large"):
        return dict(status="dead", error=code)
    if r["attempts"] + 1 >= MAX_ATTEMPTS:   # r was read before the claim counted this attempt
        return dict(status="dead", error=code)
    return dict(status="pending", error=code, not_before=now + 60 * 2 ** r["attempts"])

def kept(r, now):
    """The degraded answer stands when its re-ask fails (quota, park, error); the try still counts, so re-asks stay bounded."""
    return dict(status="degraded", output=json.loads(r["output"]) if r["output"] else None, model=r["model"],
                error="reask_failed", not_before=now + QUOTA_WAIT)

def graded(step, models):
    asked = step.asked()
    return "degraded" if asked and any(m != asked for m in models) else "done"

def run_one(step, r, x, outs, now):
    if step.model and not llm.has_key():
        return dict(status="parked", error="no_key", refund=True)   # before any PDF is fetched
    try:
        with llm.scope(fresh=r["error"] == "degraded") as models:
            out = step.run(x, outs, retry=r["error"] == "not_yet") if step.name == "results" else step.run(x, outs)
        st = graded(step, models)
        return dict(status=st, output=out, model=models[-1] if models else None, not_before=now + QUOTA_WAIT if st == "degraded" else 0)
    except Exception as e:
        return outcome(e, r, x, now)

def as_planned(step, r, x, outs):
    """True if the run's inputs are the ones it was planned for: the same fingerprint, so none pending or rewritten."""
    try:
        return step.fp(outs, step.applies(x, outs)) == r["fp"]
    except (KeyError, TypeError):   # an input's run is missing
        return False

NOT_THE_FILINGS = ("no_key", "quota", "terms", "unavailable", "budget")   # the model couldn't be asked: halving wouldn't help

CALL_WORST = 4 * 120   # one model call's worst case: four tries at a 120 s timeout (finn/llm.py)

def run_batch(step, jobs, now, clock=None):
    """Read a batch in one call. If the reply can't be read, one filing may be breaking it for the rest: halve, ask
    each half once, and follow only a half that fails whole. If both halves fail whole, the model is the problem, not
    a filing, so it stops there: a systemic bad reply costs 3 calls, one breaking filing at most 1 + 2 a halving
    (11 for 20). No call starts that might not finish inside the lease; what wasn't settled counts its try and is read later."""
    if not llm.has_key():
        return [dict(status="parked", error="no_key", refund=True) for _ in jobs]
    clock, deadline = clock or (lambda: now), now + store.LEASE - CALL_WORST   # the claim was taken at now
    res = {}

    def ask(group):
        """One call for a group: its results, or the exception that sank the whole reply."""
        try:
            with llm.scope(fresh=any(r["error"] == "degraded" for r, _, _ in group)) as models:
                got = classify.read_batch([x for _, x, _ in group])
        except Exception as e:
            return e
        if not got and len(group) > 1:
            return Missing()   # a reply that reads no filing at all is treated the same
        st = graded(step, models)
        for k, (r, x, _) in enumerate(group):
            o = got.get(k)
            res[id(r)] = (dict(status=st, output={"category": o["category"], "tier": o["tier"], "line": o["line"], "how": "model"},
                                  model=models[-1] if models else None, not_before=now + QUOTA_WAIT if st == "degraded" else 0)
                             if o else outcome(Missing(), r, x, now))
        return None

    def sink(group, e):   # each filing counts its try; backoff runs from now, not from the claim
        for r, x, _ in group:
            res[id(r)] = outcome(e, r, x, clock())

    group, e = jobs, ask(jobs)
    while e is not None:
        if len(group) == 1 or getattr(e, "code", None) in NOT_THE_FILINGS:
            sink(group, e); break
        left, right = group[:len(group) // 2], group[len(group) // 2:]
        if clock() > deadline:   # no call starts that might outlast the lease
            sink(group, e); break
        el = ask(left)
        if clock() > deadline:
            if el is not None:
                sink(left, el)
            sink(right, e); break   # the right half was in the reply that failed: its try counts, and it is read later
        er = ask(right)
        if el is not None and er is not None:
            sink(group, el); break   # both halves failed whole: the model, not a filing
        group, e = (left, el) if el is not None else (right, er)
    return [res[id(r)] for r, _, _ in jobs]

def drain(db, now=time.time, cap=None, threads=4):
    """Work every step in order. cap={"results": 50} limits one step's runs per drain; the rest wait."""
    steps.STORE_PATH[0] = db.execute("PRAGMA database_list").fetchone()["file"]
    unpark(db, now())
    worked = {}
    for step in steps.STEPS:
        plan(db, step)
        limit, n = (cap or {}).get(step.name), 0
        while limit is None or n < limit:
            want = step.batch if step.batch > 1 else threads   # one batch a claim: its work fits well inside the lease
            tok, rows = store.claim(db, step.name, want if limit is None else min(want, limit - n), now())
            if not rows:
                break
            jobs = []
            for r in rows:
                ev = db.execute("SELECT * FROM events WHERE kind=? AND id=? AND rev=?", (r["kind"], r["id"], r["rev"])).fetchone()
                x, outs = json.loads(ev["payload"]), store.runs_of(db, ev)
                if as_planned(step, r, x, outs):
                    jobs.append((r, x, outs))
                else:
                    store.release(db, r, tok, now() + MOVED_WAIT)
            n += len(jobs)
            if step.batch > 1:
                res = [o for k in range(0, len(jobs), step.batch) for o in run_batch(step, jobs[k:k + step.batch], now(), now)]
            else:
                with ThreadPoolExecutor(threads) as ex:
                    res = list(ex.map(lambda j: run_one(step, *j, now()), jobs))
            for (r, _, _), o in zip(jobs, res):
                if r["error"] == "degraded" and o["status"] not in ("done", "degraded"):
                    o = kept(r, now())   # a re-ask that failed keeps the answer it was re-asking
                store.complete(db, r, tok, **o)
        worked[step.name] = n
    return worked
