"""Pre-build promise ledgers for the portfolio and the pull demo names, so the app opens instantly.
Any other ticker is built live by the API. Usage: python3 pipeline/build_ledgers.py [SYMBOL ...]"""
import json, pathlib, sys, time, traceback
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import research

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data" / "companies"
DEMO = ["DIXON", "PIDILITIND", "TITAN", "POLYCAB"]

def main(symbols):
    OUT.mkdir(parents=True, exist_ok=True)
    for s in symbols:
        t = time.time()
        try:
            r = research.run(s)
            r["built_in"] = round(time.time() - t, 1)
            (OUT / f"{s}.json").write_text(json.dumps(r, separators=(",", ":")))
            print(s, r["score"], r["usage"]["usd_if_billed"], r["built_in"], "s", flush=True)
        except Exception:
            print(s, "FAILED", traceback.format_exc()[-300:], flush=True)
    index = sorted(p.stem for p in OUT.glob("*.json"))
    (OUT.parent / "companies.json").write_text(json.dumps(index))

if __name__ == "__main__":
    syms = sys.argv[1:] or [p["symbol"] for p in json.loads((ROOT / "data" / "portfolio.json").read_text())] + DEMO
    main(syms)
