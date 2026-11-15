"""C2: can the words of a vague filing say whether its stock will move? (docs/PRICE_REACTION.md)

Population: filings the rules can't settle, the ones a model reads today, on company-days with no rule-act filing.
Label: the company-day moved (|z| >= 3 or a band close; evals/reaction_days.csv.gz). Model: logistic regression
on TF-IDF of NSE's subject text with the company's name removed, plus the subject line, filing time and file size.
Split by time: train Nov-Jun, choose C on Jul, test Aug to 28 Oct. Not a trading signal: its heaviest words are
read as proposed rules, and no model runs at serving time.      python3 evals/run_c2.py
"""
import bisect, csv, datetime as dt, gzip, io, json, pathlib, re, sys
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from collections import Counter
from scipy.optimize import minimize
from scipy.sparse import csr_matrix, hstack
from finn import classify

# sklearn's build here doesn't load with numpy 2, so the three pieces needed are written out.
class Tfidf:
    def fit(self, docs, min_df=5, top=20000):
        df = Counter(t for d in docs for t in set(self.terms(d)))
        keep = [t for t, n in df.most_common(top) if n >= min_df]
        self.vocab = {t: i for i, t in enumerate(keep)}
        self.idf = np.array([np.log((1 + len(docs)) / (1 + df[t])) + 1 for t in keep])
        return self
    def terms(self, d):
        w = re.findall(r"[a-z][a-z0-9]+", d.lower())
        return w + [a + " " + b for a, b in zip(w, w[1:])]
    def transform(self, docs):
        r, c, v = [], [], []
        for i, d in enumerate(docs):
            for t, n in Counter(x for x in self.terms(d) if x in self.vocab).items():
                r.append(i); c.append(self.vocab[t]); v.append((1 + np.log(n)) * self.idf[self.vocab[t]])
        m = csr_matrix((v, (r, c)), shape=(len(docs), len(self.vocab)))
        norm = np.sqrt(np.asarray(m.multiply(m).sum(1)).ravel()); norm[norm == 0] = 1
        return csr_matrix(m.multiply(1 / norm[:, None]))
    def get_feature_names_out(self):
        return np.array(sorted(self.vocab, key=self.vocab.get))
TfidfVectorizer = lambda **kw: Tfidf()

class OneHotEncoder:
    def __init__(self, **kw): pass
    def fit(self, rows):
        n = Counter((j, v) for r in rows for j, v in enumerate(r))
        self.cols = {k: i for i, k in enumerate(k for k, c in n.items() if c >= 20)}
        return self
    def transform(self, rows):
        pairs = [(i, self.cols[(j, v)]) for i, r in enumerate(rows) for j, v in enumerate(r) if (j, v) in self.cols]
        return csr_matrix(([1.0] * len(pairs), ([a for a, _ in pairs], [b for _, b in pairs])), shape=(len(rows), len(self.cols)))

class LogisticRegression:
    """L2 logistic regression with balanced class weights, fitted by L-BFGS."""
    def __init__(self, C=1.0, **kw): self.C = C
    def fit(self, X, y):
        w = np.where(y == 1, len(y) / (2 * max(y.sum(), 1)), len(y) / (2 * max((1 - y).sum(), 1)))
        Xb = hstack([X, csr_matrix(np.ones((X.shape[0], 1)))]).tocsr()
        def f(b):
            z = Xb @ b; p = 1 / (1 + np.exp(-z))
            loss = -np.sum(w * (y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))) + 0.5 / self.C * b[:-1] @ b[:-1]
            g = Xb.T @ (w * (p - y)); g[:-1] += b[:-1] / self.C
            return loss, g
        b = minimize(f, np.zeros(Xb.shape[1]), jac=True, method="L-BFGS-B", options={"maxiter": 500}).x
        self.coef_, self.b0 = b[None, :-1], b[-1]
        return self
    def predict_proba(self, X):
        p = 1 / (1 + np.exp(-(X @ self.coef_[0] + self.b0)))
        return np.c_[1 - p, p]

def average_precision_score(y, p):
    o = np.argsort(-p, kind="stable"); y = np.asarray(y)[o]
    hits = np.cumsum(y)
    return float(np.sum((hits / np.arange(1, len(y) + 1))[y == 1]) / max(y.sum(), 1))

days = {(r["symbol"], r["date"]): r for r in csv.DictReader(io.StringIO(gzip.decompress((ROOT / "evals/reaction_days.csv.gz").read_bytes()).decode()))}
sess = json.loads((ROOT / "evals/reaction_meta.json").read_text())["sessions"]
REVERSE_TEXT = re.compile(r"\b(clarification|spurt in (the )?volume|price movement|news verification|rumou?r verification|takeover)\b", re.I)
rows = []
for f in sorted((ROOT / "data/raw/filings").glob("*.json.gz")):
    for x in json.loads(gzip.decompress(f.read_bytes())):
        if classify.by_rule(x) is not None:
            continue
        at = dt.datetime.strptime(x["an_dt"], "%d-%b-%Y %H:%M:%S")
        k = bisect.bisect_left(sess, at.date().isoformat())
        if k < len(sess) and sess[k] == at.date().isoformat() and at.time() >= dt.time(15, 30):
            k += 1
        r = days.get((x["symbol"], sess[k])) if k < len(sess) else None
        if not r or r["z"] == "" or r["day"] != "needs_reading":
            continue
        if REVERSE_TEXT.search(x.get("attchmntText") or ""):
            continue   # its text says it answers a move (a clarification, a spurt in volume): reverse-causal, as the subject rule would

        names = {w for w in re.findall(r"[a-z0-9]+", ((x.get("sm_name") or "") + " " + x["symbol"]).lower()) if len(w) > 2} | {"limited", "ltd"}
        text = " ".join(w for w in re.findall(r"[A-Za-z0-9]+", x.get("attchmntText") or "") if w.lower() not in names)   # no company names
        size = float(re.sub(r"[^\d.]", "", str(x.get("fileSize") or "0")) or 0)
        rows.append((sess[k], text, x["desc"], "pre" if at.time() < dt.time(9, 15) else "in" if at.time() < dt.time(15, 30) else "post",
                     np.log1p(size), int(r["reacted"])))

date = np.array([r[0] for r in rows]); y = np.array([r[5] for r in rows])
tr, va, te = date < "2026-07-01", (date >= "2026-07-01") & (date < "2026-08-01"), date >= "2026-08-01"
tf = TfidfVectorizer().fit([r[1] for r, t in zip(rows, tr) if t])
oh = OneHotEncoder(handle_unknown="ignore", min_frequency=20).fit([[r[2], r[3]] for r, t in zip(rows, tr) if t])
def X(mask, text=True):
    sub = [r for r, m in zip(rows, mask) if m]
    parts = [oh.transform([[r[2], r[3]] for r in sub]), csr_matrix([[r[4]] for r in sub])]
    return hstack(([tf.transform([r[1] for r in sub])] if text else []) + parts).tocsr()

lines = [f"population: {len(rows)} vague filings on company-days with no rule-act filing; moved {100 * y.mean():.1f}%; "
         f"train {tr.sum()} (Nov-Jun), choose C {va.sum()} (Jul), test {te.sum()} (Aug-Oct)"]
fit = {}
for text in (True, False):
    best = max(((average_precision_score(y[va], LogisticRegression(C=c, max_iter=3000, class_weight="balanced").fit(X(tr, text), y[tr]).predict_proba(X(va, text))[:, 1]), c)
                for c in (0.03, 0.1, 0.3, 1, 3)))
    m = LogisticRegression(C=best[1], max_iter=3000, class_weight="balanced").fit(X(tr | va, text), y[tr | va])
    fit[text] = (m, m.predict_proba(X(te, text))[:, 1])
base = {}
for r, t in zip(rows, tr | va):
    if t:
        base.setdefault(r[2], []).append(r[5])
prior = y[tr | va].mean()
fit["subject"] = (None, np.array([np.mean(base[r[2]]) if len(base.get(r[2], [])) >= 20 else prior for r, t in zip(rows, te) if t]))

dte, yte = date[te], y[te]
ud = sorted(set(dte)); di = np.array([ud.index(d) for d in dte])
W = np.random.default_rng(7).multinomial(len(ud), np.full(len(ud), 1 / len(ud)), size=500)
def top10(p):
    """Recall when the top 10% of each day's filings are read first."""
    hit = 0
    for d in ud:
        m = dte == d
        k = max(1, int(np.ceil(0.1 * m.sum())))
        hit += yte[m][np.argsort(-p[m])[:k]].sum()
    return hit / max(yte.sum(), 1)
for name, key in (("text model", True), ("without the text", False), ("subject's base rate", "subject")):
    p = fit[key][1]
    ap = average_precision_score(yte, p)
    boots = []
    for w in W:
        idx = np.repeat(np.arange(len(yte)), w[di])
        if yte[idx].any():
            boots.append(average_precision_score(yte[idx], p[idx]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    lines.append(f"{name}: PR-AUC {ap:.3f} (95% CI {lo:.3f}-{hi:.3f}; a coin scores {yte.mean():.3f}); recall reading the top 10% a day {100 * top10(p):.0f}%")
p = fit[True][1]; q = np.quantile(p, [0, .2, .4, .6, .8, 1])
p1, p0 = fit[True][1], fit[False][1]
diffs = []
for w in W:   # paired: the same resampled days score both models, so the difference gets its own interval
    idx = np.repeat(np.arange(len(yte)), w[di])
    if yte[idx].any():
        diffs.append(average_precision_score(yte[idx], p1[idx]) - average_precision_score(yte[idx], p0[idx]))
lo, hi = np.percentile(diffs, [2.5, 97.5])
lines.append(f"text model minus without the text, paired: {average_precision_score(yte, p1) - average_precision_score(yte, p0):+.3f} "
             f"(95% CI {lo:+.3f} to {hi:+.3f}): " + ("the text adds something" if lo > 0 else "the interval includes zero: no measurable gain from the text"))
lines.append("calibration by quintile (predicted, inflated by class weighting -> moved): " + ", ".join(
    f"{100 * p[(p >= a) & (p <= b)].mean():.0f}%->{100 * yte[(p >= a) & (p <= b)].mean():.0f}%" for a, b in zip(q[:-1], q[1:])))
m = fit[True][0]; vocab = tf.get_feature_names_out(); coef = m.coef_[0][:len(vocab)]
top = [vocab[i] for i in np.argsort(-coef)[:15]]
lines.append("heaviest words (proposed rule terms, for review): " + ", ".join(top))
(ROOT / "evals/c2_weights.json").write_text(json.dumps({"C": float(m.C), "words": {vocab[i]: round(float(coef[i]), 3) for i in np.argsort(-np.abs(coef))[:300]}}))
print("\n".join(lines))
(ROOT / "evals/c2_result.txt").write_text("\n".join(lines) + "\n")
