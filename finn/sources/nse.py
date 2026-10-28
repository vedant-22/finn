"""Polite NSE client: one session with cookies, small delay between calls, disk cache."""
import json, time, hashlib, pathlib, requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
from .. import config
CACHE = config.CACHE_DIR / "nse"
CACHE.mkdir(parents=True, exist_ok=True)

_s = None
def session():
    global _s
    if _s is None:
        _s = requests.Session()
        _s.headers.update({"User-Agent": UA, "Referer": "https://www.nseindia.com/", "Accept": "application/json,*/*"})
        try:
            _s.get("https://www.nseindia.com/", timeout=20)
        except requests.RequestException:
            pass
    return _s

def get_json(url, ttl_hours=6):
    """GET with a file cache. NSE rate-limits aggressively, so we sleep 1s between live calls."""
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if key.exists() and (time.time() - key.stat().st_mtime) < ttl_hours * 3600:
        return json.loads(key.read_text())
    for attempt in range(3):
        r = session().get(url, timeout=30)
        if r.status_code == 200:
            data = r.json()
            key.write_text(json.dumps(data))
            time.sleep(1)
            return data
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"NSE {r.status_code} for {url}")

def announcements(from_date, to_date, symbol=None):
    """from/to as datetime.date. Returns NSE's raw list."""
    f, t = from_date.strftime("%d-%m-%Y"), to_date.strftime("%d-%m-%Y")
    url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={f}&to_date={t}"
    if symbol:
        url += f"&symbol={symbol}"
    return get_json(url)

def _parse_dt(s):
    import datetime as dt
    return dt.datetime.strptime(s, "%d-%b-%Y %H:%M:%S")

def transcripts(symbol, months=16, today=None):
    """Earnings-call transcripts the company filed with NSE, newest first, one per month."""
    import datetime as dt
    today = today or dt.date.today()
    rows = announcements(today - dt.timedelta(days=months * 31), today, symbol=symbol.upper())
    seen, out = set(), []
    for x in sorted(rows, key=lambda r: _parse_dt(r["an_dt"]), reverse=True):
        blob = ((x.get("attchmntText") or "") + " " + (x.get("attchmntFile") or "")).lower()
        if "transcript" not in blob or not (x.get("attchmntFile") or "").lower().endswith((".pdf", ".zip")):
            continue
        d = _parse_dt(x["an_dt"])
        month = d.strftime("%b %Y")
        if month in seen:
            continue
        seen.add(month)
        out.append({"period": month, "filed": x["an_dt"], "url": x["attchmntFile"]})
    return out
