"""Build the push snapshot: every filing across the portfolio for the last 30 days, sorted into
tiers, with results and management changes enriched, plus 45 sessions of EOD data.

Run after market close:  python3 pipeline/build_push.py
Writes web/public/data/push.json. The app filters it by the window and thresholds the user picks.
"""
import datetime as dt, json, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import classify, eod, llm, numbers, results, research, triage
from finn.sources import nse, screener, pdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data"
DAYS = 30

def main():
    now = dt.datetime.now()
    portfolio = json.loads((ROOT / "data" / "portfolio.json").read_text())
    syms = {p["symbol"] for p in portfolio}
    llm.METER[:] = []

    rows, d = [], now.date() - dt.timedelta(days=DAYS)
    while d <= now.date():
        try:
            rows += [x for x in nse.announcements(d, d) if x["symbol"] in syms]
        except Exception as e:
            print("skip", d, e)
        d += dt.timedelta(days=1)
    print(len(rows), "filings")
    classify.classify(rows)

    names = {}
    for p in portfolio:
        c = screener.company(p["symbol"])
        names[p["symbol"]] = c["name"]
        p["name"] = c["name"]; p["mcap"] = c["ratios"].get("Market Cap")  # "short" comes from portfolio.json
        rev = [r["rev"] for r in numbers.quarter_table(c, 4) if r["rev"]]
        p["ttm_rev"] = sum(rev) if len(rev) == 4 else None

    # Results: one first cut per company per quarter, attached to the earliest results filing.
    seen = set()
    for x in sorted(rows, key=lambda r: nse._parse_dt(r["an_dt"])):
        if x["category"] == "results" and x["tier"] == "act" and x["symbol"] not in seen:
            try:
                x["results"] = results.first_cut(x["symbol"])
                seen.add(x["symbol"])
            except Exception as e:
                print("results fail", x["symbol"], e)

    ttm = {p["symbol"]: p.get("ttm_rev") for p in portfolio}
    triage.enrich(rows, names, ttm)

    hist = eod.history(syms, now.date(), sessions=45)

    filings = []
    for x in rows:
        filings.append({
            "id": x["seq_id"], "symbol": x["symbol"], "at": nse._parse_dt(x["an_dt"]).isoformat(),
            "desc": x["desc"], "subject": (x.get("attchmntText") or "")[:400], "url": x["attchmntFile"],
            "category": x["category"], "tier": x["tier"], "line": x.get("line", ""), "how": x.get("how"),
            **({"amount_cr": x["amount_cr"], "pct_rev": x["pct_rev"]} if x.get("amount_cr") else {}),
            **({"downgraded": x["downgraded"]} if x.get("downgraded") else {}),
            **({"results": x["results"]} if x.get("results") else {}),
            **({"people": x["people"]} if x.get("people") else {}),
        })
    filings.sort(key=lambda f: f["at"], reverse=True)
    # The book of holdings is invented for the demo (data/portfolio.json); the app says so while this is true
    out = {"asof": now.isoformat(timespec="minutes"), "synthetic": True, "portfolio": portfolio, "filings": filings, "eod": hist,
           "usage": research._usage()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "push.json").write_text(json.dumps(out, separators=(",", ":")))
    tiers = {t: sum(1 for f in filings if f["tier"] == t) for t in ("act", "note", "fold")}
    print("wrote push.json", tiers, out["usage"])

if __name__ == "__main__":
    main()
