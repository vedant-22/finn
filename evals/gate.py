"""The merge gate (docs/adr/0004-code-checks-and-evals-gate.md). A change to a prompt, a schema or a model passes
only if the evals still hold.

    python3 evals/gate.py           offline floors and fingerprints; exit 1 on anything red
    python3 evals/gate.py --live    with a key: classify twice and the 26 questions twice, fresh, against written floors;
                                    validates the fingerprints those runs cover
    python3 evals/gate.py --accept S   record unvalidated step S's changed fingerprint, on purpose; refused for a validated step
    python3 evals/gate.py --seed    write fingerprints to gate.json (classify validated where the recorded run's constants match)

Fingerprints: every model step's prompt, schema, model and fallback chain, hashed. Validated and unchanged passes.
First seen and unchanged is a skip ("unvalidated"). Any change is red: a validated step until --live passes, an
unvalidated one until its validator passes or --accept records it, so no prompt edit reaches main unseen. A skip prints its
reason and never counts as a pass. promise_extract and promise_grade have no --live path yet: they are validated by
rebuilding a company and re-reading evals/grades_review.md, by hand.
"""
import ast, copy, hashlib, json, os, pathlib, re, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import classify, config, explain, ledger, llm, people, triage
from finn.answer import agent, workflow

GATE = ROOT / "evals/gate.json"
VALIDATOR = {   # what can move a step from first seen to validated; the gate is red on any change either way
    "classify": "--live: the 24 labelled filings, twice",
    "people": "none yet: the 24 classify filings hold 2 management changes, too few; a labelled set of its own (ADR 4)",
    "explain": "none yet: --live runs enrich without revenue, so sizing never runs; a labelled set of its own (ADR 4)",
    "answer": "--live: the 26 published questions, twice",
    "promise_extract": "none automatic: a hand review of 20 grades (evals/grades_review.md, 17 hold, two models)",
    "agent": "none yet: ADR 3's keep rule, on a keyed run of the 26 questions; the agent is off until it passes",
    "promise_grade": "none automatic: a hand review of 20 grades (evals/grades_review.md, 17 hold, two models)",
}
STEPS = {   # step: (module file, prompt name, schema name); the model and every other argument come from the call itself
    "classify": ("finn/classify.py", "PROMPT", "SCHEMA"),
    "people": ("finn/people.py", "PROMPT", "SCHEMA"),
    "explain": ("finn/explain.py", "PROMPT", "SCHEMA"),
    "promise_extract": ("finn/ledger.py", "EXTRACT_PROMPT", "PROMISE_SCHEMA"),
    "promise_grade": ("finn/ledger.py", "GRADE_PROMPT", "GRADE_SCHEMA"),
    "answer": ("finn/answer/workflow.py", "PROMPT", "SCHEMA"),
    "agent": ("finn/answer/agent.py", "PROMPT", "SCHEMA"),
}
MODS = {"finn/classify.py": classify, "finn/people.py": people, "finn/explain.py": explain, "finn/ledger.py": ledger,
        "finn/answer/workflow.py": workflow, "finn/answer/agent.py": agent}
SCANNED = ("finn", "api", "pipeline")   # every model call in these must belong to a step
NOT_MODEL_FACING = {"task", "public", "meta"}   # privacy, caching and labels: they don't change what the model is asked

def chain(m):
    out = [m]
    while out[-1] in config.FALLBACK:
        out.append(config.FALLBACK[out[-1]])
    return out

def fp(prompt, schema, model, ch, calls=()):
    return hashlib.sha256(json.dumps([prompt, schema, model, ch] + ([sorted(calls)] if calls else []), sort_keys=True).encode()).hexdigest()[:16]

def _calls(tree):
    """Each llm.generate call in a module: (task literal or None, the call's model expression, its other model-facing
    arguments as source, line)."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and "llm.generate" in ast.unparse(n.func):
            kw = {k.arg: k.value for k in n.keywords if k.arg}
            task = kw["task"].value if isinstance(kw.get("task"), ast.Constant) else None
            args = [ast.unparse(a) for a in n.args] + [f"{k}={ast.unparse(v)}" for k, v in sorted(kw.items()) if k not in NOT_MODEL_FACING | {"model"}]
            out.append((task, kw.get("model"), json.dumps(args), n.lineno))
    return out

def _aliases(tree):
    """Lines where llm.generate is handed around rather than called (an alias, an import of the name): a call made
    through it would escape the fingerprint, so the gate can't follow it and says so."""
    inside = {id(n) for c in ast.walk(tree) if isinstance(c, ast.Call) for n in ast.walk(c.func)}
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr == "generate" and isinstance(n.value, ast.Name) and n.value.id == "llm" and id(n) not in inside:
            out.append(n.lineno)
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[-1] == "llm" and any(a.name == "generate" for a in n.names):
            out.append(n.lineno)
    return out

def call_sites():
    """{step: [(model expression, arguments)]} for every model call in the code, and the calls no step owns."""
    by, stray = {}, []
    for d in SCANNED:
        for f in sorted((ROOT / d).rglob("*.py")):
            tree, rel = ast.parse(f.read_text()), str(f.relative_to(ROOT))
            stray += [f"{rel}:{line} (llm.generate passed around, not called)" for line in _aliases(tree)]
            for task, model, args, line in _calls(tree):
                if task in STEPS and rel == STEPS[task][0]:
                    by.setdefault(task, []).append((model, args))
                else:
                    stray.append(f"{rel}:{line} (task {task!r})")
    return by, stray

def _model(step, expr):
    if expr is None:
        raise ValueError(f"{step}: its call names no model")
    return eval(compile(ast.Expression(expr), "<model>", "eval"), vars(MODS[STEPS[step][0]]))

def rendered(root, step):
    """Classify's requests as built, by root's code (evals/render_classify.py); [] for the other steps."""
    if step != "classify":
        return []
    out = subprocess.run([sys.executable, "-I", str(ROOT / "evals/render_classify.py"), str(root), str(ROOT / "evals/classification.json")],
                         capture_output=True, text=True, timeout=300)
    return json.loads(out.stdout) if out.returncode == 0 else ["could not render: " + out.stderr.strip()[-200:]]

def current(step):
    f, p, s = STEPS[step]
    sites = call_sites()[0].get(step, [])
    if not sites:
        return "no call"
    try:
        models = {_model(step, m) for m, _ in sites}
    except (ValueError, NameError, AttributeError):
        return "no model"
    if len(models) != 1:
        return "two models"
    m = models.pop()
    return fp(getattr(MODS[f], p), getattr(MODS[f], s), m, chain(m), [a for _, a in sites] + rendered(ROOT, step))

def at_commit(commit, step):
    """The same fingerprint computed from the source at a commit, by AST, without importing it. A model given as
    config.NAME, or as a module constant set to config.NAME, is read from config.py at that commit."""
    f, p, s = STEPS[step]
    show = lambda path: subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, text=True).stdout
    tree, consts, names = ast.parse(show(f)), {}, {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            names[node.targets[0].id] = node.value
            if node.targets[0].id in (p, s):
                try:
                    consts[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:   # a schema built by code (the agent's): not computable from source alone
                    return None
    cfg = {n.targets[0].id: n.value for n in ast.parse(show("finn/config.py")).body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    def val(e):   # a string, a config name, or os.environ.get("X", "default"), as config.py had it then
        if isinstance(e, ast.Constant):
            return e.value
        if isinstance(e, ast.Name) and e.id in cfg:
            return val(cfg[e.id])
        if isinstance(e, ast.Call) and e.args and isinstance(e.args[-1], ast.Constant):
            return e.args[-1].value
        return None
    def resolve(e):
        if isinstance(e, ast.Name) and e.id in names:
            e = names[e.id]
        if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name) and e.value.id == "config" and e.attr in cfg:
            return val(cfg[e.attr])
        return None
    sites = [(resolve(m), a) for t, m, a, _ in _calls(tree) if t == step]
    if not sites or len({m for m, _ in sites}) != 1 or sites[0][0] is None:
        return None
    m = sites[0][0]
    fbk = cfg.get("FALLBACK")
    lookup = {val(k): val(v) for k, v in zip(fbk.keys, fbk.values)} if isinstance(fbk, ast.Dict) else {}
    ch = [m]
    while ch[-1] in lookup:
        ch.append(lookup[ch[-1]])
    import tempfile
    with tempfile.TemporaryDirectory() as d:   # that commit's code, to build its requests
        subprocess.run(f"git archive {commit} finn | tar -x -C {d}", shell=True, cwd=ROOT, check=True)
        return fp(consts.get(p), consts.get(s), m, ch, [a for _, a in sites] + rendered(d, step))

def seed():
    g = json.loads(GATE.read_text()) if GATE.exists() else {}
    commit = subprocess.run(["git", "log", "-1", "--format=%h", "--", "evals/classify_result.txt"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    g["fingerprints"] = {}
    for step in STEPS:
        now = current(step)
        ok = step == "classify" and at_commit(commit, step) == now
        g["fingerprints"][step] = {"fp": now, "state": "validated" if ok else "first_seen",
                                   "by": f"{commit}, evals/classify_result.txt (category 22/24, tier 21/24)" if ok else ""}
    GATE.write_text(json.dumps(g, indent=1) + "\n")
    print(json.dumps(g["fingerprints"], indent=1))

PAGES = ROOT / "evals/fixtures/pages.json.gz"   # the page text the evals read, checked in (evals/fixtures/make_pages.py)

def run(script, *args):
    env = dict(os.environ, **({"FINN_PAGES": str(PAGES)} if PAGES.exists() else {}))
    p = subprocess.run([sys.executable, f"evals/{script}", *args], cwd=ROOT, capture_output=True, text=True, timeout=1800, env=env)
    return p.returncode, p.stdout + p.stderr

def offline(g, base=None, live_ok=()):
    """With base (a pull request: the base branch's gate.json), what is validated, the floors and the list of evals come
    from the base, not from this tree, so editing gate.json by hand passes nothing, and an eval that doesn't run is red."""
    out = []   # (state, name, detail): state is pass, fail or skip
    for name, f in g["offline"].items():
        code, txt = run(f["script"])
        if f.get("skip_if") and re.search(f["skip_if"], txt):
            if PAGES.exists() or base is not None:   # the evals read the checked-in pages: a fetch means a page, or the fixture, is missing
                out.append(("fail", name, "it tried to fetch a page that isn't in evals/fixtures/pages.json.gz: rebuild it (fixtures/make_pages.py)"))
            else:
                out.append(("skip", name, f"{f['skip_reason']}"))
            continue
        if code != 0:   # a crash after its lines were printed is still a crash
            out.append(("fail", name, f"exited {code}: {(txt.strip().splitlines() or [''])[-1][:160]}")); continue
        if "total" in f:
            m = re.findall(f["total"], txt)
            got, of = map(int, m[-1]) if m else (0, 1)
            floor = of if f["floor"] == "all" else f["floor"]
            out.append(("pass" if got >= floor else "fail", name, f"{got}/{of}, floor {floor}"))
            for line in re.findall(r"^skip .*$", txt, re.M):
                out.append(("skip", name, line[5:]))
        for label, rx, floor in f.get("floors", []):
            m = re.search(rx, txt)
            got = int(m.group(1)) if m else -1
            out.append(("pass" if got >= floor else "fail", f"{name} {label}", f"{got}, floor {floor}"))
        if "lead" in f:
            m = re.search(r"lead: act moved ([\d.]+)x", txt)
            al = re.search(r"alignment: .*?: (passes|FAILS)", txt)
            mt = re.search(r"matching: .*?: (passes|FAILS)", txt)
            lo, hi = f["lead"]
            ok = m and lo <= float(m.group(1)) <= hi and al and al.group(1) == "passes" and mt and mt.group(1) == "passes"
            out.append(("pass" if ok else "fail", name, f"act/fold {m and m.group(1)} in [{lo}, {hi}], alignment {al and al.group(1)}, matching {mt and mt.group(1)}"))
    return out + fingerprint_states(g, base, live_ok)

ACCEPTED = re.compile(r"^\S.*, \d{4}-\d{2}-\d{2}: \S")   # what --accept writes: who, the day, why

def fingerprint_states(g, base=None, live_ok=()):
    stray = call_sites()[1]
    out = [("fail", "model calls", "a model call that no step owns, so nothing fingerprints it: " + ", ".join(stray))] if stray else []
    if set(llm.TASKS) != set(STEPS):   # the client refuses any task not in llm.TASKS; the two lists must be one
        out.append(("fail", "model calls", f"llm.TASKS and the gate's steps differ: {sorted(set(llm.TASKS) ^ set(STEPS))}"))
    for step in list(STEPS) + [s for s in g["fingerprints"] if s not in STEPS]:
        rec = g["fingerprints"].get(step)
        if rec is None or step not in STEPS:   # a model step with no entry would never be checked
            out.append(("fail", f"fingerprint {step}", "in the gate's steps or in gate.json, not both: --accept records a new step")); continue
        now = current(step)
        if base is not None:
            ref = base["fingerprints"].get(step, {})
            if step in live_ok:
                out.append(("pass", f"fingerprint {step}", "validated by --live in this run")); continue
            if ref.get("state") == "validated" or rec["state"] == "validated":
                same = ref.get("state") == "validated" and now == ref["fp"] and rec == ref
                out.append(("pass" if same else "fail", f"fingerprint {step}", f"validated on the base branch, unchanged" if same else
                            "a validated step, or its gate.json entry, changed: it passes only by --live in this run")); continue
            if rec["fp"] != ref.get("fp") and (rec.get("by") == ref.get("by") or not ACCEPTED.match(rec.get("by", ""))):
                out.append(("fail", f"fingerprint {step}", f"changed while unvalidated, with no new record of who accepted it and why: --accept {step} --why ...")); continue
        val = rec["state"] == "validated"
        state = "fail" if now != rec["fp"] else "pass" if val else "skip"
        why = {"pass": f"validated by {rec['by']}", "skip": f"unvalidated; validator {VALIDATOR[step]}",
               "fail": "changed since it was validated: run --live" if val else
                       f"changed while unvalidated: validator {VALIDATOR[step]}; or --accept {step} records it unvalidated"}[state]
        out.append((state, f"fingerprint {step}", why))
    return out

def floors_fell(g, base):
    """Floors may rise in a pull request, never fall."""
    rank = lambda v: float("inf") if v == "all" else v
    fell = [f"{n} {f['floor']} < {base['offline'][n]['floor']}" for n, f in g["offline"].items()
            if n in base["offline"] and "floor" in f and rank(f["floor"]) < rank(base["offline"][n]["floor"])]
    fell += [f"{n} {lbl} {fl} < {b[2]}" for n, f in g["offline"].items() for (lbl, _, fl), b in zip(f.get("floors", []), base["offline"].get(n, {}).get("floors", []))
             if fl < b[2]]
    fell += [f"live {n} {k} {v} < {base['live'][n][k]}" for n, f in g["live"].items() for k, v in f.items()
             if isinstance(v, (int, float)) and k != "of" and isinstance(base["live"].get(n, {}).get(k), (int, float)) and v < base["live"][n][k]]
    lead = g["offline"].get("reaction", {}).get("lead"); blead = base["offline"].get("reaction", {}).get("lead")
    if lead and blead and (lead[0] < blead[0] or lead[1] > blead[1]):
        fell.append(f"reaction lead {lead} wider than {blead}")
    return fell

def dropped(g, base):
    """What the base's gate.json holds that this tree dropped or changed: an eval, its script, the pattern that reads its
    output, a floor, a fingerprinted step. A pull request may add an eval or raise a floor (numbers: floors_fell)."""
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    def walk(b, t, at):
        if isinstance(b, (dict, list)):
            items = b.items() if isinstance(b, dict) else enumerate(b)
            has = (lambda k: isinstance(t, dict) and k in t) if isinstance(b, dict) else (lambda k: isinstance(t, list) and k < len(t))
            return [x for k, v in items for x in (walk(v, t[k], f"{at} {k}") if has(k) else [f"{at} {k} removed"])]
        return [] if b is None or b == t or (num(b) and (num(t) or t == "all")) else [f"{at} changed"]
    return walk({"offline": base["offline"], "live": {n: dict.fromkeys(f) for n, f in base["live"].items()}, "fingerprint": dict.fromkeys(base["fingerprints"])},
                {"offline": g["offline"], "live": g["live"], "fingerprint": g["fingerprints"]}, "gate.json:")

def changed_validated(g, base):
    """Steps validated on the base whose fingerprint or entry changed, or marked validated here and not there."""
    b = base["fingerprints"]
    return sorted({s for s, r in b.items() if r.get("state") == "validated" and (current(s) != r["fp"] or g["fingerprints"].get(s) != r)}
                  | {s for s, r in g["fingerprints"].items() if r["state"] == "validated" and b.get(s, {}).get("state") != "validated"})

def live(g):
    """Returns (exit code, the steps it validated)."""
    if not llm.has_key():
        print("SKIP --live: no GEMINI_API_KEY (a free key is enough: every text here is public)"); return 2, set()
    os.environ["FINN_FRESH"] = "1"   # skip cache reads, so two runs are two runs
    cases = json.loads((ROOT / "evals/classification.json").read_text())
    runs, answered = [], []
    for _ in range(2):
        rows = copy.deepcopy(cases)
        with llm.scope() as models:
            classify.classify(rows)
            triage.enrich(rows, {}, {})
        answered += models; runs.append(rows)
    f = g["live"]["classify"]
    cat = min(sum(r["category"] == r["label_category"] for r in rows) for rows in runs)
    tier = min(sum(r["tier"] == r["label_tier"] for r in rows) for rows in runs)
    agree = sum(a["tier"] == b["tier"] and a["category"] == b["category"] for a, b in zip(*runs))
    fell = sorted({m for m in answered if m not in (config.FAST,)})
    ok = cat >= f["category"] and tier >= f["tier"] and agree >= f["agree"] and not fell
    print(f"live classify: category {cat}/24 (floor {f['category']}), tier {tier}/24 (floor {f['tier']}), two runs agree {agree}/24 "
          f"(floor {f['agree']}), fallback models {fell or 'none'}: {'PASS' if ok else 'FAIL'}")
    if ok:
        g["fingerprints"]["classify"] = {"fp": current("classify"), "state": "validated", "by": f"gate.py --live: category {cat}, tier {tier}, agree {agree}"}
    ok_a = live_answer(g)
    GATE.write_text(json.dumps(g, indent=1) + "\n")
    return (0 if ok and ok_a else 1), {s for s, k in (("classify", ok), ("answer", ok_a)) if k}

def live_answer(g):
    """The 26 published questions twice, fresh (run_answer.py --live), against floors fixed in gate.json before any
    live run, so no run sets its own bar."""
    _, txt = run("run_answer.py", "--live")
    rx = (r"live run \d: grounded (\d+)/20 \(on the labelled page \d+/20\), 'not in the calls' on (\d+)/6, answered unanswerable (\d+)/6, "
          r"rejected by the checks \d+/26, unavailable (\d+), degraded (\d+)")
    rows = [tuple(map(int, m)) for m in re.findall(rx, txt)]
    if len(rows) != 2:
        print(f"live answer: FAIL, expected two runs\n{txt[-400:]}"); return False
    f = g["live"]["answer"]
    grounded, none = min(r[0] for r in rows), min(r[1] for r in rows)
    down, fell = sum(r[3] for r in rows), sum(r[4] for r in rows)
    checked = json.loads((ROOT / "evals/answer_questions.json").read_text()).get("checked_by")
    ok = grounded >= f["grounded"] and none >= f["not_in_calls_min"] and not down and not fell and bool(checked)
    print(f"live answer: grounded {grounded}/20 (floor {f['grounded']}), 'not in the calls' {none}/6 (floor {f['not_in_calls_min']}), "
          f"unavailable {down}, degraded {fell}, labels checked by {checked or 'no one yet'}: {'PASS' if ok else 'FAIL'}")
    if ok:
        g["fingerprints"]["answer"] = {"fp": current("answer"), "state": "validated", "by": f"gate.py --live: grounded {grounded}/20, none {none}/6"}
    return ok

def accept(g, step, why, who):
    """Record an unvalidated step's changed fingerprint as first seen, with who and why. Returns why not, or None."""
    if step not in STEPS:
        return f"no model step called {step}: one of {', '.join(STEPS)}"
    if g["fingerprints"].get(step, {}).get("state") == "validated":
        return f"{step} is validated: a change to it passes only by its validator ({VALIDATOR[step]})"
    if not why.strip():
        return f'--accept {step} needs --why "what changed and why it needs no eval yet"'
    g["fingerprints"][step] = {"fp": current(step), "state": "first_seen", "by": f"{who}, {time.strftime('%Y-%m-%d')}: {why.strip()}"}

if __name__ == "__main__":
    if "--seed" in sys.argv:
        seed(); sys.exit(0)
    g = json.loads(GATE.read_text())
    if "--live" in sys.argv and "--base" not in sys.argv:
        sys.exit(live(g)[0])
    if "--accept" in sys.argv:
        step = sys.argv[sys.argv.index("--accept") + 1]
        why = sys.argv[sys.argv.index("--why") + 1] if "--why" in sys.argv else ""
        who = subprocess.run(["git", "config", "user.name"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or os.environ.get("USER", "?")
        refused = accept(g, step, why, who)
        if refused:
            print(refused); sys.exit(1)
        GATE.write_text(json.dumps(g, indent=1) + "\n"); print(f"{step}: recorded as first seen, unvalidated, by {who}"); sys.exit(0)
    base, live_ok, pre = None, set(), []
    if "--base" in sys.argv:   # a pull request: the base branch's gate.json is the reference
        ref = sys.argv[sys.argv.index("--base") + 1]
        shown = subprocess.run(["git", "show", f"{ref}:evals/gate.json"], cwd=ROOT, capture_output=True, text=True)
        if shown.returncode:
            print(f"FAIL  gate.json at {ref}: can't be read"); sys.exit(1)
        base = json.loads(shown.stdout)
        fell = dropped(g, base) or floors_fell(g, base)
        pre.append(("fail" if fell else "pass", "gate.json against the base", "; ".join(fell) or f"nothing dropped or lower than at {ref}"))
        need = changed_validated(g, base)
        if need and llm.has_key() and not fell:   # a validated step changed: only a live run in this job can pass it
            live_ok = live(g)[1] & set(need)
    res = pre + offline(g, base, live_ok)
    for state, name, detail in res:
        print(f"{state.upper():5} {name}: {detail}")
    fails = [r for r in res if r[0] == "fail"]
    print(f"\n{sum(r[0] == 'pass' for r in res)} pass, {len(fails)} fail, {sum(r[0] == 'skip' for r in res)} skip (a skip is not a pass)")
    sys.exit(1 if fails else 0)
