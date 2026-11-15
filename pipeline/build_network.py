"""Build the Network's data from the push snapshot.

Run after pipeline/build_push.py:  python3 pipeline/build_network.py
Reads web/public/data/push.json and data/network/{registry,investor}.json. No model calls.
Writes
  data/network/filings.json        the filings the Network reads, cut down to what it needs (the API loads this)
  web/public/data/network.json     what Push and Pull show without asking: a block per filing, a block per
                                   company, and the short list of what the network noticed
"""
import datetime as dt, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn.network import Network
from finn.network.engine import MATERIAL
from finn.network.registry import Registry
from finn.network.views import build_id, dump, views

ROOT = pathlib.Path(__file__).resolve().parent.parent
NET, OUT = ROOT / "data" / "network", ROOT / "web" / "public" / "data"
KEEP = ("id", "symbol", "at", "url", "category", "tier", "line", "downgraded", "people")
PERSON = ("name", "role", "action", "seniority", "effective", "reason", "previous", "education", "background", "quote", "page", "verified")


def put(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def main():
    push = json.loads((OUT / "push.json").read_text())
    names = {p["symbol"]: p["short"] for p in push["portfolio"]}
    slim = []
    for f in push["filings"]:
        if f.get("people") or f["category"] in MATERIAL:
            g = {k: f[k] for k in KEEP if k in f}
            if g.get("people"):
                g["people"] = [{k: p[k] for k in PERSON if k in p} for p in g["people"]]
            r = f.get("results")
            if r:                       # the figures a reason to call says: the quarter, the top line's and profit's change on a year ago
                top, pat = (next((l for l in r["lines"] if l["key"] == k), {}) for k in ("revenue", "pat"))
                g["results"] = {"quarter": r["quarter"], "top_label": top.get("label", ""), "top_yoy": top.get("yoy"), "pat_yoy": pat.get("yoy")}
            slim.append(g)
    researched = sorted(p.stem for p in (OUT / "companies").glob("*.json"))
    data = {"asof": push["asof"], "companies": names, "researched": researched, "filings": slim}

    # Built in memory, then each file written once and swapped in whole, so nothing reads a half-made or build-less file
    net = Network.load(ROOT, slim=data)
    out = views(net)
    out["build"] = build_id(out)
    put(OUT / "network.json", dump(out))
    # the API answers "which build is this?" from the file it is bundled with, without rebuilding the views
    put(NET / "filings.json", json.dumps({"asof": data["asof"], "build": out["build"], **data}, separators=(",", ":")))
    blocks = out["filings"]
    same = sum(1 for vs in net.verdicts.values() for _, v in vs if v.status == "same")
    print(f"wrote network.json: {len(net.filed)} people in filings, {len(net.contacts)} contacts, {len(blocks)} filing blocks, "
          f"{len(out['companies'])} companies, {len(out['notices'])} notices, {same} identity matches")


if __name__ == "__main__":
    main()
