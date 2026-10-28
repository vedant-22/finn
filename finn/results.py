"""Quarterly results from the exchange's XBRL, not from a model reading a PDF.

Revenue, EBITDA, PBT and PAT for the quarter, the quarter before, and the same quarter a year ago.
EBITDA isn't a line in Indian results, so we derive it the usual way:
    EBITDA = PBT before exceptional items + finance costs + depreciation − other income
For banks the four lines are total income, pre-provision operating profit, PBT and PAT.
"""
import datetime as dt, re
from .sources import nse

LIST = "https://www.nseindia.com/api/integrated-filing-results?index=equities&symbol={sym}&type=Integrated%20Filing-%20Financials"
OLD_LIST = "https://www.nseindia.com/api/corporates-financial-results?index=equities&symbol={sym}&period=Quarterly"

def _val(xml, tag, ctx="OneD"):
    m = re.search(rf'<in-[a-z-]+:{tag} contextRef="{ctx}"[^>]*>([^<]+)<', xml)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None

def parse(xml):
    cr = 1e7  # values are in rupees; show crore
    bank = _val(xml, "OperatingProfitBeforeProvisionAndContingencies") is not None
    lender = _val(xml, "InterestEarned") is not None
    if bank:
        rev = _val(xml, "InterestEarned")
        ebitda = _val(xml, "OperatingProfitBeforeProvisionAndContingencies")
        pbt = _val(xml, "ProfitLossFromOrdinaryActivitiesBeforeTax")
        pat = _val(xml, "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates") or _val(xml, "ProfitLossForThePeriod")
    else:
        rev = _val(xml, "RevenueFromOperations")
        pbt_pre = _val(xml, "ProfitBeforeExceptionalItemsAndTax")
        fc, da, oi = _val(xml, "FinanceCosts"), _val(xml, "DepreciationDepletionAndAmortisationExpense"), _val(xml, "OtherIncome")
        if lender:  # NBFCs: interest is the cost of goods, so EBITDA means nothing. Use net interest income.
            ebitda = (_val(xml, "InterestEarned") - (fc or 0))
        else:
            ebitda = (pbt_pre + (fc or 0) + (da or 0) - (oi or 0)) if pbt_pre is not None else None
        pbt = _val(xml, "ProfitBeforeTax")
        pat = _val(xml, "ProfitLossForPeriod")
    f = lambda v: round(v / cr, 1) if v is not None else None
    # One-offs that move PAT without the business moving: exceptional items and a tax credit.
    exc, tax = (None, None) if bank else (_val(xml, "ExceptionalItemsBeforeTax"), _val(xml, "TaxExpense"))
    return {"bank": bank or lender, "bank_kind": "bank" if bank else "lender" if lender else "", "revenue": f(rev), "ebitda": f(ebitda), "pbt": f(pbt), "pat": f(pat),
            "exceptional": f(exc), "tax": f(tax)}

def _qe(s):
    return dt.datetime.strptime(s.title(), "%d-%b-%Y").date()

def _shift(d, months):
    y, m = d.year, d.month + months
    while m <= 0:
        m += 12; y -= 1
    import calendar
    return dt.date(y, m, calendar.monthrange(y, m)[1])

def _fy_label(d):
    fy = d.year + 1 if d.month > 3 else d.year
    q = {6: 1, 9: 2, 12: 3, 3: 4}[d.month]
    return f"Q{q} FY{str(fy)[2:]}"

def first_cut(symbol, quarter_end=None):
    """Returns the headline table for the latest (or given) quarter, or None if XBRL isn't available."""
    rows = nse.get_json(LIST.format(sym=symbol), ttl_hours=6).get("data", [])
    if not rows:
        return None
    # Use the latest revision of each (quarter, basis) filing.
    best = {}
    for r in rows:
        k = (r["qe_Date"].upper(), r["consolidated"])
        if k not in best or r["type_Sub"] == "Revision":
            best[k] = r
    quarters = sorted({_qe(k[0]) for k in best}, reverse=True)
    qe = quarter_end or quarters[0]
    basis = "Consolidated" if (qe.strftime("%d-%b-%Y").upper(), "Consolidated") in best else "Standalone"

    def get(d):
        r = best.get((d.strftime("%d-%b-%Y").upper(), basis))
        if not r or not r.get("xbrl"):
            return None
        xml = nse.session().get(r["xbrl"], timeout=30).text
        return {**parse(xml), "q": _fy_label(d), "xbrl": r["xbrl"], "pdf": r.get("pdf_attach") if (r.get("pdf_attach") or "").lower().endswith(".pdf") else None, "filed": r.get("broadcast_Date")}

    cur, prev, yago = get(qe), get(_shift(qe, -3)), get(_shift(qe, -12))
    if not cur:
        return None
    lines = []
    for key, label in (("revenue", "Revenue"), ("ebitda", "EBITDA"), ("pbt", "PBT"), ("pat", "PAT")):
        v = cur[key]
        lines.append({"key": key, "label": {"bank": {"revenue": "Interest earned", "ebitda": "Pre-provision profit"}, "lender": {"ebitda": "Net interest income"}}.get(cur["bank_kind"], {}).get(key, label),
                      "value": v, "prev": prev and prev[key], "yago": yago and yago[key],
                      "qoq": _chg(v, prev and prev[key]), "yoy": _chg(v, yago and yago[key])})
    margin = round(cur["ebitda"] / cur["revenue"] * 100, 1) if cur["ebitda"] and cur["revenue"] and not cur["bank"] else None
    return {"quarter": cur["q"], "basis": basis.lower(), "bank": cur["bank"], "lines": lines, "ebitda_margin": margin,
            "prev_margin": round(prev["ebitda"] / prev["revenue"] * 100, 1) if prev and prev["ebitda"] and prev["revenue"] and not cur["bank"] else None,
            "yago_margin": round(yago["ebitda"] / yago["revenue"] * 100, 1) if yago and yago["ebitda"] and yago["revenue"] and not cur["bank"] else None,
            "source": {"xbrl": cur["xbrl"], "pdf": cur["pdf"], "filed": cur["filed"]},
            "compare": {"prev": prev and prev["q"], "yago": yago and yago["q"]},
            "one_offs": [o for o in (_one_off(x) for x in (cur, prev, yago) if x) if o]}

def _one_off(q):
    """Exceptional items over 5% of PBT, or a tax credit (negative tax), so a PAT swing can be read for what it is."""
    exc, tax, pbt = q.get("exceptional") or 0, q.get("tax"), q.get("pbt")
    big_exc = exc and pbt and abs(exc) >= 0.05 * abs(pbt)
    credit = tax is not None and tax < 0
    if not big_exc and not credit:
        return None
    return {"q": q["q"], "exceptional": exc if big_exc else None, "tax_credit": -tax if credit else None}

def _chg(a, b):
    if a is None or b in (None, 0):
        return None
    if b < 0:  # growth off a loss isn't meaningful as a percentage
        return None
    return round((a / b - 1) * 100, 1)
