"""The ledger's code checks (finn/ledger.py recheck), offline: rules the grading prompt states, enforced so a model's
grade can't break them. Cases on made-up rows, then the committed ledgers: rechecked already, and none breaks a rule.
Usage: python3 evals/run_recheck.py"""
import copy, glob, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import ledger

ok = total = 0
lines = []
def check(name, cond, detail=""):
    global ok, total
    total += 1; ok += bool(cond)
    lines.append(f"{'ok  ' if cond else 'FAIL'} {name}{f'  [{detail}]' if detail and not cond else ''}")
    print(lines[-1])

# When a time frame ends, read as late as its words allow, from the call's month
for by, period, want in [("FY27", "May 2026", (2027, 3)), ("this year", "May 2026", (2027, 3)), ("Q3 FY27", "Aug 2026", (2026, 12)),
                         ("next 3 to 4 quarters", "Oct 2025", (2026, 12)), ("end of FY26", "Aug 2025", (2026, 3)), ("September 2026", "May 2026", (2026, 9)),
                         ("medium term", "May 2026", None), ("unspecified", "May 2026", None)]:
    got = ledger.deadline(by, period)
    check(f"deadline: '{by}' said in {period} ends {want}", got == want, got)

Q = [{"q": "Jun 2026"}, {"q": "Sep 2026"}]          # the latest reported quarter: September 2026
def row(**kw):
    return {"id": 1, "period": "May 2026", "by_when": "FY27", "target": "Revenue growth of over 10%", "status": "kept",
            "evidence_kind": "numbers", "evidence": "Revenue Sep 2026 YoY 26%", "verdict": "model's sentence", "hard": True, **kw}
def after(r):
    r = copy.deepcopy(r); ledger.recheck([r], Q); return r

r = after(row())
check("a growth target for a year not ended, graded kept, is not due", (r["status"], r.get("checked")) == ("pending", "not_due"), r["status"])
check("... and its line says when it is due and that the period hasn't ended",
      "March 2027" in r["verdict"] and "hasn't ended" in r["verdict"], r["verdict"])
check("a margin target for a year not ended, kept on the call's word, is not due",
      after(row(target="EBITDA margin 20-24%", evidence_kind="quote"))["status"] == "pending")
check("a launch due later but done early stays kept", after(row(target="Launch wires in three states"))["status"] == "kept")
check("a growth target whose year has ended stays kept", after(row(by_when="FY26", period="May 2025"))["status"] == "kept")
check("a growth target management itself deferred stays missed",
      after(row(status="missed", evidence_kind="quote", target="Expand margin 120-130 bps"))["status"] == "missed")
r = after(row(status="pending", by_when="Q1 FY27", target="Commission the plant"))
check("a pending promise past its date with nothing said is unclear, past due", (r["status"], r.get("checked")) == ("unclear", "past_due"), r["status"])
r = after(row(status="pending", by_when="Q1 FY27", target="Commission the plant", restated=[{"period": "Aug 2026", "page": 3, "url": ""}]))
check("... unless a later call said it again (its date may have moved)", r["status"] == "pending", r["status"])
r = after(row(target="Segment margin of 12%", by_when="FY26", period="May 2025"))
check("a grade settled by numbers the results don't report is unclear, unmeasured", (r["status"], r.get("checked")) == ("unclear", "unmeasured"), r["status"])
check("no check ever adds a kept, missed or partly",
      all(after(row(status=s, target=t))["status"] in (s, "pending", "unclear")
          for s in ("kept", "missed", "partly", "pending", "quiet", "unclear") for t in ("Revenue growth of 10%", "Launch a plant"))
      and all(after(row(status=s))["status"] == s for s in ("pending", "quiet", "unclear")))

# The committed ledgers: already rechecked (pipeline/recheck_ledgers.py), so a second pass changes nothing
files = sorted(glob.glob(str(ROOT / "web/public/data/companies/*.json")))
moved, early = [], []
for f in files:
    d = json.loads(pathlib.Path(f).read_text())
    rows = copy.deepcopy(d["ledger"])
    moved += [f"{d['symbol']} #{i}" for i, *_ in ledger.recheck(rows, d["quarters"])]
    last = ledger._qend(d["quarters"][-1]["q"]) if d["quarters"] else None
    early += [f"{d['symbol']} #{b['id']}" for b in d["ledger"] if b["status"] == "kept" and last and ledger.RATE.search(b.get("target", ""))
              and (due := ledger.deadline(b.get("by_when"), b.get("period"))) and due > last]
check(f"the {len(files)} committed ledgers are rechecked: a second pass moves nothing", not moved, moved)
check("no committed ledger counts a growth or margin target kept before its period ends", not early, early)

lines.append(f"TOTAL {ok}/{total}")
print(lines[-1])
(ROOT / "evals" / "recheck_result.txt").write_text("\n".join(lines) + "\n")
sys.exit(0 if ok == total else 1)
