"""Rebuild pages.json.gz: the text of every PDF page the offline evals read (answer, agent, quotes), from the local
cache or NSE. The gate points FINN_PAGES at it, so CI runs those evals where NSE blocks cloud addresses.

    python3 evals/fixtures/make_pages.py
"""
import gzip, json, pathlib, runpy, sys, tempfile, shutil
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from finn.sources import pdf

real, text = pdf.pages, {}
def recording(url, max_pages=None):
    out = real(url, max_pages=max_pages)
    if len(out) > len(text.get(url, [])):
        text[url] = out
    return out
pdf.pages = recording
keep = {f: (ROOT / "evals" / f).read_text() for f in ("answer_result.txt", "agent_result.txt", "quotes_result.txt")}
for script in ("run_answer.py", "run_agent.py", "run_quotes.py"):
    try:
        runpy.run_path(str(ROOT / "evals" / script), run_name="__main__")
    except SystemExit:
        pass
for f, t in keep.items():   # this run only records pages; the committed results stay as they were
    (ROOT / "evals" / f).write_text(t)
out = ROOT / "evals/fixtures/pages.json.gz"
out.write_bytes(gzip.compress(json.dumps(text, sort_keys=True).encode(), 9, mtime=0))
print(f"{len(text)} PDFs, {sum(map(len, text.values()))} pages, {out.stat().st_size / 1e6:.2f} MB")
