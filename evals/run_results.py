"""Cross-check the results first cut (parsed from NSE XBRL) against screener.in's quarterly table,
which is compiled independently from the same filings. Two sources agreeing within 1% is the test.

EBITDA is compared with screener's "Operating Profit", which is defined the same way
(revenue minus operating costs, before other income). Banks are skipped for EBITDA.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import numbers, results
from finn.sources import screener

ROOT = pathlib.Path(__file__).resolve().parent.parent
syms = [p["symbol"] for p in json.loads((ROOT / "data" / "portfolio.json").read_text())]
ok = total = 0
rows = []
for s in syms:
    try:
        r = results.first_cut(s)
    except Exception as e:
        print(f"{s:11} no XBRL ({str(e)[:60]})"); continue
    if not r:
        print(f"{s:11} no XBRL"); continue
    c = screener.company(s)
    if c["basis"] != r["basis"]:
        print(f"{s:11} basis differs (xbrl {r['basis']}, screener {c['basis']}), skipped"); continue
    q = numbers.quarter_table(c, 1)[-1]
    want = {"revenue": q["rev"], "pbt": q["pbt"], "pat": q["pat"], "ebitda": None if r["bank"] else q["op"]}  # lenders' NII is defined differently on screener
    line = []
    for l in r["lines"]:
        w = want.get(l["key"])
        if w is None or l["value"] is None:
            continue
        total += 1
        good = abs(l["value"] - w) <= max(1.0, abs(w) * 0.01)
        ok += good
        line.append(f"{l['key']} {l['value']:.0f}/{w:.0f}{'' if good else ' X'}")
    print(f"{s:11} {r['quarter']} {'  '.join(line)}")
print(f"\nagree within 1%: {ok}/{total} = {ok/total:.0%}")
