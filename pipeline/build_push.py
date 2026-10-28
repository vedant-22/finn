"""Build the push snapshot: every filing across the portfolio for the last 30 days, sorted into
tiers, with results and management changes enriched, plus 45 sessions of EOD data.

Run after market close:  python3 pipeline/build_push.py
Writes web/public/data/push.json. The app filters it by the window and thresholds the user picks.
"""
import datetime as dt, json, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import classify, eod, explain, llm, numbers, people, results, research
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
        p["name"] = c["name"]; p["mcap"] = c["ratios"].get("Market Cap")
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

    def enrich_people(x):
        try:
            x["people"] = people.from_filing(names.get(x["symbol"], x["sm_name"]), x["attchmntFile"])
        except (pdf.FetchError, llm.LLMError, Exception) as e:
            x["people"] = []; print("people fail", x["symbol"], str(e)[:100])
        # How loud: a CFO leaving interrupts you; a new company secretary doesn't.
        ranks = [p["seniority"] for p in x["people"]]
        if "top" in ranks:
            x["tier"] = "act"
        elif "board" in ranks or "senior" in ranks:
            x["tier"] = "note"
        elif ranks:
            x["tier"] = "fold"
        else:
            x["tier"] = "note"  # couldn't read the filing; show it, but don't interrupt
    mg = [x for x in rows if x["category"] == "management_change" and x["tier"] != "fold"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(enrich_people, mg))

    # Filings whose subject line is empty boilerplate get read, and sized against the company.
    ttm = {p["symbol"]: p.get("ttm_rev") for p in portfolio}
    def enrich_line(x):
        try:
            e = explain.explain(names.get(x["symbol"], x["sm_name"]), x["desc"], x["attchmntFile"])
        except Exception as ex:
            print("explain fail", x["symbol"], str(ex)[:80]); return
        x["line"] = e.get("line", "")
        amt = e.get("amount_cr")
        if amt and ttm.get(x["symbol"]):
            x["amount_cr"] = amt
            x["pct_rev"] = round(amt / ttm[x["symbol"]] * 100, 2)
        # Sizing rule: a deal, demand, penalty or raise worth under 0.5% of a year's revenue doesn't interrupt
        # you, and neither does a legal matter the filing itself calls routine unless it's over 1%. One-line note instead.
        pct = x.get("pct_rev")
        small = pct is not None and pct < 0.5
        routine_legal = x["category"] == "litigation" and e.get("routine") and (pct is None or pct < 1)
        if x["tier"] == "act" and x["category"] in ("litigation", "M&A", "fund_raise", "capex") and (small or routine_legal):
            x["tier"] = "note"; x["downgraded"] = "small"
    vague = [x for x in rows if x["tier"] in ("act", "note") and not x.get("line") and x["category"] in
             ("litigation", "M&A", "fund_raise", "capex", "press_release", "credit_rating", "insider_trading", "dividend")]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(enrich_line, vague))

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
    out = {"asof": now.isoformat(timespec="minutes"), "portfolio": portfolio, "filings": filings, "eod": hist,
           "usage": research._usage()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "push.json").write_text(json.dumps(out, separators=(",", ":")))
    tiers = {t: sum(1 for f in filings if f["tier"] == t) for t in ("act", "note", "fold")}
    print("wrote push.json", tiers, out["usage"])

if __name__ == "__main__":
    main()
