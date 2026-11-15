"""The sha256 of every request classify would send for the 24 labelled filings, with the model and the fetch stubbed and
a stand-in letter, so how a request is built (how much of a filing goes in, the letter's cut) is fingerprinted, not
only the call's text. The gate runs it on this tree and, for a validated commit, on that commit's code.
    python3 -I evals/render_classify.py <root to import finn from> <classification.json>"""
import hashlib, json, sys
sys.path.insert(0, sys.argv[1])
from finn import classify, llm
from finn.sources import pdf
LETTER = "Ref: NSE. Dear Sir, Subject: Intimation under Regulation 30. " + "The company informs the exchange of the matter set out here in full. " * 30
sent = []
llm.generate = lambda prompt, **k: sent.append(prompt) or []
pdf.pages = lambda url, *a, **k: [LETTER]
rows = [{k: v for k, v in x.items() if not k.startswith("label_")} for x in json.load(open(sys.argv[2]))]
classify.classify(rows)
print(json.dumps([hashlib.sha256(p.encode()).hexdigest() for p in sent]))
