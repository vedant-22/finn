"""Everything here is arithmetic on filed numbers. No model is involved, so these never hallucinate."""

def _series(table, row):
    if not table:
        return []
    for k, v in table["rows"].items():
        if k.lower().startswith(row.lower()):
            return v
    return []

def _pct(a, b):
    if a is None or b in (None, 0):
        return None
    return round((a / b - 1) * 100, 1)

def _cagr(first, last, years):
    if not first or not last or first <= 0 or last <= 0 or years <= 0:
        return None
    return round(((last / first) ** (1 / years) - 1) * 100, 1)

def is_financial(c):
    # Banks and NBFCs report "Revenue"/"Financing Profit" on screener instead of Sales/Operating Profit.
    return bool(_series(c["quarters"], "Revenue")) and not _series(c["quarters"], "Sales")

def quarter_table(c, n=8):
    q = c["quarters"]
    cols = q["cols"][-n:]
    fin = is_financial(c)
    rev = _series(q, "Revenue" if fin else "Sales")[-n:]
    if fin:
        # For lenders, net interest income is the useful "operating" line; screener's Financing Profit is after provisions.
        op = [(r - i) if r is not None and i is not None else None
              for r, i in zip(_series(q, "Revenue"), _series(q, "Interest"))][-n:]
        opm = _series(q, "Gross NPA")[-n:]
    else:
        op = _series(q, "Operating Profit")[-n:]
        opm = _series(q, "OPM")[-n:]
    pbt = _series(q, "Profit before tax")[-n:]
    pat = _series(q, "Net Profit")[-n:]
    rows = []
    for i, col in enumerate(cols):
        j = len(q["cols"]) - n + i
        yoy_base = _series(q, "Revenue" if fin else "Sales")[j - 4] if j - 4 >= 0 else None
        rows.append({"q": col, "rev": _at(rev, i), "op": _at(op, i), "opm": _at(opm, i), "pbt": _at(pbt, i), "pat": _at(pat, i),
                     "rev_yoy": _pct(_at(rev, i), yoy_base)})
    return rows

def _at(xs, i):
    return xs[i] if i < len(xs) else None

def snapshot(c):
    """Headline numbers, trajectory, balance sheet and cash quality from the standardised tables."""
    a, b, cf, rt = c["annual"], c["balance"], c["cashflow"], c["ratio_table"]
    fin = is_financial(c)
    years = [y for y in (a["cols"] if a else []) if y.startswith(("Mar", "Dec", "Jun", "Sep"))]
    rev = _series(a, "Revenue" if fin else "Sales")[:len(years)]
    pat = _series(a, "Net Profit")[:len(years)]
    opm = [] if fin else _series(a, "OPM")[:len(years)]
    cfo = _series(cf, "Cash from Operating")
    fcf = _series(cf, "Free Cash Flow")
    borrowings = _series(b, "Borrowings")
    equity = [((x or 0) + (y or 0)) for x, y in zip(_series(b, "Equity Capital"), _series(b, "Reserves"))]
    ccc = _series(rt, "Cash Conversion Cycle")
    wcd = _series(rt, "Working Capital Days")
    roce = _series(rt, "ROCE")
    n5 = min(5, len(years) - 1)
    last5 = slice(-5, None)
    cfo5, pat5 = [x for x in cfo[last5] if x is not None], [x for x in pat[-5:] if x is not None]
    conv = round(sum(cfo5) / sum(pat5) * 100) if cfo5 and pat5 and sum(pat5) > 0 and not fin else None
    de = round(borrowings[-1] / equity[-1], 2) if borrowings and equity and equity[-1] else None
    return {
        "financial": fin,
        "years": years[-6:],
        "rev": rev[-6:], "pat": pat[-6:], "opm": opm[-6:],
        "cfo": cfo[-6:], "fcf": fcf[-6:],
        "rev_cagr5": _cagr(rev[-n5 - 1] if len(rev) > n5 else None, rev[-1] if rev else None, n5),
        "pat_cagr5": _cagr(pat[-n5 - 1] if len(pat) > n5 else None, pat[-1] if pat else None, n5),
        "cash_conversion5": conv,
        "debt": borrowings[-1] if borrowings else None,
        "de": de,
        "ccc": ccc[-6:], "wc_days": wcd[-6:], "roce": roce[-6:],
        "mcap": c["ratios"].get("Market Cap"), "pe": c["ratios"].get("Stock P/E"), "price": c["ratios"].get("Current Price"),
    }

def numbers_for_prompt(c):
    rows = quarter_table(c, 8)
    if is_financial(c):
        out = ["Quarter | Revenue (interest earned) | Net interest income | Gross NPA % | PBT | PAT | Revenue YoY %"]
    else:
        out = ["Quarter | Revenue | Operating profit (EBITDA) | OPM % | PBT | PAT | Revenue YoY %"]
    for r in rows:
        out.append(f"{r['q']} | {r['rev']} | {r['op']} | {r['opm']} | {r['pbt']} | {r['pat']} | {r['rev_yoy']}")
    s = snapshot(c)
    out.append("")
    out.append("Year | Revenue | PAT | OPM % | Cash from operations")
    for i, y in enumerate(s["years"]):
        out.append(f"{y} | {_at(s['rev'], i)} | {_at(s['pat'], i)} | {_at(s['opm'], i)} | {_at(s['cfo'], i)}")
    out.append(f"Borrowings latest: {s['debt']}; Debt/Equity: {s['de']}")
    return "\n".join(out)
