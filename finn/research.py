"""Pull: build one company's research file from primary sources only.

Steps are separate functions so the web API can run them one request at a time
(each stays well inside a serverless time limit) and the batch pipeline can run them in a row.
"""
import datetime as dt, sys
from concurrent.futures import ThreadPoolExecutor
from . import ledger, llm, numbers, config
from .sources import nse, screener, pdf

N_CALLS = 5  # four calls whose promises we grade, plus the latest call as evidence

def sources(symbol, today=None, every_call=False):
    """Fast step: financial tables, snapshot and the list of transcripts. No model calls.
    every_call keeps the whole merged list, not just the calls FINN reads; grading checks against it."""
    today = today or dt.date.today()
    c = screener.company(symbol)
    nse_ok = True
    try:
        ts = nse.transcripts(symbol, today=today)
    except Exception:
        ts, nse_ok = [], False
    ts = _merge_transcripts(ts, c["concalls"])
    return {
        "symbol": c["symbol"], "name": c["name"], "basis": c["basis"], "source": c["source"],
        "asof": today.isoformat(),
        "snapshot": numbers.snapshot(c),
        "quarters": numbers.quarter_table(c, 8),
        "numbers_text": numbers.numbers_for_prompt(c),
        "transcripts": ts if every_call else ts[:N_CALLS + 1],
        "nse_ok": nse_ok,
    }

def _month(p):
    d = dt.datetime.strptime(p, "%b %Y")
    return d.year * 12 + d.month

def _merge_transcripts(nse_list, screener_list):
    """One entry per call with every known URL for it. NSE first (the exchange's own copy);
    screener's BSE link as the alternate. Some companies file only a one-page letter pointing
    to their website, which is why the alternate matters."""
    calls = [{"period": t["period"], "urls": [t["url"]]} for t in nse_list]
    for t in screener_list:
        near = [c for c in calls if abs(_month(c["period"]) - _month(t["period"])) <= 1]
        if near:
            near[0]["urls"].append(t["url"])
        else:
            calls.append({"period": t["period"], "urls": [t["url"]]})
    calls.sort(key=lambda c: _month(c["period"]), reverse=True)
    for c in calls:
        c["url"] = c["urls"][0]
    return calls

def promises_for(t):
    err = "no transcript"
    for url in t.get("urls", [t["url"]]):
        try:
            if len(pdf.pages(url, max_pages=6)) < 4:
                err = "filing is a cover letter, not the transcript"; continue
            return ledger.extract_promises(url, t["period"])
        except (pdf.FetchError, llm.LLMError) as e:
            err = e.code                                  # the client sees the code; the detail is logged
            print(f"{t['period']} call: {e}", file=sys.stderr)
    return {"period": t["period"], "url": t["url"], "error": err, "promises": [], "dropped_unverified": 0, "soft_count": 0}

def grade(src, calls):
    calls = sorted(calls, key=lambda c: dt.datetime.strptime(c["period"], "%b %Y"))
    latest = calls[-1] if calls else None
    older = [p for c in calls[:-1] for p in c["promises"]]
    if not older:
        return {"grades": [], "read": "", "questions": [], "bull": [], "bear": []}
    latest_q = src["quarters"][-1]["q"] if src["quarters"] else "the latest quarter"
    return ledger.grade(src["name"], src["basis"], src["asof"], latest_q, older, src["numbers_text"],
                        latest["period"] if latest else "", latest["url"] if latest and not latest.get("error") else None)

def assemble(src, calls, graded):
    calls = sorted(calls, key=lambda c: dt.datetime.strptime(c["period"], "%b %Y"))
    older = [p for c in calls[:-1] for p in c["promises"]]
    by_id = {g["id"]: g for g in graded.get("grades", [])}
    book = []
    for i, p in enumerate(older):
        g = by_id.get(i, {"status": "unclear", "verdict": "", "evidence_kind": "none", "evidence": "", "repeat_of": -1})
        book.append({**p, **{k: v for k, v in g.items() if k != "id"}, "id": i})
    # Restated promises fold into the first time they were made; the count of restatements is kept.
    roots = {}
    for b in book:
        r = b.get("repeat_of", -1)
        if r is not None and 0 <= r < len(book) and r != b["id"]:
            root = r
            while 0 <= book[root].get("repeat_of", -1) < len(book) and book[root]["repeat_of"] != root:
                root = book[root]["repeat_of"]
            roots.setdefault(root, []).append(b)
    ledger_rows = []
    for b in book:
        if b["id"] in {x["id"] for xs in roots.values() for x in xs}:
            continue
        restated = roots.get(b["id"], [])
        if restated:
            last = restated[-1]  # the latest restatement carries the freshest grade
            b = {**b, **{k: last[k] for k in ("status", "verdict", "evidence_kind", "evidence") if k in last},
                 "evidence_page": last.get("evidence_page"), "evidence_url": last.get("evidence_url"),
                 "restated": [{"period": x["period"], "page": x["page"], "url": x["url"]} for x in restated]}
        ledger_rows.append(b)
    ledger.recheck(ledger_rows, src["quarters"])           # the grading rules a model can break, enforced in code
    hard = [b for b in ledger_rows if b.get("hard")]
    score = {s: sum(1 for b in hard if b["status"] == s) for s in ("kept", "partly", "missed", "quiet", "pending", "unclear")}
    usage = _usage()
    return {
        **{k: src[k] for k in ("symbol", "name", "basis", "source", "asof", "snapshot", "quarters")},
        "calls": [{"period": c["period"], "url": c["url"], "pages": c.get("pages"), "found": len(c["promises"]),
                   "dropped": c.get("dropped_unverified", 0), "soft": c.get("soft_count", 0), "error": c.get("error")} for c in calls],
        "ledger": ledger_rows,
        "open": calls[-1]["promises"] if calls else [],
        "score": score,
        "read": graded.get("read", ""), "questions": graded.get("questions", []),
        "bull": graded.get("bull", []), "bear": graded.get("bear", []),
        "usage": usage,
    }

def _usage():
    recs, llm.METER[:] = list(llm.METER), []
    live = [r for r in recs if not r["cached"]]
    return {"calls": len(recs), "live_calls": len(live),
            "tokens_in": sum(r["in"] for r in recs), "tokens_out": sum(r["out"] for r in recs),
            "usd_if_billed": round(sum(llm.usd(r["model"], r["in"], r["out"]) for r in recs), 4),
            "by_model": {m: sum(r["in"] + r["out"] for r in recs if r["model"] == m) for m in {r["model"] for r in recs}}}

def run(symbol, today=None):
    llm.METER[:] = []
    src = sources(symbol, today)
    with ThreadPoolExecutor(max_workers=3) as ex:
        calls = list(ex.map(promises_for, src["transcripts"]))
    good = [c for c in calls if not c.get("error")]
    calls = (good[:N_CALLS] if len(good) >= 2 else calls[:N_CALLS])
    graded = grade(src, calls)
    return assemble(src, calls, graded)
