"""Accuracy of filing triage on hand-labelled real filings (evals/classification.json).

Labels were set by reading each filing, using the tier policy in finn/classify.py.
Category accuracy uses the reference document's categories. Tier is what decides whether
the investor gets interrupted, so it's the number that matters more.
"""
import copy, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import classify, numbers, triage
from finn.sources import screener

cases = json.loads((pathlib.Path(__file__).parent / "classification.json").read_text())
rows = copy.deepcopy(cases)
classify.classify(rows)
names, ttm = {}, {}
for r in rows:
    if r["symbol"] not in names:
        c = screener.company(r["symbol"])
        names[r["symbol"]] = c["name"]
        rev = [q["rev"] for q in numbers.quarter_table(c, 4) if q["rev"]]
        ttm[r["symbol"]] = sum(rev) if len(rev) == 4 else None
triage.enrich(rows, names, ttm)

cat = sum(r["category"] == r["label_category"] for r in rows)
tier = sum(r["tier"] == r["label_tier"] for r in rows)
missed_act = [r for r in rows if r["label_tier"] == "act" and r["tier"] != "act"]
false_act = [r for r in rows if r["label_tier"] != "act" and r["tier"] == "act"]
print(f"filings: {len(rows)}")
print(f"category: {cat}/{len(rows)} = {cat/len(rows):.0%}")
print(f"tier:     {tier}/{len(rows)} = {tier/len(rows):.0%}")
print(f"should have interrupted but didn't: {len(missed_act)}")
print(f"interrupted when it shouldn't have: {len(false_act)}")
for r in rows:
    if r["category"] != r["label_category"] or r["tier"] != r["label_tier"]:
        print(f"  {r['symbol']:10} {r['desc'][:28]:28} got {r['category']}/{r['tier']}  want {r['label_category']}/{r['label_tier']}")
