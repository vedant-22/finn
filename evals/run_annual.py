"""The annual-report readers against hand-read labels, offline, from the committed fixture.

    python3 evals/run_annual.py                the checks and the scores; writes evals/annual_result.txt
    python3 evals/run_annual.py --first-pass   once, the first run on the held-out half: kept verbatim in the result

Labels: evals/annual_truth.json (dev, which the readers were written on, and held_out, labelled after the readers
were frozen and before they first ran on it). Pages and calls: evals/fixtures/annual_pages.json.gz.
The asserts are what must never happen on screen (a quote not on its page, a figure not printed there or not the
label's, an emphasis or a modified opinion the auditor didn't write); the scores are how much the rules read.
"""
import datetime as dt, gzip, hashlib, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import annual, config

FIXTURE = ROOT / "evals/fixtures/annual_pages.json.gz"
TRUTH = ROOT / "evals/annual_truth.json"
SERVED = ROOT / "web/public/data/annual"
COMPANIES = ROOT / "web/public/data/companies"
RESULT = ROOT / "evals/annual_result.txt"
FIRST = ROOT / "evals/annual_first_pass.txt"
SECOND = ROOT / "evals/annual_second_pass.txt"
SNAPSHOT = "2026-10-28"
# Where each question template fires over the 22, as listed in docs/plans/annual-report.md before the fold was built
FIRING = {"emphasis": ["DIXON", "MARUTI", "ULTRACEMCO"], "size": ["SYNGENE"], "rise": ["LT"]}

fx = json.loads(gzip.decompress(FIXTURE.read_bytes()))
truth = json.loads(TRUTH.read_text())
labels, split = truth["companies"], truth["split"]
syms = sorted(p.stem for p in COMPANIES.glob("*.json"))
checks, lines = [], []


def check(ok, what):
    checks.append(bool(ok))
    lines.append(f"{'ok  ' if ok else 'FAIL'} {what}")


def make(sym):
    """What the readers make from the fixture for one company, as build_annual.py --serve writes it."""
    company = json.loads((COMPANIES / f"{sym}.json").read_text())
    if sym in fx["reports"]:
        r = fx["reports"][sym]
        pages = {int(p): t for p, t in r["pages"].items()}
        return annual.compose(sym, r, {"reports": r["reports"], "notes": r["notes"], "pages_total": r["pages_total"]},
                              pages, company, fx["calls"]), pages, company
    u = fx["unread"].get(sym)
    return (annual.not_read(sym, {"url": u.get("url"), "filed": u.get("filed_text")}, u["why"]) if u else None), {}, company


made = {s: make(s) for s in syms}

# ---------- unit tests: the rules on lines met in these reports ----------
A = annual
check([A.number(x) for x in ("5,311", "1,11,006", "(12.5)", "9218.42*", "-", "Nil", "abc")] == [5311, 111006, -12.5, 9218.42, None, None, None],
      "figures: Indian grouping, brackets, a footnote star; a dash or Nil is not a figure")
check([round(A.to_crore(5311, "million"), 2), round(A.to_crore(111006, "lakh"), 2), round(A.to_crore(50640067, "thousand"), 2)] == [531.1, 1110.06, 5064.01],
      "units to crore: million, lakh, thousand")
check([A.unit_of(x) for x in ("(All amounts are in Indian Rupees Million, except", "` in Crores", "` / Lakhs", "v crore", "(C in ‘000)",
                              "(All amounts in H crores, unless", "( in crores)", "As at March 31, 2026")] ==
      ["million", "crore", "lakh", "crore", "thousand", "crore", "crore", None], "units as these PDFs print them, the rupee sign lost or swapped")
check(A.crore_text(628.5) == "629" and A.crore_text(3.74) == "3.7" and A.crore_text(1804.31) == "1,804", "crore shown as read: halves round up")
check(A.year_columns("Particulars 31 March 2026 31 March 2025 (a) ", "") == [2026, 2025]
      and A.year_columns("March 31, 2025 note 30 ... As at 31-03-2026 As at 31-03-2025", "") == [2026, 2025]
      and A.year_columns("", "As at March 31, 2025 As at March 31, 2026") == [2025, 2026], "year columns read nearest the claims line, in their printed order")
srf = {1: "32 CONTINGENT LIABILITIES\nAs at\nMarch 31, 2026\nAs at\nMarch 31, 2025\n(` in crores)\na\nClaims against the group not acknowledged as debts :\nSales tax and entry tax\n14.01\n14.01\nIncome Tax\n46.63\n238.78\n"}
check(not A.read_claims(srf, {"page": 1, "at": 0})["rows"], "SRF's case: a head ending in a colon, then a capitalised sub-row, gives no figure (the first held-out pass showed 14.01)")
wrap = {1: "36. Contingent liabilities\nParticulars\nAs at\nMarch 31, 2026\nAs at\nMarch 31, 2025\n` in crore\nClaims against the Group not acknowledged as debt (refer\nnote below)\n824\n782\n"}
check([(r["fy26"], r["fy25"]) for r in A.read_claims(wrap, {"page": 1, "at": 0})["rows"]] == [("824", "782")], "a claims label wrapped onto a lowercase line keeps its figures")
two = "\n".join(["(A) Claims against the Group disputed and not acknowledged as debts", "As at", "March 31, 2026", "As at", "March 31, 2025", "` in crore",
                 "(i) Excise", "562", "957", "143", "419", "Total", "705", "1,376", "(ii) GST", "1,281", "200", "Total", "1,281", "200", "(B) Guarantees"])
check(not A.read_claims({1: "38 CONTINGENT LIABILITIES\n" + two}, {"page": 1, "at": 0})["rows"], "a Total per head (Maruti) is never read as the claims total")
one = "\n".join(["(a) Claims (excluding claims by employees where amount not ascertainable)", "not acknowledged as debts:", "As at March 31, 2026", "As at March 31, 2025",
                 "Rs. Crores", "- Sales tax", "0.47", "0.47", "- Land", "-", "8.11", "- Income tax", "29.09", "-", "Total", "29.56", "8.58", "(b) Guarantees"])
got = A.read_claims({1: "28. (i) Contingent liabilities not provided for\n" + one}, {"page": 1, "at": 0})["rows"]
check([(r["fy26"], r["fy25"]) for r in got] == [("29.56", "8.58")], "one printed Total that its rows add up to is read (DCM Shriram's form)")
bad = one.replace("29.56", "30.56")
check(not A.read_claims({1: "28. Contingent liabilities\n" + bad}, {"page": 1, "at": 0})["rows"], "a Total its rows don't add up to is not read")
cci = A.term_patterns({"abbr": "CCI", "expansion": "Competition Commission of India"})
call = A.flat("the Competi-\ntion   Commission ruled; the cci and CCIL are not it")
check([n for n, _, rx in cci if rx.search(call)] == ["expansion"] and cci[1][1] == "Competition Commission",
      "terms: the expansion across a hyphenated line break, 'of India' optional; the abbreviation case-sensitive and word-bounded")
epr = A.term_patterns({"abbr": "EPR", "expansion": "Extended Producer Responsibility"})
check(not any(rx.search("Maruti Suzuki's first fully electric SUV represents a repricing") for _, _, rx in epr), "'represents' and 'repricing' are not EPR")
check(A.defined_term("Note 37(b) ... orders of the Competition Commission of India (‘CCI’) against which") == {"abbr": "CCI", "expansion": "Competition Commission of India"}
      and A.defined_term("under the Production Linked Incentive (PLI) Scheme") == {"abbr": "PLI", "expansion": "Production Linked Incentive"},
      "the paragraph's defined term: the abbreviation and the words whose initials it is")

# ---------- asserts ----------
check(all(s in labels for s in syms), f"every one of the {len(syms)} companies has a label ({sum(s in labels for s in syms)})")
check(all(made[s][0] is not None for s in syms), "every company was cut, or is listed as unread with its reason")
stale = [s for s in syms if made[s][0] and (not (SERVED / f"{s}.json").exists() or json.loads((SERVED / f"{s}.json").read_text()) != json.loads(json.dumps(made[s][0])))]
check(not stale, f"the served files are what the readers make from the fixture{': stale ' + ', '.join(stale) if stale else ''}")
late = [s for s, r in fx["reports"].items() if r["filed"] > SNAPSHOT]
check(not late, f"every report used was filed on or before {SNAPSHOT}{': ' + ', '.join(late) if late else ''}")

hits = [(s, h) for s, r in fx["reports"].items() for h in r["sweep"]]
loose = [(s, h["page"]) for s, h in hits if h["where"] == "unaccounted"]
check(not loose, f"the whole-PDF sweep: {len(hits)} modifying headings, each in a cut audit report or out of scope by a named rule{': unaccounted ' + str(loose) if loose else ''}")
rederive = []
for s, r in fx["reports"].items():
    pages = {int(p): t for p, t in r["pages"].items()}
    again = annual.sweep({p: pages[p] for p in {h["page"] for h in r["sweep"]}}, r["reports"])
    if sorted((h["page"], h["heading"], h["where"]) for h in again) != sorted((h["page"], h["heading"], h["where"]) for h in r["sweep"]):
        rederive.append(s)
check(not rederive, f"each sweep hit's place re-derives from its stored page{': ' + ', '.join(rederive) if rederive else ''}")
oos = sorted((s, h["page"], h["where"]) for s, h in hits if h["where"] not in ("standalone audit report", "consolidated audit report"))
lab_oos = sorted((s, x["page"], x["where"]) for s, l in labels.items() for x in l.get("out_of_scope", []))
check(oos == lab_oos, f"the out-of-scope hits are the labelled ones: {oos}")

quotes = bad_quotes = 0
figures = bad_figures = 0
for s in syms:
    out, pages, company = made[s]
    if not out or not out["read"]:
        continue
    for b in out["blocks"]:
        for it in b.get("items", []):
            quotes += 1
            bad_quotes += not annual.on_page(it["quote"], pages, it["src"]["page"])
            c = it.get("calls")
            if c and c.get("quote"):
                quotes += 1
                cp = {int(k): v for k, v in fx["calls"][c["url"]].items()}
                bad_quotes += not annual.on_page(c["quote"], cp, c["page"])
        for x in (b.get("trail") or {}).get("src", []):
            quotes += 1
            bad_quotes += not annual.on_page(x["quote"], pages, x["page"])
        if b.get("quote"):
            quotes += 1
            bad_quotes += not annual.on_page(b["quote"], pages, b["src"][0]["page"])
    cl = out["checks"]["claims"]
    if cl:
        for r in cl["rows"]:
            for v in (r["fy26"], r["fy25"]):
                figures += 1
                bad_figures += v not in pages.get(cl["page"], "") and v not in pages.get(cl["page"] + 1, "")
check(quotes and not bad_quotes, f"every quote shown is exact on its cited page: {quotes - bad_quotes}/{quotes}")
check(not bad_figures, f"every figure shown is printed on its note's page: {figures - bad_figures}/{figures}")

wrong_fig, false_eom, false_mod, ratio_bad = [], [], [], []
for s in syms:
    out, pages, company = made[s]
    lab = labels.get(s)
    if not out or not out["read"] or not lab:
        continue
    for k, r in out["checks"]["reports"].items():
        lr = lab["reports"].get(k)
        if lr is None or set(r["emphasis"]) - set(lr["emphasis"]):
            false_eom.append(f"{s} {k}")
        if r["modified"] and not (lr or {}).get("modified"):
            false_mod.append(f"{s} {k}")
    cl, lc = out["checks"]["claims"], lab["claims"]
    if cl and cl["rows"] and [[x["fy26"], x["fy25"]] for x in cl["rows"]] != lc.get("rows"):
        wrong_fig.append(s)
    if out["checks"]["ratio"] is not None:
        snap = company["snapshot"]
        if not (company["basis"] == out["set"] and snap["years"][-1] == "Mar 2026" and snap["pat"][-1] > 0):
            ratio_bad.append(s)
check(not wrong_fig, f"no claims figure shown that differs from its label{': ' + ', '.join(wrong_fig) if wrong_fig else ''}")
check(not false_eom, f"no emphasis of matter shown that the auditor didn't write{': ' + ', '.join(false_eom) if false_eom else ''}")
check(not false_mod, "no opinion shown as modified that isn't")
check(not ratio_bad, "a ratio to profit only where the note's set is the company file's basis and FY26 profit is positive")

neg_bad, negq_bad, unlabelled, other_words = [], [], [], []
for s in syms:
    out = made[s][0]
    if not out or not out["read"]:
        continue
    for c in out["checks"]["calls"]:
        n = len(c["read"])
        if c["negative"] and (not c["names"] or n < 1):
            neg_bad.append(s)
        lab = labels.get(s, {}).get("calls", {}).get(c["note"])
        if c["negative"]:
            if not lab or "other_words" not in lab:
                unlabelled.append(f"{s} {c['note']}")
            elif lab["other_words"]:
                other_words.append(f"{s} {c['note']}")
    for q in out["questions"]:
        if "Neither term is in the transcripts" in q:
            c = next((x for x in out["checks"]["calls"] if f"note {x['note']} " in q), None)
            if not c or not c["negative"] or len(c["read"]) < 3:
                negq_bad.append(s)
check(not neg_bad, "a 'neither appears' line only with a defined term and at least one readable call searched")
check(not negq_bad, "the question says the term isn't in the transcripts only when three or more readable calls were searched")
check(not unlabelled, f"every 'neither appears' line has a hand label{': missing ' + ', '.join(unlabelled) if unlabelled else ''}")
check(not other_words, f"no hand label found the calls discussing the matter in other words{': ' + ', '.join(other_words) if other_words else ''} (if one did, the negative form is withdrawn for every company)")
m = made.get("MARUTI", (None,))[0]
mc = m and next((c for c in m["checks"]["calls"] if c["note"] == "38(B)"), None)
check(mc and len(mc["read"]) == 1 and m["questions"] and "Neither term" not in m["questions"][0],
      "Maruti: one readable call of five, so its question takes the plain form")
check(all(len(made[s][0]["questions"]) <= 2 for s in syms if made[s][0]), "at most two questions a company")
k = made.get("KFINTECH", (None,))[0]
check(k and not k["read"] and "cover letter" in k["why"], "KFin: not read, and the page says the filing is a cover letter")

kinds = {"emphasis": "The auditor drew attention", "size": "years of profit. Which", "rise": "rose from"}
firing = {name: sorted(s for s in syms if made[s][0] and any(t in q for q in made[s][0]["questions"])) for name, t in kinds.items()}
if FIRING is None:
    lines.append(f"skip firing lists not pinned yet: {firing}")
else:
    check(firing == FIRING, f"the questions fire where the plan lists them: {firing}")
check(all(len(v) <= len(syms) // 2 for v in firing.values()), "no question rule fires on more than half the companies (base rate)")

sha_ok = sha_n = 0
badkeys = [s for s, r in fx["reports"].items() if not r["pages"] or not all(1 <= int(x) <= r["pages_total"] for x in r["pages"])]
check(not badkeys, f"the fixture's pages are keyed by the PDF's own page number{': ' + ', '.join(badkeys) if badkeys else ''}")
for s, r in fx["reports"].items():
    p = config.CACHE_DIR / "pdf" / (hashlib.sha1(r["url"].encode()).hexdigest() + ".pdf")
    if p.exists():
        sha_n += 1
        sha_ok += hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"]
if sha_n:
    check(sha_ok == sha_n, f"the fixture's sha256 matches the cached PDF: {sha_ok}/{sha_n}")
else:
    lines.append("skip sha256: no annual-report PDF in the local cache (CI)")

# ---------- scores ----------
def score(half):
    f = {k: [0, 0, 0] for k in ("report found", "opinion modified", "emphasis", "audit-trail exception", "claims note page", "claims figures")}
    shown = right = 0
    names = [s for s in split[half] if labels.get(s, {}).get("read")]
    for s in names:
        out, lab = made[s][0], labels[s]
        if not out or not out["read"]:
            for k, lr in lab["reports"].items():
                for fld in ("report found", "opinion modified", "emphasis", "audit-trail exception"):
                    f[fld][1] += 1
            continue
        got = out["checks"]["reports"]
        for k, lr in lab["reports"].items():
            r = got.get(k)
            for fld, ok, pos in (("report found", r and r["page"] == lr["page"], True),
                                 ("opinion modified", r and r["modified"] == lr["modified"], lr["modified"]),
                                 ("emphasis", r and r["emphasis"] == lr["emphasis"], bool(lr["emphasis"])),
                                 ("audit-trail exception", r and bool(r["trail"]) == lr["trail_exception"], lr["trail_exception"])):
                f[fld][0] += bool(ok); f[fld][1] += 1; f[fld][2] += bool(pos)
        cl, lc = out["checks"]["claims"], lab["claims"]
        f["claims note page"][0] += bool(cl and cl["page"] == lc["page"]); f["claims note page"][1] += 1; f["claims note page"][2] += 1
        want = lc.get("rows")
        got_rows = [[x["fy26"], x["fy25"]] for x in cl["rows"]] if cl else []
        f["claims figures"][0] += (got_rows == want) if want else (not got_rows)
        f["claims figures"][1] += 1; f["claims figures"][2] += bool(want)
        shown += bool(got_rows); right += bool(got_rows) and got_rows == want
    return f, shown, right, len(names)


lines.append("")
lines.append("scores: right / labelled, and how many of those labels are positives (a field with no positives tests false alarms only)")
summary = {}
for half in ("dev", "held_out"):
    f, shown, right, n = score(half)
    summary[half] = (f, shown, right, n)
    for k, (a, b, pos) in f.items():
        lines.append(f"  {half:8} {k:22} {a}/{b}   positives {pos}")
    lines.append(f"  {half:8} {'claims figures shown':22} {shown} of {n} reports read, {right} right")

lines.append("")
lines.append("thresholds, fixed in the plan before the readers ran on the held-out half")
f_all = {k: [summary['dev'][0][k][i] + summary['held_out'][0][k][i] for i in range(2)] for k in summary['dev'][0]}
aud = f_all["opinion modified"][0] == f_all["opinion modified"][1] and f_all["emphasis"][0] == f_all["emphasis"][1]
lines.append(f"  {'met   ' if aud else 'MISSED'} auditor: opinion and every emphasis of matter right on every report read ({f_all['emphasis'][0]}/{f_all['emphasis'][1]} emphasis, {f_all['opinion modified'][0]}/{f_all['opinion modified'][1]} opinion)")
lines.append(f"  {'met   ' if not wrong_fig else 'MISSED'} claims: zero wrong figures shown over all 22 ({len(wrong_fig)} wrong)")
ho = summary["held_out"]
lines.append(f"  {'met   ' if ho[1] >= 8 else 'MISSED'} claims: figures shown for at least 8 of the 11 held out ({ho[1]})")
lines.append(f"  {'met   ' if not bad_quotes else 'MISSED'} quotes: every one exact on its cited page ({quotes - bad_quotes}/{quotes})")
lines.append("")
lines.append("auditor recall rests on the dev half's three emphasis companies and the whole-PDF sweep: the planning probe had")
lines.append("already swept all 22 reports, so the held-out half was known to hold no emphasis and tests false alarms only.")
lines.append(f"firing: {firing}")
lines.append("")
lines.append(f"TOTAL {sum(checks)}/{len(checks)}")

text = "\n".join(lines) + "\n"
PASSES = {"--first-pass": (FIRST, "The first run of the frozen readers on the held-out half"),
          "--second-pass": (SECOND, "The second pass, after the fixes the first held-out pass called for (docs/plans/annual-report.md)")}
for flag, (path, what) in PASSES.items():
    if flag in sys.argv:
        if path.exists():
            raise SystemExit(f"{path.name} is already recorded; a recorded pass is never rewritten")
        path.write_text(f"{what}, {dt.date.today()}, kept as it came out.\n\n" + text)
# The recorded passes first, kept as they came out; this run last, so its TOTAL is the file's last
body = "".join(f"---- {path.name}, as recorded ----\n{path.read_text()}\n" for path, _ in PASSES.values() if path.exists())
body += "---- this run ----\n" + text
# A clone has no PDFs, so its run skips the sha256 check: it prints its own total and leaves the record of the full run as it is
if sha_n or not RESULT.exists():
    RESULT.write_text(body)
print(text, end="")
sys.exit(0 if all(checks) else 1)
