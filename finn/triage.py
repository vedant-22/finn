"""After classification: read the filings that matter and set how loud each one is.

Management changes are ranked by who is moving. Deals, demands and raises are sized against
a year's revenue. This is where most of FINN's judgment about "what interrupts you" lives.
"""
from concurrent.futures import ThreadPoolExecutor
from . import explain, llm, people
from .sources import pdf

def enrich(rows, names, ttm):
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
    def enrich_line(x):
        try:
            e = explain.explain(names.get(x["symbol"], x["sm_name"]), x["desc"], x["attchmntFile"])
        except Exception as ex:
            print("explain fail", x["symbol"], str(ex)[:80]); return
        x["line"] = e.get("line") or x.get("line", "")
        amt = e.get("amount_cr")
        if amt and ttm.get(x["symbol"]):
            x["amount_cr"] = amt
            x["pct_rev"] = round(amt / ttm[x["symbol"]] * 100, 2)
        # Sizing rule: a deal, demand, penalty or raise worth under 0.5% of a year's revenue doesn't interrupt
        # you, and neither does a legal matter the filing itself calls routine unless it's over 1%. One-line note instead.
        pct = x.get("pct_rev")
        small = pct is not None and pct < 0.5
        routine_legal = x["category"] == "litigation" and e.get("routine") and (pct is None or pct < 1)
        # A deal or raise with no stated size that the filing itself presents as procedural
        # (a new shell subsidiary, a follow-on form) is routine too.
        routine_other = x["category"] != "litigation" and e.get("routine") and pct is None
        if x["tier"] == "act" and x["category"] in ("litigation", "M&A", "fund_raise", "capex") and (small or routine_legal or routine_other):
            x["tier"] = "note"; x["downgraded"] = "small"
    # Read anything that could interrupt and has a size, plus anything whose subject says nothing.
    sizeable = ("litigation", "M&A", "fund_raise", "capex")
    vague = [x for x in rows if (x["tier"] == "act" and x["category"] in sizeable) or
             (x["tier"] in ("act", "note") and not x.get("line") and x["category"] in
              sizeable + ("press_release", "credit_rating", "insider_trading", "dividend"))]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(enrich_line, vague))

