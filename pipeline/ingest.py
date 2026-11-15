"""Run the ledger by hand.

    python3 pipeline/ingest.py poll [--until 2026-11-12] [--days 3] [--archive]
    python3 pipeline/ingest.py drain [--cap-results 50]
    python3 pipeline/ingest.py status
    python3 pipeline/ingest.py view          # filings in push.json's shape, to data/out/view.json
    python3 pipeline/ingest.py day 2026-11-12 [--cap-results 50]   # poll + drain one whole-market day, write evals/ingest_day.txt

No high-water mark: poll re-reads its lookback and inserts are idempotent. The ledger is data/cache/ledger.sqlite.
"""
import argparse, collections, datetime as dt, gzip, json, pathlib, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import llm, triage
from finn.ingest import steps, store, worker
from finn.sources import nse, pdf

SNAPSHOT = ROOT / "web/public/data/push.json"
USD_INR = 88   # assumed, not looked up

def poll(db, until, days, archive=False):
    new = 0
    for k in range(days):
        d = until - dt.timedelta(days=k)
        raw = ROOT / "data/raw/filings" / f"{d}.json.gz"
        rows = json.loads(gzip.decompress(raw.read_bytes())) if archive else nse.announcements(d, d)
        new += sum(store.put(db, x) > 0 for x in rows)
    return new

def view(db):
    out = []
    for ev in store.latest(db):
        x, runs = json.loads(ev["payload"]), store.runs_of(db, ev)
        t = json.loads(runs["tier"]["output"]) if "tier" in runs and runs["tier"]["status"] == "done" else None
        if not t:
            continue
        res = runs.get("results")
        cut = res and res["status"] == "done" and json.loads(res["output"] or "null")
        out.append({"id": x["seq_id"], "symbol": x["symbol"], "at": nse._parse_dt(x["an_dt"]).isoformat(), "desc": x["desc"],
                    "subject": (x.get("attchmntText") or "")[:400], "url": x["attchmntFile"], **t,
                    **({"results": store.fact(db, cut["fact"])} if cut else {})})
    return sorted(out, key=lambda f: f["at"], reverse=True)

def cost_estimate(st):
    """What the parked model work would have cost: the snapshot's mean per model call, read in batches of 20, and
    people and explain behind a parked read through the snapshot's shares of read filings. Explain's share is a range:
    at least the act deals (explained whatever read says), at most every act or note filing explain could take,
    as if read's line always came back empty. Returns (low calls, high calls, per call)."""
    snap = json.loads(SNAPSHOT.read_text())
    per_call = snap["usage"]["usd_if_billed"] / snap["usage"]["calls"]
    read = [f for f in snap["filings"] if f["how"] == "model"]
    share = lambda ok: sum(map(ok, read)) / len(read)
    people = share(lambda f: f["category"] == "management_change")
    lo = share(lambda f: f["tier"] == "act" and f["category"] in triage.SIZEABLE)
    hi = share(lambda f: f["tier"] in ("act", "note") and f["category"] in triage.SIZEABLE + ("press_release", "credit_rating", "insider_trading", "dividend"))
    parked = lambda s: st.get((s, "parked"), 0)
    base = -(-parked("read") // 20) + parked("people") + parked("explain") + parked("read") * people
    return base + parked("read") * lo, base + parked("read") * hi, per_call

def cost_line(st):
    lo, hi, per_call = cost_estimate(st)
    return (f"cost had a key been there (estimate): {lo:.0f}-{hi:.0f} model calls x ${per_call:.4f} (the 28 Oct snapshot's mean per call) = "
            f"${lo * per_call:.2f}-{hi * per_call:.2f}, about Rs {lo * per_call * USD_INR:.0f}-{hi * per_call * USD_INR:.0f} at Rs {USD_INR} "
            f"to the dollar (assumed); flash-lite list price as of Aug 2026 (finn/config.py)")

def day(db, d, cap):
    fetched = []
    real = pdf.pages
    pdf.pages = lambda *a, **k: fetched.append(a[0]) or real(*a, **k)
    t0 = time.time()
    poll(db, d, 1)
    worker.drain(db, cap={"results": cap})
    wall = time.time() - t0
    pdf.pages = real
    st = store.status(db)
    evs = store.latest(db)
    rules = sum(1 for ev in evs for r in [store.runs_of(db, ev).get("rules")] if r and r["output"] not in (None, "null"))
    model_steps = ("read", "people", "explain")
    cuts = db.execute("SELECT COUNT(*) FROM runs WHERE step='results' AND status='done' AND output!='null'").fetchone()[0]
    by_status = collections.Counter()
    for (_, k), v in st.items():
        by_status[k] += v
    n_runs = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    dead = collections.Counter(r["error"] for r in db.execute("SELECT error FROM runs WHERE step='results' AND status='dead'"))
    lines = [f"Whole-market day {d}, no model key. python3 pipeline/ingest.py day {d} --cap-results {cap}",
             f"filings {len(evs)}, companies {len({ev['symbol'] for ev in evs})}",
             f"settled by rules {rules} of {len(evs)}",
             f"model steps parked {sum(st.get((s, 'parked'), 0) for s in model_steps)}, blocked behind them {sum(v for (s, k), v in st.items() if k == 'blocked')}, PDFs fetched {len(fetched)}",
             f"results cuts done {cuts}, "
             f"not_yet {st.get(('results', 'not_yet'), 0)}, dead {dict(dead)}, left by the cap {st.get(('results', 'pending'), 0)}",
             f"wall time {wall:.0f} s",
             f"statuses {dict(by_status)}: they sum to {sum(by_status.values())}, and the ledger holds {n_runs} runs",
             cost_line(st)]
    (ROOT / "evals/ingest_day.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("date", nargs="?")
    ap.add_argument("--until", default=str(dt.date.today())); ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--archive", action="store_true"); ap.add_argument("--cap-results", type=int, default=None)
    a = ap.parse_args()
    db = store.connect() if a.cmd != "day" else None
    if a.cmd == "poll":
        print(poll(db, dt.date.fromisoformat(a.until), a.days, a.archive), "new revisions")
    elif a.cmd == "drain":
        print(worker.drain(db, cap={"results": a.cap_results} if a.cap_results else None))
    elif a.cmd == "status":
        for (s, k), v in sorted(store.status(db).items()):
            print(f"{s:8} {k:9} {v}")
    elif a.cmd == "view":
        (ROOT / "data/out").mkdir(parents=True, exist_ok=True)
        (ROOT / "data/out/view.json").write_text(json.dumps(view(db), indent=1))
        print("wrote data/out/view.json")
    elif a.cmd == "cost":   # the cost line again from a day's ledger, without polling
        print(cost_line(store.status(store.connect(store.PATH.with_name(f"ledger_{a.date}.sqlite")))))
    elif a.cmd == "day":   # its own ledger file, so the day's counts are the day's alone
        day(store.connect(store.PATH.with_name(f"ledger_{a.date}.sqlite")), dt.date.fromisoformat(a.date), a.cap_results or 50)
