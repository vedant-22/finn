"""End-of-day price and volume from NSE's daily bhavcopy: one official file per day covers every stock."""
import csv, datetime as dt, io, zipfile, requests
from . import config

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip"
CACHE = config.CACHE_DIR / "bhav"
CACHE.mkdir(parents=True, exist_ok=True)

def day(d, symbols):
    p = CACHE / f"{d:%Y%m%d}.csv"
    if not p.exists():
        r = requests.get(URL.format(d=f"{d:%Y%m%d}"), headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200 or r.content[:2] != b"PK":
            return None  # holiday or weekend
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            p.write_bytes(z.read(z.namelist()[0]))
    out = {}
    for row in csv.DictReader(io.StringIO(p.read_text())):
        if row["TckrSymb"] in symbols and row["SctySrs"] in ("EQ", "BE"):
            out[row["TckrSymb"]] = {"close": float(row["ClsPric"]), "prev": float(row["PrvsClsgPric"]), "vol": int(float(row["TtlTradgVol"]))}
    return out

def history(symbols, end, sessions=45):
    """Last `sessions` trading days for the given symbols: {sym: [{d, close, chg, vol}]}, oldest first."""
    symbols, series, d, got = set(symbols), {s: [] for s in symbols}, end, 0
    while got < sessions and (end - d).days < sessions * 2:
        rows = day(d, symbols)
        if rows:
            got += 1
            for s, r in rows.items():
                series[s].append({"d": d.isoformat(), "close": r["close"], "chg": round((r["close"] / r["prev"] - 1) * 100, 2) if r["prev"] else 0, "vol": r["vol"]})
        d -= dt.timedelta(days=1)
    return {s: list(reversed(v)) for s, v in series.items()}
