"""Price reaction: do the filings FINN's rules mark act move their stock more often than the ones they fold?

Reads evals/reaction_days.csv.gz and reaction_meta.json (pipeline/build_reaction.py, copied from data/out). A company-day "moved" when |z| >= 3 over the
event day and the next, or it closed at a price band. Intervals: a bootstrap over dates (B = 20,000 multinomial
weights over per-date sums), so a market-wide day counts once. Misses: Benjamini-Hochberg at q = 0.10 over a
family fixed from counts alone, before any rate was computed.      python3 evals/run_reaction.py
"""
import collections, csv, datetime as dt, gzip, io, json, pathlib, sys
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/out"
B, SEED, Q = 20000, 7, 0.10
# (subject, tier) pairs with at least 200 single-subject company-days that have a z: from counts alone, committed
# (with the table) before any rate was computed.
FAMILY = [["Allotment of Securities", "fold"], ["Analysts/Institutional Investor Meet/Con. Call Updates", "fold"],
          ["Analysts/Institutional Investor Meet/Con. Call Updates", "note"], ["Bagging/Receiving of orders/contracts", "note"],
          ["Certificate under SEBI (Depositories and Participants) Regulations, 2018", "fold"], ["Copy of Newspaper Publication", "fold"],
          ["Credit Rating", "fold"], ["ESOP/ESOS/ESPS", "fold"], ["Investor Presentation", "note"], ["Monitoring Agency Report", "fold"],
          ["Outcome of Board Meeting", "act"], ["Shareholders meeting", "fold"], ["Trading Window", "fold"]]

rows = list(csv.DictReader(io.StringIO(gzip.decompress((ROOT / "evals/reaction_days.csv.gz").read_bytes()).decode())))
meta = json.loads((ROOT / "evals/reaction_meta.json").read_text())
Zrows = [r for r in rows if r["z"] != ""]
dates = sorted({r["date"] for r in Zrows}); di = {d: k for k, d in enumerate(dates)}
D = len(dates)
idx = np.array([di[r["date"]] for r in Zrows]); moved = np.array([int(r["reacted"]) for r in Zrows])
col = lambda k: np.array([r[k] for r in Zrows])
day, res, subj, cat = col("day"), col("results") == "1", col("subject"), col("category")
W = np.random.default_rng(SEED).multinomial(D, np.full(D, 1 / D), size=B).astype(np.float32)

def rate(mask):
    n, k = np.bincount(idx[mask], minlength=D).astype(np.float32), np.bincount(idx[mask], moved[mask], minlength=D).astype(np.float32)
    with np.errstate(all="ignore"):
        return k.sum() / max(n.sum(), 1), (W @ k) / (W @ n), int(n.sum())

def ratio(a, b):
    (pa, da, na), (pb, db, nb) = rate(a), rate(b)
    lo, hi = np.nanpercentile(da / db, [2.5, 97.5])
    return pa / pb, lo, hi, na, nb, da / db

lines = []
say = lambda s: lines.append(s)
NONE, ACT, FOLD, NOTE = day == "none", day == "act", day == "fold", day == "note"
months = (dt.date.fromisoformat(dates[-1]) - dt.date.fromisoformat(dates[0])).days / 30.4
say(f"coverage: {len(rows)} company-days ({sum(r['day'] != 'none' for r in rows)} with filings), {len(Zrows)} with a z, "
    f"{D} event days from {dates[0]} to {dates[-1]} ({months:.1f} months); {meta['adjusted']} adjustment days left out")
# Matching: a filing that finds no price row is lost silently, so the study stops if too many do (an ISIN-only match
# once lost 19%). A top-500 stock files results about four times a year; far fewer means its filings aren't matched.
share, ryear = meta["matched"] / meta["filings"], meta["results_a_year_top500"]
match_ok = share >= 0.97 and 3 <= ryear <= 5 and len(set(meta["top500"])) == len(meta["top500"])
say(f"matching: {meta['matched']:,} of {meta['filings']:,} filings matched a price ({share:.1%}); the rest from {meta['unmatched_symbols']} symbols "
    f"with no EQ or BE price all year; a top-500 stock's results filings a year: median {ryear:.1f}: "
    + ("passes" if match_ok else "FAILS: stop and fix the match"))
floor_ok = months >= 3 and ACT.sum() >= 200
say(f"archive floor (3 months and 200 act company-days): {'met' if floor_ok else 'NOT met: the headline stays out of the summary'}")

# The lead: act against fold among filing days, then without results.
N, lo, hi, na, nf, _ = ratio(ACT, FOLD)
N2, lo2, hi2, na2, _, _ = ratio(ACT & ~res, FOLD)
say(f"lead: act moved {N:.1f}x as often as fold (95% CI {lo:.1f}-{hi:.1f}); act {na}, fold {nf} company-days")
say(f"lead without results: {N2:.1f}x (95% CI {lo2:.1f}-{hi2:.1f}); act without results {na2} company-days")
weak = lo <= 1 or N2 < 1.5
say(f"lead strength: {'WEAK: lead with the live market day' if weak else 'holds'}")
for name, m in (("act", ACT), ("act without results", ACT & ~res), ("note", NOTE), ("fold", FOLD), ("no filing", NONE),
                ("needs the reading", day == "needs_reading"), ("reverse-causal", day == "reverse")):
    p, d, n = rate(m)
    a, b = np.nanpercentile(d, [2.5, 97.5])
    say(f"rate {name}: {100 * p:.1f}% (95% CI {100 * a:.1f}-{100 * b:.1f}), n {n}" + (" (too few)" if n < 200 else ""))
L, llo, lhi, *_ = ratio(ACT, NONE)
say(f"context: act against no-filing days {L:.1f}x (95% CI {llo:.1f}-{lhi:.1f})")
vol = np.array([int(r["vol3"]) for r in Zrows])
say(f"second label, volume 3x its 20-session median: act {100 * vol[ACT].mean():.0f}%, fold {100 * vol[FOLD].mean():.0f}%, no filing {100 * vol[NONE].mean():.0f}%")

# Categories, then subjects, as lift over no-filing days.
for c in sorted({x for x in cat if x}):
    m = (cat == c) & (ACT | NOTE | FOLD)
    if m.sum() >= 50:
        l, a, b, n, *_ = ratio(m, NONE)
        say(f"category {c}: lift {l:.1f} (95% CI {a:.1f}-{b:.1f}), n {n}" + (" (too few)" if n < 200 else ""))

tier_of = {(s, t): t for s, t in FAMILY}
draws = {(s, t): ratio((subj == s) & (day == t), NONE) for s, t in FAMILY}
acts = [k for k in FAMILY if k[1] == "act"]
bar_act = np.nanmedian(np.array([draws[tuple(k)][5] for k in acts]), axis=0) if acts else None
tests = []
for (s, t), (l, a, b, n, _, d) in sorted(draws.items(), key=lambda kv: -kv[1][0]):
    if t == "act":
        diff, bar = d - 1.5, "1.5"                      # too loud: lift under 1.5
        p = (np.sum(diff >= 0) + 1) / (B + 1)
    elif bar_act is not None:
        diff, bar = d - bar_act, "the median act subject"   # too quiet: lift above the median act subject's
        p = (np.sum(diff <= 0) + 1) / (B + 1)
    else:
        continue
    tests.append((p, s, t, l, a, b, n, bar, d))
    say(f"subject [{t}] {s}: lift {l:.1f} (95% CI {a:.1f}-{b:.1f}), n {n}, p {p:.4f} against {bar}")
m = len(tests)
order = sorted(tests)
kept = max((k + 1 for k, x in enumerate(order) if x[0] <= Q * (k + 1) / m), default=0)
say(f"named misses: {kept} of {m} subjects survive Benjamini-Hochberg at q {Q}; expected false finds at most {Q * kept:.1f}")
for p, s, t, l, a, b, n, bar, d in order[:kept]:
    fa, fb = np.nanpercentile(d + (1.5 if t == "act" else bar_act), [50 * kept * Q / m, 100 - 50 * kept * Q / m])
    say(f"miss [{t}] {s}: lift {l:.1f}, FCR-adjusted interval {fa:.1f}-{fb:.1f}, n {n}; proposed: {'note' if t == 'act' else 'act'}")
# The test above could only flag a quiet subject that moves like results: the family has one act subject, so its
# median is board-meeting outcomes. This second test is post hoc, its bar chosen after the rates were seen, so it is
# exploratory and never a rule edit on its own: a quiet subject is flagged if it moves more than twice as often as a
# no-filing day.
quiet = [(p, s, t, l, a, b, n, d) for p, s, t, l, a, b, n, bar, d in tests if t != "act"]
quiet = sorted(((np.sum(d - 2.0 <= 0) + 1) / (B + 1), s, t, l, a, b, n) for _, s, t, l, a, b, n, d in quiet)
kq = max((k + 1 for k, x in enumerate(quiet) if x[0] <= Q * (k + 1) / len(quiet)), default=0)
say(f"pre-registered bar for a quiet subject: the median act subject, {np.median(bar_act):.1f}x, from {len(acts)} act subject(s)")
say(f"exploratory, post hoc: {kq} of {len(quiet)} fold or note subjects move more than 2x a no-filing day, surviving Benjamini-Hochberg at q {Q}")
for p, s, t, l, a, b, n in quiet[:max(kq, 3)]:
    say(f"exploratory [{t}] {s}: lift {l:.1f} (95% CI {a:.1f}-{b:.1f}), n {n}, p {p:.4f} against 2.0" + (" (survives)" if (p, s) in [(x[0], x[1]) for x in quiet[:kq]] else ""))

# Alignment: results days' mean |z| by day, which must peak on day 0 or +1.
al = meta["align"]
pooled = np.average(np.array([v[:-1] for v in al.values()]), axis=0, weights=[v[-1] for v in al.values()])
peak = int(np.argmax(pooled)) - 5
say(f"alignment: results days' mean |z| peaks on day {peak:+d} ({pooled.max():.2f} against {np.delete(pooled, [5, 6]).max():.2f} elsewhere): "
    + ("passes" if peak in (0, 1) else "FAILS: stop and fix the event day"))
for b, v in al.items():
    say(f"alignment {b}: n {v[-1]}, day 0 {v[5]:.2f}, day +1 {v[6]:.2f}, other days at most {max(v[:5] + v[7:-1]):.2f}")

# Interrupts a week for a 20-stock book drawn from the 500 most traded.
weeks = len(meta["sessions"]) / 5
by_sym = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r["day"] != "none":
        by_sym[r["symbol"]][0] += r["day"] == "act"; by_sym[r["symbol"]][1] += r["upper_act"] == "1"
rng = np.random.default_rng(SEED)
books = [rng.choice(meta["top500"], 20, replace=False) for _ in range(2000)]
low = np.array([sum(by_sym[s][0] for s in b) for b in books]) / weeks
up = np.array([sum(by_sym[s][1] for s in b) for b in books]) / weeks
top = set(meta["top500"])
in_top = np.array([r["symbol"] in top for r in Zrows])
say(f"interrupts a week, 20-stock book: median {np.median(low):.1f} (90th percentile {np.percentile(low, 90):.1f}) from rule-settled filings, "
    f"up to {np.median(up):.1f} ({np.percentile(up, 90):.1f}) if every filing that needs a model were act; "
    f"{100 * moved[ACT & in_top].mean():.0f}% of the rule-settled ones moved the price")

# Cross-check on the tiers the app shipped for the 28 Oct snapshot.
snap = json.loads((ROOT / "web/public/data/push.json").read_text())["filings"]
sess = meta["sessions"]; zmap = {(r["symbol"], r["date"]): int(r["reacted"]) for r in Zrows}
got = collections.defaultdict(list)
for f in snap:
    at = dt.datetime.fromisoformat(f["at"])
    k = next((d for d in sess if d > at.date().isoformat() or (d == at.date().isoformat() and at.time() < dt.time(15, 30))), None)
    if k and (f["symbol"], k) in zmap:
        got[f["tier"]].append(zmap[(f["symbol"], k)])
say("snapshot cross-check (shipped tiers, small n): " + ", ".join(f"{t} {100 * np.mean(v):.0f}% of {len(v)}" for t, v in sorted(got.items())))
say(f"bootstrap B {B}, seed {SEED}; family of {len(FAMILY)} subjects fixed before rates")

print("\n".join(lines))
(ROOT / "evals/reaction_result.txt").write_text("\n".join(lines) + "\n")
GROUPS = (("no filing", NONE), ("fold", FOLD), ("note", NOTE), ("act without results", ACT & ~res), ("act", ACT))
OUT.mkdir(parents=True, exist_ok=True)   # a fresh checkout has no data/out
json.dump({"rates": {g: float(rate(m)[0]) for g, m in GROUPS}, "n": {g: rate(m)[2] for g, m in GROUPS},
           "ci": {g: [float(v) for v in np.nanpercentile(rate(m)[1], [2.5, 97.5])] for g, m in GROUPS},
           "align": al, "lead": [float(N), float(lo), float(hi)]}, open(OUT / "reaction_plot.json", "w"))
sys.exit(0 if peak in (0, 1) else 1)
