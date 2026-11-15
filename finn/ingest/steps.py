"""FINN's filing policy as steps over the ledger. Each step calls the function build_push and triage.enrich use.

A step says which steps it reads, whether it applies to a filing (True, False, or None when it can't tell
because an input is parked), and how to run. Its fingerprint covers its version, its prompt, schema, model
and fallback chain, and the fingerprint, status and output of every step it reads, so a change anywhere upstream
(a new prompt, or a re-asked run that came back different) re-runs exactly what depends on it.
"""
import datetime as dt, hashlib, json
from .. import classify, config, explain, numbers, people, results, triage
from ..sources import nse, screener
from . import store

SETTLED = {"done": "settled", "degraded": "settled"}   # a re-ask that answers the same re-runs nothing downstream

class NotYet(Exception):
    """XBRL lags the filing; try again at the next drain."""

FALLBACK_READING = {"category": "unclassified", "tier": "note", "line": "", "how": "fallback"}   # read gave up, as classify does

def chain(m):
    out = [m]
    while out[-1] in config.FALLBACK:
        out.append(config.FALLBACK[out[-1]])
    return out

def _out(r):
    return json.loads(r["output"]) if r is not None and r["output"] else None

def reading(outs):
    """Category, tier and line from rules or read; None while that is unknown (read parked or blocked)."""
    if _out(outs.get("rules")):
        return _out(outs["rules"])
    rd = outs.get("read")
    if rd is None or rd["status"] in ("parked", "blocked", "pending"):
        return None
    return _out(rd) if rd["status"] in ("done", "degraded") else FALLBACK_READING

def settled(outs, step):
    r = outs.get(step)
    return r is not None and r["status"] in ("done", "degraded") and _out(r) is not None

def quarter_end(at):
    """The last quarter that ended before a filing's day: a filing on 1 Oct is after 30 Sep, one on 30 Sep is not."""
    d = nse._parse_dt(at).date()
    m = (d.month - 1) // 3 * 3
    return dt.date(d.year - 1, 12, 31) if m == 0 else dt.date(d.year, m, 30 if m in (6, 9) else 31)

TTM_VERSION = 4   # 2: the four quarters before q, not the latest four on screener (a replay saw the future); 3: as filed first;
                  # 4: a fact per day, since what was public depends on the day

def quarters_before(q, n):
    """The n quarter ends before q, newest first."""
    out, y, m = [], q.year, q.month
    for _ in range(n):
        y, m = (y - 1, m + 9) if m <= 3 else (y, m - 3)
        out.append(dt.date(y, m, 30 if m in (6, 9) else 31))
    return out

def _as_filed(db, symbol, q, by):
    """A quarter's revenue as its own results filing gave it, if the ledger holds that filing and it was public by `by`."""
    f = store.fact(db, f"results:v{BY_NAME['results'].version}:{symbol}:{q}")
    try:
        filed = nse._parse_dt(f["source"]["filed"]).date()
    except (TypeError, KeyError, ValueError):   # no such filing in the ledger, or no date on it: not known as filed
        return None
    if filed > by:
        return None
    return next((l["value"] for l in f["lines"] if l["key"] == "revenue" and l["value"]), None)

def ttm(symbol, q, by=None):
    """Revenue over the four quarters before the filing's quarter q, so a replay of an old filing is sized as it could
    have been then. Point in time first: each quarter as its own results filing gave it, filed by the filing's day `by`
    (the ledger stores those as facts). Where any is missing, screener's table, which carries later restatements; the
    fact says which. A fact per (symbol, quarter, day): an earlier filing mustn't read what a later one could see.
    A miss isn't stored."""
    db = store.connect(STORE_PATH[0])
    by = by or q + dt.timedelta(days=90)
    key = f"ttm:v{TTM_VERSION}:{symbol}:{q}:{by}"
    got = store.fact(db, key)
    if got is not None:
        return got["ttm"]
    want = quarters_before(q, 4)
    filed = [_as_filed(db, symbol, p, by) for p in want]
    if all(v is not None for v in filed):
        return store.fact(db, key, {"ttm": round(sum(filed), 2), "basis": "as filed"}, fp=f"v{TTM_VERSION}")["ttm"]
    if _results_due(db, symbol, {str(p) for p in want}, by):
        raise Waiting(symbol)   # a results filing it could size against is still being read: size it after, in any drain order
    c = screener.company(symbol)
    rows = numbers.quarter_table(c, len(c["quarters"]["cols"]))
    before = [r for r in rows if (lambda d: (d.year, d.month))(dt.datetime.strptime(r["q"], "%b %Y")) < (q.year, q.month)][-4:]
    rev = [r["rev"] for r in before if r["rev"]]
    return sum(rev) if len(rev) == 4 else None   # restated figures, the fallback: never stored as the day's fact

class Waiting(Exception):
    """An input the run could use is still on its way (a results filing the ledger holds but hasn't read): wait."""

def _results_due(db, symbol, quarters, by):
    """True if the ledger holds a results filing for one of these quarters, public by `by`, still waiting to be read."""
    for (payload,) in db.execute("SELECT e.payload FROM events e JOIN runs r ON r.kind=e.kind AND r.id=e.id AND r.rev=e.rev "
                                 "WHERE e.symbol=? AND r.step='results' AND r.status IN ('pending', 'not_yet')", (symbol,)):
        x = json.loads(payload)
        if str(quarter_end(x["an_dt"])) in quarters and nse._parse_dt(x["an_dt"]).date() <= by:
            return True
    return False

STORE_PATH = [None]   # the worker sets this, so facts land in the ledger being drained

class Step:
    def __init__(self, name, inputs, applies, run, model=None, batch=1, version=1):
        self.name, self.inputs, self.applies, self.run, self.model, self.batch, self.version = name, inputs, applies, run, model, batch, version

    def fp(self, outs, applies=True):
        """A run that doesn't apply leaves the model out, so a new prompt re-runs only the filings it reads."""
        m = self.model() if self.model and applies is not False else None
        sig = [self.name, self.version, m and [m[0], m[1], m[2], chain(m[2])],
               [(i, outs[i]["fp"], SETTLED.get(outs[i]["status"], outs[i]["status"]), outs[i]["output"]) for i in self.inputs]]
        return hashlib.sha256(json.dumps(sig, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def code(self):
        """The step's own code: when this changes, every event is planned again, not only those whose inputs moved."""
        m = self.model() if self.model else None
        sig = [self.name, self.version, m and [m[0], m[1], m[2], chain(m[2])]]
        return hashlib.sha256(json.dumps(sig, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def asked(self):
        return self.model()[2] if self.model else None

def _results(x, outs, retry=False):
    q = quarter_end(x["an_dt"])
    key = f"results:v{BY_NAME['results'].version}:{x['symbol']}:{q}"
    db = store.connect(STORE_PATH[0])
    if store.fact(db, key) is None:
        cut = results.first_cut(x["symbol"], q, ttl_hours=0 if retry else 6)
        if cut is None:
            raise NotYet(nse._parse_dt(x["an_dt"]).date().isoformat())   # dead 60 days after the filing: late filers exist
        store.fact(db, key, cut, fp=f"v{BY_NAME['results'].version}", event=str(x["seq_id"]))
    return {"fact": key}

def _size(x, outs):
    amt, q = _out(outs["explain"])["amount_cr"], quarter_end(x["an_dt"])
    t = ttm(x["symbol"], q, by=nse._parse_dt(x["an_dt"]).date())
    return {"amount_cr": amt, "ttm": t, "pct_rev": round(amt / t * 100, 2) if t else None}

def _tier(x, outs):
    """The tier as today's code would set it, with each parked or failed input handled the way enrich handles a failure."""
    c = reading(outs)
    if c is None:
        return {**FALLBACK_READING, "how": "not read"}
    t = dict(c)
    p = outs.get("people")
    if p is not None and (p["status"] != "done" or _out(p) is not None):   # people applied (done with nothing = didn't apply)
        t["people"] = (_out(p) or {}).get("people", []) if p["status"] in ("done", "degraded") else []
        t["tier"] = triage.tier_from_people(t["people"])
        if p["status"] not in ("done", "degraded"):
            t["how"] = t.get("how", "") + ", people not read"
    e = outs.get("explain")
    if e is not None and e["status"] in ("done", "degraded") and _out(e):
        ex, s = _out(e), _out(outs.get("size")) or {}
        t["line"] = ex.get("line") or t.get("line", "")
        if s.get("pct_rev") is not None:
            t["amount_cr"], t["pct_rev"] = s["amount_cr"], s["pct_rev"]
        if triage.downgrade(t, ex, t.get("pct_rev")):
            t["tier"], t["downgraded"] = "note", "small"
    elif e is not None and e["status"] != "done":
        t["unsized"] = True   # explain parked or failed: the rule tier stands, marked unsized
    return t

STEPS = [
    Step("rules", [], lambda x, o: True,
         lambda x, o: (lambda r: r and {"category": r[0], "tier": r[1], "line": "", "how": r[2]})(classify.by_rule(x))),
    Step("read", ["rules"], lambda x, o: _out(o["rules"]) is None, None,
         model=lambda: (classify.PROMPT, classify.SCHEMA, classify.MODEL), batch=20),
    Step("results", ["rules", "read"],
         lambda x, o: None if reading(o) is None else (reading(o)["category"], reading(o)["tier"]) == ("results", "act"), _results,
         version=2),   # 2: quarter_end no longer skips back a quarter for a filing on a quarter's first day
    Step("people", ["rules", "read"],
         lambda x, o: None if reading(o) is None else reading(o)["category"] == "management_change" and reading(o)["tier"] != "fold",
         lambda x, o: {"people": people.from_filing(x["sm_name"], x["attchmntFile"])},
         model=lambda: (people.PROMPT, people.SCHEMA, people.MODEL)),
    Step("explain", ["rules", "read"], lambda x, o: None if reading(o) is None else triage.needs_explain(dict(reading(o))),
         lambda x, o: explain.explain(x["sm_name"], x["desc"], x["attchmntFile"]),
         model=lambda: (explain.PROMPT, explain.SCHEMA, explain.MODEL)),
    Step("size", ["explain"],
         lambda x, o: None if o["explain"]["status"] in ("parked", "blocked") else bool(settled(o, "explain") and _out(o["explain"]).get("amount_cr")),
         _size, version=3),   # 2: ttm as of the quarter before the filing's; 3: as public on the filing's day
    Step("tier", ["rules", "read", "people", "explain", "size"], lambda x, o: True, _tier),
]
BY_NAME = {s.name: s for s in STEPS}
