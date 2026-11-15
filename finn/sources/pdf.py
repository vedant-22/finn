"""Download a PDF once, keep per-page text. Page numbers are what citations point to."""
import hashlib, io, re, time, zipfile, requests, pymupdf
from urllib.parse import urljoin, urlsplit
from .. import config

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
CACHE = config.CACHE_DIR / "pdf"
CACHE.mkdir(parents=True, exist_ok=True)

class FetchError(RuntimeError):
    """A fixed code for the client (unreachable, not_pdf, too_large); the URL and upstream detail are for the log only."""
    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail

# Its own session: no proxy or netrc from the environment, and redirects are followed here, one checked hop at a time.
SESSION = requests.Session()
SESSION.trust_env = False
MAX_HOPS, DEADLINE_S = 3, 45


def _check_hop(url):
    """A URL FINN may fetch a filing from: http(s), the default port, no user name or password."""
    u = urlsplit(url)
    try:
        port = u.port
    except ValueError:
        port = -1
    if u.scheme not in ("http", "https") or not u.hostname or "@" in u.netloc or port not in (None, {"http": 80, "https": 443}[u.scheme]):
        raise FetchError("unreachable", f"refused URL: {url[:200]}")


def _download(url, cap, deadline, limit_s=DEADLINE_S):
    headers = {"User-Agent": UA}
    if "nseindia" in url:
        headers["Referer"] = "https://www.nseindia.com/"
    for _ in range(MAX_HOPS + 1):
        _check_hop(url)
        try:
            r = SESSION.get(url, headers=headers, timeout=40, stream=True, allow_redirects=False)
        except requests.RequestException as e:
            raise FetchError("unreachable", f"{type(e).__name__} for {url}")
        with r:
            if r.is_redirect:
                url = urljoin(url, r.headers.get("location", ""))
                continue
            if r.status_code != 200:
                raise FetchError("unreachable", f"{r.status_code} for {url}")
            if int(r.headers.get("content-length") or 0) > cap:
                raise FetchError("too_large", url)
            data = bytearray()
            for chunk in r.iter_content(64 * 1024):
                data += chunk
                if len(data) > cap:
                    raise FetchError("too_large", url)
                if time.monotonic() > deadline:
                    raise FetchError("unreachable", f"over {limit_s}s: {url}")
            return bytes(data)
    raise FetchError("unreachable", f"more than {MAX_HOPS} redirects: {url}")


def fetch(url, max_mb=40, deadline_s=DEADLINE_S):
    """The API keeps the defaults (40 MB, 45 s); the batch build of annual reports passes its own (80 MB, 180 s)."""
    p = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
    if p.exists():
        return p.read_bytes()
    cap = int(max_mb * 1e6)
    data = _download(url, cap, time.monotonic() + deadline_s, deadline_s)
    if url.endswith(".zip") or data[:2] == b"PK":   # NSE sometimes wraps the PDF in a zip
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = [n for n in z.namelist() if n.lower().endswith(".pdf")]
                if not names:
                    raise FetchError("not_pdf", f"zip without pdf: {url}")
                if z.getinfo(names[0]).file_size > cap:
                    raise FetchError("too_large", f"zip member: {url}")
                with z.open(names[0]) as f:      # read no more than the cap, whatever the header claims
                    data = f.read(cap + 1)
                if len(data) > cap:
                    raise FetchError("too_large", f"zip member: {url}")
        except zipfile.BadZipFile:
            raise FetchError("not_pdf", f"bad zip: {url}")
    if not data.startswith(b"%PDF"):
        raise FetchError("not_pdf", url)
    p.write_bytes(data)
    return data

_FIXTURE = {}

def _fixture():
    """Page text checked in for the evals (FINN_PAGES=evals/fixtures/pages.json.gz), so they run where NSE is blocked."""
    import gzip, json, os
    path = os.environ.get("FINN_PAGES")
    if path and path not in _FIXTURE:
        _FIXTURE[path] = json.loads(gzip.decompress(open(path, "rb").read()))
    return _FIXTURE.get(path, {}) if path else {}

def pages(url, max_pages=None):
    """List of page texts, 1-indexed by position+1."""
    got = _fixture().get(url)
    if got is not None:
        return got[:max_pages]
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
        i = max(0, j + len(anchor) - int(len(q) * 1.15))
    window = txt[i:i + int(len(q) * 1.15)]
    # Fuzzy matching may forgive a dropped filler word or a swapped synonym, never a changed figure
    # or a flipped meaning: every number in the quote must be in this stretch of the page exactly,
    # and the quote can't add or drop a negation.
    for n in re.findall(r"\d[\d.,%]*", q):
        if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", window):
            return False
    neg = lambda t: len(re.findall(r"\b(not|no|never|nt|cannot|without)\b", t))
    if neg(q) != neg(window[:len(q) + 20]):
        return False
    # Share of the quote's characters found, in order, in the page text near the anchor.
    blocks = difflib.SequenceMatcher(None, q, window, autojunk=False).get_matching_blocks()
    return sum(b.size for b in blocks) / len(q) >= threshold
