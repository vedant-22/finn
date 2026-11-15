"""docs/img/reaction.png from data/out/reaction_plot.json (written by evals/run_reaction.py). DESIGN.md colours."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data/out/reaction_plot.json").read_text())
INK, INK2, RULE, BRAND = "#333333", "#6A6970", "#D9D9D9", "#005DA3"
plt.rcParams.update({"font.family": "Helvetica", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": RULE})
fig, (a, b) = plt.subplots(2, 1, figsize=(4, 5.6), dpi=200, gridspec_kw={"height_ratios": [1.15, 1]})

groups = ["no filing", "fold", "note", "act without results", "act"]
for k, g in enumerate(groups):
    r, (lo, hi) = 100 * d["rates"][g], d["ci"][g]
    a.barh(k, r, color=BRAND if g == "act" else INK2, height=0.6)
    a.plot([100 * lo, 100 * hi], [k, k], color=INK, lw=1)
    a.text(100 * hi + 0.4, k, f"{r:.1f}%  (n {d['n'][g]:,})", va="center", fontsize=8.5, color=INK)
a.set_yticks(range(len(groups)), groups)
a.set_xlim(0, 30); a.set_xlabel("% of company-days that moved, with 95% CI")
a.set_title("How often the stock moved, by FINN's rule tier\nNSE, Nov 2025 to Oct 2026. Moved: |z| ≥ 3 or a band close", loc="left", x=-0.62, fontsize=9.5, color=INK)
for s in ("top", "right"):
    a.spines[s].set_visible(False); b.spines[s].set_visible(False)

days = list(range(-5, 6))
for name, col, lw in (("after close", BRAND, 1.8), ("in session", INK2, 1.2)):
    if name in d["align"]:
        v = d["align"][name]
        b.plot(days, v[:-1], color=col, lw=lw, label=f"filed {name} (n {v[-1]:,})")
b.axvspan(-0.5, 1.5, color="#EEF4F9", zorder=0)
b.set_xticks(days); b.set_xlabel("session from the event day"); b.set_ylabel("mean |z| that day")
b.set_title("Results days: the move lands on the event day", loc="left", x=-0.2, fontsize=9.5, color=INK)
b.set_ylim(0.7, 2.75); b.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=1)
fig.tight_layout()
fig.savefig(ROOT / "docs/img/reaction.png", facecolor="white", bbox_inches="tight", pad_inches=0.15)
print("wrote docs/img/reaction.png")
