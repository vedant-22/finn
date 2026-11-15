"""Apply finn.ledger.recheck to the committed ledgers, with no model call and no refetch, so the 28 Oct snapshot
keeps its date. New builds run the same checks in finn.research.assemble. Idempotent: a second run changes nothing.
Usage: python3 pipeline/recheck_ledgers.py"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from finn import ledger

OUT = pathlib.Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "companies"
STATES = ("kept", "partly", "missed", "quiet", "pending", "unclear")

for f in sorted(OUT.glob("*.json")):
    d = json.loads(f.read_text())
    changed = ledger.recheck(d["ledger"], d["quarters"])
    if not changed:
        continue
    d["score"] = {s: sum(1 for b in d["ledger"] if b.get("hard") and b["status"] == s) for s in STATES}
    f.write_text(json.dumps(d, separators=(",", ":")))
    now = {b["id"]: b["status"] for b in d["ledger"]}
    print(d["symbol"], ", ".join(f"#{i} {old} -> {now[i]} ({why})" for i, why, old in changed), "| score", d["score"])
