"""Does the quote check catch what it should?

Must pass: real quotes; small slips (a dropped word, lost commas); single-word synonym swaps that keep
the meaning ("will" -> "shall"). Must fail: a changed number, an added "not", and two real sentences
stitched together from different pages. The line we draw: tolerate copying noise, reject anything that
changes what management committed to."""
import json, pathlib, random, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn.sources import pdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
random.seed(11)
# The sample is pinned: drawn once from the ledgers at the commit that recorded quotes_result.txt. Sampling the
# live ledgers made the number drift as they were rebuilt (68/81 on 13 Nov), which the gate caught.
real = json.loads((ROOT / "evals/quotes_sample.json").read_text())["real"]
sample = random.sample(real, 15)

def bump(q):
    m = re.search(r"\d+", q)
    return q[:m.start()] + str(int(m.group()) + 3) + q[m.end():] if m else None

PARA = {"we": "the company", "expect": "anticipate", "will": "shall", "growth": "expansion", "margin": "profitability",
        "next": "coming", "year": "period", "should": "would", "around": "about", "target": "aim"}

cases = []
for p in sample:
    pages = pdf.pages(p["url"], max_pages=60)
    q = p["quote"]
    cases.append(("real", q, pages, p["page"], True))
    words = q.split()
    if len(words) > 8:  # a dropped filler word and different punctuation: still the same sentence
        cases.append(("slip", " ".join(words[:3] + words[4:]).replace(",", ""), pages, p["page"], True))
    para = " ".join(PARA.get(w.lower(), w) for w in words)
    if para != q:
        cases.append(("synonym swap", para, pages, p["page"], True))
    m = re.search(r"\b(will|is|are|expect|should|would)\b", q)
    if m:
        cases.append(("negation added", q[:m.end()] + " not" + q[m.end():], pages, p["page"], False))
    b = bump(q)
    if b:
        cases.append(("number changed", b, pages, p["page"], False))
    other = [x for x in real if x["url"] == p["url"] and x["page"] != p["page"]]
    if other:
        o = other[0]["quote"].split()
        cases.append(("stitched", " ".join(words[: len(words) // 2] + o[len(o) // 2:]), pages, p["page"], False))

by = {}
for kind, q, pages, page, want in cases:
    got = pdf.verify_quote(q, pages, page) is not None
    t = by.setdefault(kind, [0, 0]); t[0] += got == want; t[1] += 1
    if got != want:
        print(f"WRONG [{kind}] expected {'pass' if want else 'fail'}: {q[:110]}")
tot = sum(v[0] for v in by.values()), sum(v[1] for v in by.values())
for k, (a, n) in by.items():
    print(f"{k:15} {a}/{n}")
print(f"overall {tot[0]}/{tot[1]} = {tot[0]/tot[1]:.0%}")
