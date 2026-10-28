"""Download a PDF once, keep per-page text. Page numbers are what citations point to."""
import hashlib, io, re, zipfile, requests, pymupdf
from .. import config

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
CACHE = config.CACHE_DIR / "pdf"
CACHE.mkdir(parents=True, exist_ok=True)

class FetchError(RuntimeError):
    pass

def fetch(url, max_mb=40):
    p = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
    if p.exists():
        return p.read_bytes()
    headers = {"User-Agent": UA}
    if "nseindia" in url:
        headers["Referer"] = "https://www.nseindia.com/"
    try:
        r = requests.get(url, headers=headers, timeout=40)
    except requests.RequestException as e:
        raise FetchError(f"could not reach {url}: {e}")
    if r.status_code != 200 or len(r.content) > max_mb * 1e6:
        raise FetchError(f"{r.status_code} for {url}")
    data = r.content
    if url.endswith(".zip") or data[:2] == b"PK":   # NSE sometimes wraps the PDF in a zip
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".pdf")]
            if not names:
                raise FetchError("zip without pdf")
            data = z.read(names[0])
    if not data.startswith(b"%PDF"):
        raise FetchError(f"not a pdf: {url}")
    p.write_bytes(data)
    return data

def pages(url, max_pages=None):
    """List of page texts, 1-indexed by position+1."""
    doc = pymupdf.open(stream=fetch(url), filetype="pdf")
    n = doc.page_count if max_pages is None else min(doc.page_count, max_pages)
    return [doc[i].get_text() for i in range(n)]

def paged_text(page_list, start=1):
    """Text with explicit page markers so the model can cite pages."""
    return "\n".join(f"\n[[PAGE {i}]]\n{t.strip()}" for i, t in enumerate(page_list, start=start))

def _norm(s):
    return re.sub(r"[^a-z0-9%.]+", " ", s.lower()).strip()

def verify_quote(quote, page_list, page):
    """True if the quote really appears on the cited page (or the next one, for page breaks).

    Exact match after normalising punctuation and spacing; otherwise a strict fuzzy check that
    allows the model's small slips (a dropped 'uh', a changed comma) but not a paraphrase.
    Returns the page where it was found, or None.
    """
    q = _norm(quote)
    if len(q) < 12:
        return None
    candidates = [page] + [p for p in (page + 1, page - 1) if p != page]
    for p in candidates:
        if 1 <= p <= len(page_list):
            txt = _norm(page_list[p - 1])
            if p + 1 <= len(page_list):
                txt += " " + _norm(page_list[p])[:600]
            if q in txt:
                return p
            if _fuzzy_in(q, txt):
                return p
    for i, t in enumerate(page_list, start=1):  # model got the page wrong but the quote is real
        if q in _norm(t):
            return i
    return None

def _fuzzy_in(q, txt, threshold=0.9):
    import difflib
    words = q.split()
    if len(words) < 4:
        return False
    anchor = " ".join(words[:3])
    i = txt.find(anchor)
    if i < 0:
        anchor = " ".join(words[-3:]); j = txt.find(anchor)
        if j < 0:
            return False
        i = max(0, j - len(q))
    window = txt[i:i + int(len(q) * 1.3)]
    return difflib.SequenceMatcher(None, q, window).ratio() >= threshold
