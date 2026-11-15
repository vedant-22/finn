"""screener.in company page: standardised financial tables and links to primary documents.

We only take numbers (which screener compiles from the company's own filings) and document links.
Screener's own prose ("About", "AI Summary") is not used anywhere.
"""
import hashlib, re, time, requests
from bs4 import BeautifulSoup
from .. import config

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
CACHE = config.CACHE_DIR / "screener"
CACHE.mkdir(parents=True, exist_ok=True)

class NotFound(Exception):
    pass

def _get(url, ttl_hours=12):
    p = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if p.exists() and time.time() - p.stat().st_mtime < ttl_hours * 3600:
        return p.read_text()
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
    if r.status_code == 404:
        raise NotFound(url)
    r.raise_for_status()
    p.write_text(r.text)
    return r.text

def _num(s):
    s = s.replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None

def _table(soup, section_id):
    sec = soup.find(id=section_id)
    if not sec:
        return None
    t = sec.find("table", class_="data-table")
    if not t:
        return None
    cols = [th.get_text(" ", strip=True) for th in t.find("thead").find_all("th")][1:]
    rows = {}
    for tr in t.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        name = tds[0].get_text(" ", strip=True).replace("\xa0", " ").rstrip("+").strip()
        rows[name] = [_num(td.get_text(strip=True)) for td in tds[1:]]
    return {"cols": cols, "rows": rows}

def company(symbol):
    """Fetch consolidated figures, falling back to standalone when a company has no subsidiaries."""
    sym = symbol.upper().strip()
    basis = "consolidated"
    html = _get(f"https://www.screener.in/company/{sym}/consolidated/")
    soup = BeautifulSoup(html, "html.parser")
    q = _table(soup, "quarters")
    if not q or not q["rows"] or all(v is None for v in next(iter(q["rows"].values()))):
        basis = "standalone"
        html = _get(f"https://www.screener.in/company/{sym}/")
        soup = BeautifulSoup(html, "html.parser")
        q = _table(soup, "quarters")
    if not q:
        raise NotFound(sym)
    name = soup.find("h1").get_text(strip=True) if soup.find("h1") else sym
    ratios = {}
    for li in soup.select("#top-ratios li"):
        k = li.find("span", class_="name"); v = li.find("span", class_="number")
        if k and v:
            ratios[k.get_text(strip=True)] = _num(v.get_text(strip=True))
    return {
        "symbol": sym, "name": name, "basis": basis,
        "source": f"https://www.screener.in/company/{sym}/" + ("consolidated/" if basis == "consolidated" else ""),
        "ratios": ratios,
        "quarters": q,
        "annual": _table(soup, "profit-loss"),
        "balance": _table(soup, "balance-sheet"),
        "cashflow": _table(soup, "cash-flow"),
        "ratio_table": _table(soup, "ratios"),
        "concalls": _concalls(soup),
        "annual_reports": _annual_reports(soup),
    }

def _concalls(soup):
    out = []
    for li in soup.select(".concalls ul.list-links li, #documents .concalls li"):
        label = li.find("div")
        tr = li.find("a", title="Raw Transcript")
        if label and tr:
            out.append({"period": label.get_text(strip=True), "url": tr["href"]})
    if not out:  # layout fallback: find the Concalls heading and walk its list
        h = soup.find("h3", string=re.compile("Concalls"))
        if h:
            for li in h.find_parent("div").find_parent("div").select("li"):
                label = li.find("div"); tr = li.find("a", title="Raw Transcript")
                if label and tr:
                    out.append({"period": label.get_text(strip=True), "url": tr["href"]})
    return out

def _annual_reports(soup):
    out = []
    h = soup.find("h3", string=re.compile("Annual reports"))
    if h:
        for a in h.find_parent("div").select("a")[:3]:
            out.append({"label": a.get_text(" ", strip=True)[:60], "url": a["href"]})
    return out
