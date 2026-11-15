"""Print a fixed random sample of graded promises with everything needed to check them by hand:
the promise quote, the verdict, the evidence, and the company's quarterly numbers.
My verdicts on the sample go in evals/grades_review.md."""
import json, pathlib, random
ROOT = pathlib.Path(__file__).resolve().parent.parent
random.seed(3)
rows = []
for f in sorted((ROOT / "web/public/data/companies").glob("*.json")):
    c = json.loads(f.read_text())
    for p in c["ledger"]:
        if p.get("hard") and p["status"] in ("kept", "missed", "partly", "quiet"):
            rows.append((c, p))
for c, p in random.sample(rows, min(20, len(rows))):
    q = " | ".join(f"{r['q']}: rev {r['rev']} opm {r['opm']} pat {r['pat']}" for r in c["quarters"][-5:])
    print(f"## {c['symbol']} [{p['period']} p{p['page']}] {p['target']} by {p['by_when']}\n"
          f"said: {p['quote']}\nstatus: {p['status']}  verdict: {p['verdict']}\n"
          f"evidence ({p['evidence_kind']}): {p['evidence']}\nquarters: {q}\n")
