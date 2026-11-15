"""The ledger's checks, on real archive rows, with every fetch and model call stubbed. No key, no network.

    python3 evals/run_ingest.py        (check 9 needs data/raw/filings from pipeline/archive.py, and is skipped without it)
"""
import copy, datetime as dt, gzip, json, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import classify, config, explain, llm, people, results, triage
from finn.ingest import steps, store, worker
from finn.sources import pdf

results_, lines = [], []
def check(n, name, ok, detail=""):
    if ok is None:
        lines.append(f"skip {n}. {name}   [{detail}]"); return
    results_.append(bool(ok)); lines.append(f"{'ok  ' if ok else 'FAIL'} {n}. {name}" + ("" if ok else f"   [{detail}]"))

DAY = [x for x in json.loads(gzip.decompress((ROOT / "evals/fixtures/filings_2025-12-05.json.gz").read_bytes()))]   # the archive's day, checked in
pick = lambda desc, n=1: [x for x in DAY if x["desc"] == desc][:n]
MGMT, ACQ = pick("Appointment", 3), pick("Acquisition", 2)
RES = [x for x in DAY if (classify.by_rule(x) or ("",))[0] == "results"][:2]
VAGUE = [x for x in DAY if classify.by_rule(x) is None][:25]
T0 = dt.datetime(2026, 1, 10).timestamp()
clock = [T0]; now = lambda: clock[0]

def ledger(rows):
    db = store.connect(pathlib.Path(tempfile.mkdtemp()) / "l.sqlite")
    for x in rows:
        store.put(db, x)
    return db

def key(on):
    os.environ.pop("GEMINI_API_KEY", None)
    if on:
        os.environ["GEMINI_API_KEY"] = "test-not-a-key"

def run(db, step, sid):
    ev = [e for e in store.latest(db) if e["id"] == str(sid)][0]
    return store.runs_of(db, ev).get(step)

fetched, calls = [], {}
def count(name, fn):
    def f(*a, **k):
        calls[name] = calls.get(name, 0) + 1
        return fn(*a, **k)
    return f
pdf.pages = lambda url, *a, **k: fetched.append(url) or (_ for _ in ()).throw(pdf.FetchError("unreachable", "stub"))
CUT = lambda sym, q=None, ttl_hours=6: {"quarter": str(q), "lines": []}
results.first_cut = count("cut", CUT)
REAL_TTM, steps.ttm = steps.ttm, lambda sym, q, by=None: 10000.0
people.from_filing = count("people", lambda co, url: [{"name": "A", "seniority": "top"}])
explain.explain = count("explain", lambda co, desc, url: {"line": "bought X for Rs 10 cr", "amount_cr": 10, "routine": False})
classify.read_batch = count("read", lambda batch: {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))})
key(False)

# 1. Two polls of a window store each filing once.
db = ledger(DAY)
again = sum(store.put(db, x) > 0 for x in DAY)
check(1, "two polls of a day store each filing once", again == 0 and len(store.latest(db)) == len({x["seq_id"] for x in DAY}), again)

# 2. Cosmetic change: no revision. Real change: revision 2, which re-runs its steps.
db = ledger(ACQ[:1]); worker.drain(db, now)
cos = dict(ACQ[0], sort_date="x", fileSize="9 MB", difference="1")
real = dict(ACQ[0], attchmntText=ACQ[0]["attchmntText"] + " Revised.")
r1, r2 = store.put(db, cos), store.put(db, real)
worker.drain(db, now)
check(2, "a cosmetic change makes no revision; a real one makes revision 2, which runs its steps",
      r1 == 0 and r2 == 2 and run(db, "tier", ACQ[0]["seq_id"])["rev"] == 2 and run(db, "tier", ACQ[0]["seq_id"])["status"] == "done", (r1, r2))

# 3. Retries: two failures then success is done; five failures is dead; not_pdf is dead at once (one attempt, counted at claim).
key(True); clock[0] = T0
db = ledger(MGMT)
seq = {MGMT[0]["seq_id"]: [RuntimeError("x"), RuntimeError("x"), None], MGMT[1]["seq_id"]: [RuntimeError("x")] * 9,
       MGMT[2]["seq_id"]: [pdf.FetchError("not_pdf")]}
def flaky(co, url):
    sid = [x["seq_id"] for x in MGMT if x["attchmntFile"] == url][0]
    e = seq[sid].pop(0) if seq[sid] else None
    if e:
        raise e
    return [{"name": "A", "seniority": "senior"}]
people.from_filing = flaky
for _ in range(6):
    worker.drain(db, now); clock[0] += 3600
got = [run(db, "people", x["seq_id"])["status"] for x in MGMT]
check(3, "two failures then a success end done; five failures end dead; not_pdf is dead at once",
      got == ["done", "dead", "dead"] and run(db, "people", MGMT[1]["seq_id"])["attempts"] == 5 and run(db, "people", MGMT[2]["seq_id"])["attempts"] == 1, got)

# 4. A worker that dies mid-step: its lease expires, the run is reclaimed and done once, and the late original writes nothing.
people.from_filing = count("people", lambda co, url: [{"name": "A", "seniority": "top"}])
db = ledger(MGMT[:1]); clock[0] = T0; sid = MGMT[0]["seq_id"]
worker.plan(db, steps.BY_NAME["rules"])
dead_tok, dead_rows = store.claim(db, "rules", 9, now())   # a worker leases the run, then dies
worker.drain(db, now)                                        # inside the lease: nothing to claim
early = run(db, "rules", sid)["status"]
clock[0] += store.LEASE + 60; calls.clear(); worker.drain(db, now)   # the lease has expired
late = store.complete(db, dead_rows[0], dead_tok, "dead")
check(4, "an expired lease is reclaimed and done once; the late worker writes nothing",
      early == "pending" and run(db, "rules", sid)["status"] == "done" and calls.get("people") == 1 and late is False,
      (early, run(db, "rules", sid)["status"], calls, late))

# 5. A partial batch leaves the missing filings pending.
db = ledger(VAGUE[:20]); clock[0] = T0
classify.read_batch = lambda batch: {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(0, len(batch), 2)}
worker.drain(db, now)
st = [run(db, "read", x["seq_id"])["status"] for x in VAGUE[:20]]
check(5, "a partial batch leaves the missing filings pending", st.count("done") == 10 and st.count("pending") == 10, st)
classify.read_batch = count("read", lambda batch: {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))})

# 6. No key: every model step parked or blocked, nothing fetched, the view as today's code shows a failure; a key unparks.
key(False); fetched.clear(); calls.clear()
rows6 = MGMT + ACQ + RES + VAGUE
db = ledger(rows6); worker.drain(db, now, cap={"results": 0})
model = [r for s in ("read", "people", "explain") for r in db.execute("SELECT status, error FROM runs WHERE step=?", (s,))]
applied = [r for r in model if not (r["status"] == "done")]
vague_tier = [json.loads(run(db, "tier", x["seq_id"])["output"]) for x in VAGUE]
ok6 = all(r["status"] in ("parked", "blocked") for r in applied) and not fetched and not calls \
      and all((t["category"], t["tier"]) == ("unclassified", "note") for t in vague_tier)
key(True); worker.drain(db, now, cap={"results": 0})
ok6b = all(run(db, "read", x["seq_id"])["status"] == "done" for x in VAGUE) and calls.get("read", 0) == 2
check(6, "no key: model steps parked or blocked, none failed, nothing fetched; a key unparks them", ok6 and ok6b, (len(applied), fetched[:2], calls))

# 7. Changing read's prompt re-runs read and what reads it, never rules, and results only where read categorised.
db = ledger(rows6); worker.drain(db, now)
fp = lambda: {(r["id"], r["step"]): r["fp"] for r in db.execute("SELECT id, step, fp FROM runs")}
before = fp(); classify.PROMPT += " "; worker.drain(db, now); after = fp(); classify.PROMPT = classify.PROMPT[:-1]
changed = {s for (i, s) in before if before[(i, s)] != after.get((i, s))}
res_changed = {i for (i, s) in before if s == "results" and before[(i, s)] != after[(i, s)]}
check(7, "a new read prompt re-runs read, people, explain, size and tier, never rules; results only for filings read categorised",
      "rules" not in changed and {"read", "explain", "tier"} <= changed and res_changed <= {str(x["seq_id"]) for x in VAGUE}
      and not res_changed & {str(x["seq_id"]) for x in RES}, (changed, len(res_changed)))

# 8. Results in any order, and a not_yet before the cut, give one fact per (symbol, quarter).
twin = [dict(RES[0], seq_id=f"{RES[0]['seq_id']}{k}") for k in range(3)]
state = {"n": 0}
def lagging(sym, q=None, ttl_hours=6):
    state["n"] += 1
    return None if state["n"] == 1 else CUT(sym, q)
results.first_cut = lagging
db = ledger(list(reversed(twin))); clock[0] = dt.datetime(2025, 12, 6).timestamp()   # within 60 days of the quarter
worker.drain(db, now, threads=1)
reads = state["n"]; worker.drain(db, now); lag_reads = state["n"] - reads   # at once: the lagging filing isn't read again
lag_wait = run(db, "results", twin[0]["seq_id"])["not_before"] - clock[0]
clock[0] += worker.NOT_YET_WAIT[1]; worker.drain(db, now)
facts = db.execute("SELECT key FROM facts WHERE key LIKE 'results:%'").fetchall()
check(8, "results in any order and a not_yet first give one fact per (symbol, quarter)",
      len(facts) == 1 and all(run(db, "results", x["seq_id"])["status"] == "done" for x in twin), (len(facts), state))
results.first_cut = count("cut", CUT)

# 9. The archive holds every filing in the 28 Oct snapshot.
snap = json.loads((ROOT / "web/public/data/push.json").read_text())["filings"]
days = {f["at"][:10] for f in snap}
have = set()
for d in days:
    p = ROOT / "data/raw/filings" / f"{d}.json.gz"
    if p.exists():
        have |= {str(x["seq_id"]) for x in json.loads(gzip.decompress(p.read_bytes()))}
miss = [f["id"] for f in snap if str(f["id"]) not in have]
archived = (ROOT / "data/raw/filings").exists()
check(9, f"the archive holds the snapshot's {len(snap)} filing ids", (not miss) if archived else None,
      f"{len(miss)} missing" if archived else "no archive here: pipeline/archive.py fetches it")

# 10. Explain parks: the rule tier stands, marked unsized, as triage.enrich does when explain fails.
key(False)
db = ledger(ACQ[:1]); worker.drain(db, now)
t = json.loads(run(db, "tier", ACQ[0]["seq_id"])["output"])
row = copy.deepcopy(ACQ[0]); row.update(category=t["category"], tier=classify.by_rule(ACQ[0])[1], line="")
explain.explain = lambda *a: (_ for _ in ()).throw(llm.LLMError("no_key"))
triage.enrich([row], {}, {})
check(10, "explain parked keeps the rule tier, marked unsized, as enrich does on the same failure",
      t["tier"] == row["tier"] == "act" and t.get("unsized") is True, (t, row["tier"]))

# 11. A fallback model answering inside explain marks that run degraded.
key(True)
def fell_back(*a):
    llm._answered(config.FALLBACK[config.FAST])
    return {"line": "x", "amount_cr": None, "routine": False}
explain.explain = fell_back
db = ledger(ACQ[:1]); worker.drain(db, now)
check(11, "a fallback inside explain marks the run degraded", run(db, "explain", ACQ[0]["seq_id"])["status"] == "degraded",
      run(db, "explain", ACQ[0]["seq_id"])["status"])

# 12. Sizing in a replay uses the four quarters before the filing's, not screener's latest four; a fallback isn't stored.
import threading
from finn import numbers
from finn.sources import screener
QS = ["Jun 2024", "Sep 2024", "Dec 2024", "Mar 2025", "Jun 2025", "Sep 2025", "Dec 2025"]
saved = screener.company, numbers.quarter_table
screener.company = lambda sym: {"quarters": {"cols": QS if sym == "LONG" else QS[:3]}}
numbers.quarter_table = lambda c, n: [{"q": q, "rev": 10.0 ** k} for k, q in enumerate(c["quarters"]["cols"])][-n:]
db = ledger([]); steps.STORE_PATH[0] = db.execute("PRAGMA database_list").fetchone()["file"]
got12 = REAL_TTM("LONG", steps.quarter_end("05-Dec-2025 10:00:00")), REAL_TTM("SHORT", steps.quarter_end("05-Dec-2025 10:00:00"))
stored = db.execute("SELECT key FROM facts").fetchall()
screener.company, numbers.quarter_table = saved
check(12, "a replay sizes against the four quarters before the filing's, not the latest four; a fallback or a miss isn't stored",
      got12 == (1111.0 * 10, None) and len(stored) == 0, (got12, len(stored)))

# 22. Point in time: where the ledger holds the four earlier quarters' own results filings, sizing reads them as filed,
# and a quarter filed after the filing's day sends it back to screener's restated table.
def filed_fact(db_, sym, qe, rev, on):
    store.fact(db_, f"results:v{steps.BY_NAME['results'].version}:{sym}:{qe}",
               {"lines": [{"key": "revenue", "value": rev}], "source": {"filed": on}}, fp="test")
screener.company = lambda sym: {"quarters": {"cols": QS}}
numbers.quarter_table = lambda c, n: [{"q": q, "rev": 10.0 ** k} for k, q in enumerate(c["quarters"]["cols"])][-n:]
db = ledger([]); steps.STORE_PATH[0] = db.execute("PRAGMA database_list").fetchone()["file"]
Q = steps.quarter_end("05-Dec-2025 10:00:00")
for qe, rev, on in zip(steps.quarters_before(Q, 4), (400.0, 300.0, 200.0, 100.0), ("01-Aug-2025", "10-May-2025", "12-Feb-2025", "11-Nov-2024")):
    filed_fact(db, "PIT", qe, rev, f"{on} 18:00:00")
    filed_fact(db, "LATE", qe, rev, f"{'06-Dec-2025' if rev == 400.0 else on} 18:00:00")
pit, late = REAL_TTM("PIT", Q, by=dt.date(2025, 12, 5)), REAL_TTM("LATE", Q, by=dt.date(2025, 12, 5))
basis = {r["key"].split(":")[2]: json.loads(r["value"])["basis"] for r in db.execute("SELECT key, value FROM facts WHERE key LIKE 'ttm:%'")}
for qe, rev, on in zip(steps.quarters_before(Q, 4), (400.0, 300.0, 200.0, 100.0), ("06-Dec-2025", "10-May-2025", "12-Feb-2025", "11-Nov-2024")):
    filed_fact(db, "TWO", qe, rev, f"{on} 18:00:00")
later, earlier = REAL_TTM("TWO", Q, by=dt.date(2025, 12, 20)), REAL_TTM("TWO", Q, by=dt.date(2025, 12, 5))   # the later filing is sized first
screener.company, numbers.quarter_table = saved
check(27, "a filing sized after a later one of the same quarter doesn't read a result made public between them",
      (later, earlier) == (1000.0, 1111.0 * 10), (later, earlier))
check(22, "sizing reads the four earlier quarters as filed and stores that; one filed after the day falls back to screener, not stored",
      pit == 1000.0 and late == 1111.0 * 10 and basis == {"PIT": "as filed"}, (pit, late, basis))

# 13. A degraded read is re-asked fresh an hour later, at most twice; an answer that differs re-runs tier.
key(True); clock[0] = T0
answers = iter(["press_release", "order_win", "order_win", "order_win"])
fresh = []
def degraded_read(batch):
    llm._answered(steps.chain(config.FAST)[1]); fresh.append(llm._FRESH.get())
    c = next(answers); calls["read"] = calls.get("read", 0) + 1
    return {i: {"i": i, "category": c, "tier": "note", "line": "x"} for i in range(len(batch))}
classify.read_batch = degraded_read; calls.clear()
db = ledger(VAGUE[:1]); sid = VAGUE[0]["seq_id"]
worker.drain(db, now); t1 = json.loads(run(db, "tier", sid)["output"])["category"]
worker.drain(db, now); early = calls["read"]                          # inside the hour: not re-asked
for _ in range(4):
    clock[0] += 3601; worker.drain(db, now)
t2 = json.loads(run(db, "tier", sid)["output"])["category"]
db13 = db
check(13, "a degraded read is re-asked fresh an hour later, at most twice; an answer that differs re-runs tier",
      (t1, t2, early, calls["read"], fresh) == ("press_release", "order_win", 1, 3, [False, True, True]), (t1, t2, early, calls["read"], fresh))
classify.read_batch = count("read", lambda batch: {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))})

# 14. Planning reads only what changed: a quiet drain reads no event; a new step version plans every event again.
db = ledger(rows6); worker.drain(db, now)
worker.PLANNED["events"] = 0; worker.drain(db, now); quiet = worker.PLANNED["events"]
worker.drain(db13, now); worker.PLANNED["events"] = 0; worker.drain(db13, now); quiet += worker.PLANNED["events"]   # re-asked the same
steps.BY_NAME["size"].version += 1; worker.PLANNED["events"] = 0; worker.drain(db, now); steps.BY_NAME["size"].version -= 1
check(14, "a quiet drain reads no event, even after a re-ask answered the same; a new step version plans every event again",
      quiet == 0 and worker.PLANNED["events"] >= len(rows6), (quiet, worker.PLANNED["events"]))

# 15. A run whose workers keep dying is counted at each claim and ends dead after five.
db = ledger(MGMT[:1]); clock[0] = T0; sid = MGMT[0]["seq_id"]
worker.plan(db, steps.BY_NAME["rules"])
for _ in range(store.MAX_ATTEMPTS + 1):
    store.claim(db, "rules", 9, now()); clock[0] += store.LEASE + 1   # each worker dies holding the lease
check(15, "a run whose workers die five times ends dead, each death counted",
      (run(db, "rules", sid)["status"], run(db, "rules", sid)["attempts"]) == ("dead", store.MAX_ATTEMPTS), dict(run(db, "rules", sid)))

# 16. Two drains at once, on two connections, run each model step once per filing.
import time as _t
rows_read = []
classify.read_batch = lambda batch: rows_read.extend(x["seq_id"] for x in batch) or {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))}
def slow(co, url):
    _t.sleep(0.02); calls["people"] = calls.get("people", 0) + 1
    return [{"name": "A", "seniority": "top"}]
people.from_filing = slow; calls.clear(); clock[0] = T0
db = ledger(MGMT + ACQ + VAGUE[:8]); path = db.execute("PRAGMA database_list").fetchone()["file"]
errs = []
def go():
    try:
        worker.drain(store.connect(path), now)
    except Exception as e:
        errs.append(repr(e))
th = [threading.Thread(target=go) for _ in range(2)]; [t.start() for t in th]; [t.join() for t in th]
race = ledger(MGMT[:1]); worker.plan(race, steps.BY_NAME["rules"]); tok16, rows16 = store.claim(race, "rules", 1, now())
ev16 = store.latest(race)[0]; store.set_run(race, ev16, "rules", rows16[0]["fp"], "pending")   # a planner that read before the claim
check(16, "two drains at once run each model step once per filing; a racing planner can't reset a leased run",
      store.runs_of(race, ev16)["rules"]["lease"] == tok16 and not errs and calls.get("people") == len(MGMT) and sorted(rows_read) == sorted(x["seq_id"] for x in VAGUE[:8])
      and all(run(db, "tier", x["seq_id"])["status"] == "done" for x in MGMT + ACQ), (errs, calls, len(rows_read)))

# 17. A re-ask that fails keeps the degraded answer, and the tier it gave.
key(True); clock[0] = T0
turns = iter(["fallback", "quota"])
def reask_fails(batch):
    if next(turns) == "quota":
        raise llm.LLMError("quota")
    llm._answered(steps.chain(config.FAST)[1])
    return {i: {"i": i, "category": "order_win", "tier": "act", "line": "x"} for i in range(len(batch))}
classify.read_batch = reask_fails
db = ledger(VAGUE[:1]); sid = VAGUE[0]["seq_id"]
worker.drain(db, now); before = json.loads(run(db, "tier", sid)["output"])
clock[0] += 3601; worker.drain(db, now); after = json.loads(run(db, "tier", sid)["output"]); rd = run(db, "read", sid)
check(17, "a re-ask that fails keeps the degraded answer and its tier",
      (before["tier"], after["tier"], rd["status"], (json.loads(rd["output"] or "null") or {}).get("category")) == ("act", "act", "degraded", "order_win"),
      (before, after, rd["status"], rd["error"]))

# 18. A re-ask that answers the same, now from the model asked, re-runs nothing downstream.
turns18 = iter([True, False])
def same_answer(batch):
    if next(turns18):
        llm._answered(steps.chain(config.FAST)[1])
    return {i: {"i": i, "category": "management_change", "tier": "note", "line": "x"} for i in range(len(batch))}
classify.read_batch = same_answer; calls.clear(); clock[0] = T0
people.from_filing = count("people", lambda co, url: [{"name": "A", "seniority": "senior"}])
db = ledger(VAGUE[:1]); sid = VAGUE[0]["seq_id"]
worker.drain(db, now); clock[0] += 3601; worker.drain(db, now)
check(18, "a re-ask that answers the same re-runs nothing downstream: people read once",
      run(db, "read", sid)["status"] == "done" and calls.get("people") == 1, (run(db, "read", sid)["status"], calls))

# 23. A step parked for terms (private text, no paid terms) waits through a drain with a key, and resumes once the terms are paid.
key(True); clock[0] = T0; os.environ.pop("FINN_MODEL_TERMS", None)
real_explain, explain.explain = explain.explain, lambda *a: (_ for _ in ()).throw(llm.LLMError("terms"))
db = ledger(ACQ[:1]); sid = ACQ[0]["seq_id"]; worker.drain(db, now)
explain.explain = lambda co, desc, url: {"line": "bought X for Rs 10 cr", "amount_cr": 10, "routine": False}
worker.drain(db, now); waited = (run(db, "explain", sid)["status"], run(db, "explain", sid)["error"])
os.environ["FINN_MODEL_TERMS"] = "paid"; worker.drain(db, now); os.environ.pop("FINN_MODEL_TERMS")
explain.explain = real_explain
check(23, "a step parked for terms waits with a key alone, and runs once the terms are paid",
      waited == ("parked", "terms") and run(db, "explain", sid)["status"] == "done", (waited, run(db, "explain", sid)["status"]))

# 19. A claim takes one batch (20 to read, 4 otherwise) and leases it for 30 minutes, three times its worst case.
classify.read_batch = count("read", lambda batch: {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))})
claims, real_claim = [], store.claim
def watched(db_, step, n, at, **k):
    tok, rows = real_claim(db_, step, n, at, **k)
    lease = db_.execute("SELECT MAX(lease_until) FROM runs WHERE lease=?", (tok,)).fetchone()[0]
    claims.append((step, len(rows), lease and lease - at))
    return tok, rows
store.claim = watched; clock[0] = T0
db = ledger(VAGUE + MGMT + ACQ); worker.drain(db, now)
store.claim = real_claim
got19 = [(st, k, l) for st, k, l in claims if k]
check(19, "a claim takes one batch, 20 to read and 4 otherwise, leased for 30 minutes",
      got19 and all(k <= (20 if st == "read" else 4) and l == store.LEASE == 1800 for st, k, l in got19)
      and any(st == "read" and k == 20 for st, k, l in got19), got19[:6])

# 24. A run is worked only against the inputs it was planned for. Tier is planned; another drain starts re-asking the
# degraded read; this drain must not work tier on a read that is in flight, or it says "not read" for good.
key(True); clock[0] = T0
def fallback_act(batch):
    llm._answered(steps.chain(config.FAST)[1])
    return {i: {"i": i, "category": "order_win", "tier": "act", "line": "x"} for i in range(len(batch))}
classify.read_batch = fallback_act
db = ledger(VAGUE[:1]); sid = VAGUE[0]["seq_id"]
worker.drain(db, now, cap={"tier": 0})                                   # read degraded; tier planned, not yet worked
answer24 = json.loads(run(db, "read", sid)["output"])
clock[0] += 3601; worker.unpark(db, now())                               # drain A: the re-ask is due,
tokA, rowsA = store.claim(db, "read", 20, now())                         # and A holds the read while it asks
worker.drain(db, now); mid = run(db, "tier", sid)                        # drain B, meanwhile
store.complete(db, rowsA[0], tokA, status="degraded", output=answer24, model=steps.chain(config.FAST)[1], not_before=now() + 3600)
clock[0] += worker.MOVED_WAIT + 1; worker.drain(db, now); end = json.loads(run(db, "tier", sid)["output"])
check(24, "a tier claimed while its read is being re-asked isn't worked; when the re-ask answers the same, the tier carries the reading",
      (mid["status"], mid["attempts"], end["category"]) == ("pending", 0, "order_win") and end.get("how") != "not read", (mid["status"], mid["attempts"], end))

# 25. One filing whose reply can never be read doesn't take the 19 beside it: the batch is halved until it is alone.
bad25 = VAGUE[3]["seq_id"]
def poisoned(batch):
    calls["read"] = calls.get("read", 0) + 1
    if any(x["seq_id"] == bad25 for x in batch):
        raise llm.LLMError("bad_response")
    return {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))}
classify.read_batch = poisoned; clock[0] = T0
db = ledger(VAGUE[:20])
for _ in range(store.MAX_ATTEMPTS):
    worker.drain(db, now); clock[0] += 3600
st25 = {x["seq_id"]: run(db, "read", x["seq_id"])["status"] for x in VAGUE[:20]}
def down(batch):
    calls["read"] = calls.get("read", 0) + 1
    raise llm.LLMError("unavailable")
classify.read_batch = down; calls.clear(); worker.drain(ledger(VAGUE[:20]), now)
check(25, "one unreadable filing ends dead alone and the 19 beside it are read; a model that is down is asked once, not 39 times",
      [k for k, v in st25.items() if v == "dead"] == [bad25] and sum(v == "done" for v in st25.values()) == 19 and calls.get("read") == 1,
      (sorted(set(st25.values())), calls.get("read")))

# 26. A filing revised while its read is parked: only the newest revision goes to the model.
key(False); clock[0] = T0
db = ledger(VAGUE[:1]); sid = VAGUE[0]["seq_id"]; worker.drain(db, now)   # no key: the read parks
store.put(db, dict(VAGUE[0], attchmntText=(VAGUE[0].get("attchmntText") or "") + " Revised."))
key(True); sent26 = []
classify.read_batch = lambda batch: sent26.extend(x.get("attchmntText") or "" for x in batch) or {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))}
worker.drain(db, now)
old26 = db.execute("SELECT status FROM runs WHERE id=? AND rev=1 AND step='read'", (str(sid),)).fetchone()["status"]
check(26, "a filing revised while its read is parked sends only its newest revision to the model; the old run is superseded",
      len(sent26) == 1 and sent26[0].endswith(" Revised.") and old26 == "superseded" and run(db, "read", sid)["status"] == "done", (len(sent26), old26))
classify.read_batch = count("read", lambda batch: {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))})

# 21. A lagging results filing waits a quarter of its age before NSE is read again, 15 minutes to 6 hours.
check(21, "a not_yet isn't re-read at the next drain; it waits a quarter of its age, at most 6 hours",
      lag_reads == 0 and worker.NOT_YET_WAIT[0] <= lag_wait <= worker.NOT_YET_WAIT[1], (lag_reads, lag_wait))

# 20. The quarter a filing's results are for: the last that ended before its day.
qe = {d: str(steps.quarter_end(f"{d} 10:00:00")) for d in ("01-Oct-2025", "30-Sep-2025", "01-Jan-2026", "31-Dec-2025", "01-Apr-2026")}
check(20, "a filing on 1 Oct is for 30 Sep; one on 30 Sep is for 30 Jun", qe == {"01-Oct-2025": "2025-09-30", "30-Sep-2025": "2025-06-30",
      "01-Jan-2026": "2025-12-31", "31-Dec-2025": "2025-09-30", "01-Apr-2026": "2026-03-31"}, qe)

# 28. A model that answers every batch with an unreadable reply costs 3 calls for 20 filings, not 39: both halves
#     failing whole means the model, not a filing, so halving stops. Each filing counts one try.
key(True)
def garbled(batch):
    calls["read"] = calls.get("read", 0) + 1
    raise llm.LLMError("bad_response")
classify.read_batch = garbled; calls.clear(); clock[0] = T0
db28 = ledger(VAGUE[:20]); worker.drain(db28, now)
st28 = [run(db28, "read", x["seq_id"]) for x in VAGUE[:20]]
check(28, "a reply the model always garbles costs 3 calls for 20 filings, not 39, and each filing counts one try",
      calls.get("read") == 3 and all(r["status"] == "pending" and r["attempts"] == 1 for r in st28), (calls.get("read"), {r["status"] for r in st28}))

# 29. Read's reply is checked item by item: a missing line, a tier off the list or a made-up category is unread, never a crash.
import importlib as _il
_il.reload(classify)
items29 = [{"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(20)]
del items29[0]["line"]; items29[1]["tier"] = "URGENT"; items29[2]["category"] = "made_up"
_gen = llm.generate
llm.generate = lambda *a, **k: copy.deepcopy(items29)
try:
    db29 = ledger(VAGUE[:20]); clock[0] = T0
    crashed = None
    try:
        worker.drain(db29, now)
    except Exception as e:
        crashed = repr(e)
    st29 = [run(db29, "read", x["seq_id"])["status"] for x in VAGUE[:20]]
    tiers29 = {(run(db29, "tier", x["seq_id"]) or {"status": None})["status"] for x in VAGUE[:20]}
finally:
    llm.generate = _gen
check(29, "a reply item off the schema is unread, the other 17 are read, and the drain runs on to tier",
      crashed is None and sorted(st29) == ["done"] * 17 + ["pending"] * 3 and tiers29 == {"done", None}, (crashed, sorted(set(st29)), tiers29))

# 30. Halving stops before a call that might outlast the lease: what is left is handed back untried, not paid twice.
bad30 = VAGUE[5]["seq_id"]
starts30 = []
def slow(batch):
    calls["read"] = calls.get("read", 0) + 1
    starts30.append(clock[0])
    if calls["read"] <= 3:
        clock[0] += store.LEASE / 2   # the claim's first calls each take half the lease
    if any(x["seq_id"] == bad30 for x in batch):
        raise llm.LLMError("bad_response")
    return {i: {"i": i, "category": "press_release", "tier": "note", "line": "x"} for i in range(len(batch))}
classify.read_batch = slow; calls.clear(); clock[0] = T0
db30 = ledger(VAGUE[:20]); worker.drain(db30, now)
st30 = [run(db30, "read", x["seq_id"]) for x in VAGUE[:20]]
check(30, "no halving call starts after the lease's last safe moment, and no filing counts more than one try",
      len(starts30) >= 2 and all(t <= T0 + store.LEASE - worker.CALL_WORST for t in starts30) and all(r["attempts"] <= 1 for r in st30),
      ([round(t - T0) for t in starts30], sorted({(r["status"], r["error"], r["attempts"]) for r in st30}, key=str)))

# 31. Sizing doesn't depend on drain order: with results capped, size waits for an earlier quarter's results filing the
#     ledger holds, rather than sizing against screener's restated table and never looking again.
saved31 = (steps.ttm, results.first_cut, screener.company, numbers.quarter_table, explain.explain, classify.read_batch)
FILED31 = {"2025-06-30": "10-Aug-2025 18:00:00", "2025-03-31": "10-May-2025 18:00:00", "2024-12-31": "10-Feb-2025 18:00:00", "2024-09-30": "10-Nov-2024 18:00:00"}
RES31 = next(x for x in DAY if (classify.by_rule(x) or ("",))[0] == "results")
ACQ31 = next(x for x in DAY if x["desc"] == "Acquisition")
steps.ttm = REAL_TTM
results.first_cut = lambda sym, q=None, ttl_hours=6: {"lines": [{"key": "revenue", "value": 250.0}], "source": {"filed": FILED31[str(q)]}}
screener.company = lambda sym: {"quarters": {"cols": ["Sep 2024", "Dec 2024", "Mar 2025", "Jun 2025", "Sep 2025"]}}
numbers.quarter_table = lambda c, n: [{"q": q, "rev": 400.0} for q in c["quarters"]["cols"]]   # restated later: 400 a quarter
explain.explain = lambda *a: {"line": "bought X for Rs 10 cr", "amount_cr": 10, "routine": False}
classify.read_batch = lambda b: {}
rows31 = [dict(RES31, seq_id=f"9000{k}", symbol="ORD", an_dt=on) for k, on in enumerate(FILED31.values())] + [dict(ACQ31, seq_id="90100", symbol="ORD", an_dt="05-Dec-2025 10:00:00")]
def sized(caps):
    db_ = ledger(rows31); clock[0] = T0
    for c in caps:
        worker.drain(db_, now, cap=c); clock[0] += 3600
    r = run(db_, "size", "90100")
    return json.loads(r["output"])["pct_rev"] if r and r["output"] else None
try:
    key(True)
    order31 = (sized([None]), sized([{"results": 2}, None, None]))
finally:
    steps.ttm, results.first_cut, screener.company, numbers.quarter_table, explain.explain, classify.read_batch = saved31
check(31, "a filing is sized the same whatever the drain order: with results capped, size waits for them",
      order31 == (1.0, 1.0), order31)

# 32. Two polls at once, each on its own connection, store each filing once and neither fails.
import threading as _th
path32 = pathlib.Path(tempfile.mkdtemp()) / "l.sqlite"; store.connect(path32)
errs32 = []
def poll32():
    db_ = store.connect(path32)
    try:
        for x in DAY[:200]:
            store.put(db_, x)
    except Exception as e:
        errs32.append(repr(e))
ts = [_th.Thread(target=poll32) for _ in range(3)]
[t.start() for t in ts]; [t.join() for t in ts]
n32 = store.connect(path32).execute("SELECT COUNT(*) FROM events").fetchone()[0]
check(32, "three polls at once store each filing once, and none fails", not errs32 and n32 == len({str(x["seq_id"]) for x in DAY[:200]}), (errs32[:1], n32))
key(False)

ok, n = sum(results_), len(results_)
lines.append(f"TOTAL {ok}/{n}" + (f", {sum(l.startswith('skip') for l in lines)} skipped" if any(l.startswith("skip") for l in lines) else ""))
print("\n".join(lines))
if not any(l.startswith("skip") for l in lines):   # a run that skipped a check doesn't replace the record of one that ran them all
    (ROOT / "evals/ingest_result.txt").write_text("\n".join(lines) + "\n")
sys.exit(0 if ok == n else 1)
