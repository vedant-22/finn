"""Fill in joiners' backgrounds the snapshot missed, without rebuilding it.

The people reader used to stop at page 15, so a board outcome with the profile in a late annexure
(Home First's new CFO, page 23) came out as "not stated". This rereads only those filings with the
fixed reader and copies background, previous roles and education onto the same person. Nothing else
in push.json changes, so the brief keeps its counts.

usage: python3 pipeline/refill_backgrounds.py [--dry]
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from finn import people

PUSH = pathlib.Path(__file__).resolve().parents[1] / "web/public/data/push.json"
EMPTY = {"", "not stated", "none", "n/a"}
JOINS = {"appointed", "re-appointed", "redesignated"}
key = lambda name: re.sub(r"^(mr|ms|mrs|dr|shri|smt)\.?\s+", "", name.strip().lower()).replace(".", "")

def main(dry):
    push = json.loads(PUSH.read_text())
    names = {p["symbol"]: p.get("name", p["symbol"]) for p in push.get("portfolio", [])}
    filled = 0
    for f in push["filings"]:
        gaps = [x for x in f.get("people") or [] if x["action"] in JOINS and (x.get("background") or "").strip().lower() in EMPTY]
        if not gaps:
            continue
        fresh = {key(x["name"]): x for x in people.from_filing(names.get(f["symbol"], f["symbol"]), f["url"])}
        for x in gaps:
            y = fresh.get(key(x["name"]))
            if not y or (y.get("background") or "").strip().lower() in EMPTY:
                print("still none:", f["symbol"], x["name"])
                continue
            print("filled:", f["symbol"], x["name"], "->", y["background"])
            x.update(background=y["background"], previous=y.get("previous") or [], education=y.get("education") or "")
            filled += 1
    if filled and not dry:
        PUSH.write_text(json.dumps(push, ensure_ascii=False, separators=(",", ":")))
    print(f"{filled} filled" + (" (dry run)" if dry else ""))

if __name__ == "__main__":
    main("--dry" in sys.argv)
