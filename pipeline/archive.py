"""The raw archive: a year of every NSE filing and every EQ/BE price, one gzip per day under data/raw/.

Resumable (a day already on disk is skipped), one request a second, and a manifest of counts per day.
    python3 pipeline/archive.py [filings|prices|both]
"""
import csv, datetime as dt, gzip, io, json, pathlib, sys, time, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import config
from finn.sources import nse

RAW = config.ROOT / "data" / "raw"
FILINGS = (dt.date(2025, 11, 1), dt.date(2026, 10, 28))
PRICES = (dt.date(2025, 8, 1), dt.date(2026, 10, 30))
BHAV = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip"
COLS = ["ISIN", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "PrvsClsgPric", "TtlTradgVol", "TtlTrfVal"]

def days(a, b):
    while a <= b:
        yield a
        a += dt.timedelta(days=1)

def get(url):
    global_s = nse.session()
    for attempt in range(4):
        try:
            r = global_s.get(url, timeout=40)
        except Exception:
            r = None
        if r is not None and r.status_code in (200, 404):
            time.sleep(1)
            return r
        nse._s = None; global_s = nse.session()   # cookies expired or a block: start a fresh session
        time.sleep(5 + 10 * attempt)
    raise RuntimeError(f"gave up on {url}")

def manifest(kind):
    p = RAW / f"{kind}_manifest.json"
    return p, (json.loads(p.read_text()) if p.exists() else {})

def fetch_filings():
    path, man = manifest("filings")
    for d in days(*FILINGS):
        out = RAW / "filings" / f"{d}.json.gz"
        if out.exists():
            continue
        f = d.strftime("%d-%m-%Y")
        r = get(f"https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={f}&to_date={f}")
        rows = r.json() if r.status_code == 200 else []
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(gzip.compress(json.dumps(rows).encode()))
        # A round count may mean the API cut the list; the day is flagged so the study can say so.
        man[str(d)] = {"n": len(rows), "round": bool(rows) and len(rows) % 500 == 0}
        path.write_text(json.dumps(man, indent=0))
        print("filings", d, len(rows), flush=True)

def fetch_prices():
    path, man = manifest("prices")
    for d in days(*PRICES):
        out = RAW / "prices" / f"{d}.csv.gz"
        if d.weekday() >= 5 or out.exists() or man.get(str(d)) == "holiday":
            continue
        r = get(BHAV.format(d=d.strftime("%Y%m%d")))
        if r.status_code == 404 or not r.content.startswith(b"PK"):
            man[str(d)] = "holiday"
        else:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            rows = [x for x in csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode())) if x["SctySrs"] in ("EQ", "BE")]
            buf = io.StringIO(); w = csv.writer(buf); w.writerow(COLS)
            w.writerows([x[c] for c in COLS] for x in rows)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(gzip.compress(buf.getvalue().encode()))
            man[str(d)] = len(rows)
        path.write_text(json.dumps(man, indent=0))
        print("prices", d, man[str(d)], flush=True)

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    if what in ("prices", "both"):
        fetch_prices()
    if what in ("filings", "both"):
        fetch_filings()
