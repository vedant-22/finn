"""The company-day table for the price-reaction study (docs/PRICE_REACTION.md), from the raw archive.

A company-day is a company and the first session whose close follows its filing (the event day); its window
is that day and the next. It is credited to its loudest filing under FINN's rules. Abnormal return: the
stock's return over the window from NSE's previous close, minus the market median each day; z divides by
sigma*sqrt(2), sigma from the prior 60 sessions with no non-routine filing and no adjustment.
    python3 pipeline/build_reaction.py   ->  data/out/reaction_days.csv.gz, data/out/reaction_meta.json
"""
import bisect, collections, csv, datetime as dt, gzip, io, json, pathlib, re, sys
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import classify, triage

RAW, OUT = ROOT / "data/raw", ROOT / "data/out"
# Filings that answer a price move rather than cause one. Reported apart, never counted as act or fold.
REVERSE = ("Spurt in Volume", "Price movement", "News Verification", "Rumour Verification", "Clarification", "Takeover", "PIT", "Insider")
REVERSE_RX = re.compile(r"\b(" + "|".join(map(re.escape, REVERSE)) + r")\b", re.I)   # whole words: "PIT" isn't "Capital"
RANK = {"fold": 0, "note": 1, "act": 2}
BANDS = np.array([2, 5, 10, 20])
CLOSE_T = dt.time(15, 30)

def load_prices():
    """One row per company: a symbol and every ISIN it traded under. An ISIN changes on a split or a face-value change,
    and NSE's announcements keep the old one, so keying by ISIN alone lost a fifth of the year's filings (HDFC Bank's
    among them; found in review). A rename keeps the ISIN, so the new symbol joins the old row."""
    days = sorted(p.name[:10] for p in (RAW / "prices").glob("*.csv.gz"))
    syms, isins, rows = {}, {}, []
    for t, d in enumerate(days):
        for r in csv.DictReader(io.StringIO(gzip.decompress((RAW / "prices" / f"{d}.csv.gz").read_bytes()).decode())):
            i = syms.get(r["TckrSymb"], isins.get(r["ISIN"]))
            if i is None:
                i = len(syms)
            syms.setdefault(r["TckrSymb"], i); isins.setdefault(r["ISIN"], i)
            rows.append((i, t, r["TckrSymb"], r["SctySrs"] == "EQ", *(float(r[k] or "nan") for k in ("ClsPric", "PrvsClsgPric", "HghPric", "LwPric", "TtlTradgVol", "TtlTrfVal"))))
    n = max(syms.values()) + 1
    P = {k: np.full((n, len(days)), np.nan) for k in ("close", "prev", "high", "low", "vol", "turn")}
    sym, eq = [""] * n, np.zeros((n, len(days)), bool)
    for i, t, s, is_eq, *v in rows:
        if np.isfinite(P["close"][i, t]) and (eq[i, t] or not is_eq):
            continue                      # one price a company a day: EQ over BE
        sym[i], eq[i, t] = s, is_eq
        for k, x in zip(P, v):
            P[k][i, t] = x
    return days, syms, isins, sym, P

def kind(x):
    """What FINN's rules say about one filing, and whether that is final without a model."""
    if REVERSE_RX.search(x["desc"]):
        return "reverse", None
    r = classify.by_rule(x)
    if r is None:
        return "vague", None
    cat, tier, _ = r
    if (cat == "management_change" and tier != "fold") or (tier == "act" and cat in triage.SIZEABLE):
        return "model_dependent", cat     # people or size can change the tier
    return tier, cat

def main():
    days, syms, isins, sym, P = load_prices()
    sdate = [dt.date.fromisoformat(d) for d in days]
    n, T = P["close"].shape
    r = P["close"] / P["prev"] - 1
    prior_close = np.concatenate([np.full((n, 1), np.nan), P["close"][:, :-1]], axis=1)
    # An adjustment day: NSE moved the previous close (over 0.5%), or the day's return is beyond any price band
    # (over 30%). The bhavcopy's previous close is NOT adjusted for bonuses and splits: Nestle's and HDFC Bank's
    # 1:1 bonuses in Aug 2025 show as -51% and -50% days. The second rule catches them.
    with np.errstate(all="ignore"):
        adj = (np.abs(P["prev"] / prior_close - 1) > 0.005) | (np.abs(r) > 0.30)
    ok = np.isfinite(r) & ~adj
    med = np.array([np.median(r[ok[:, t], t]) if ok[:, t].any() else np.nan for t in range(T)])
    ar = np.where(ok, r - med, np.nan)

    filings, read, unmatched = {}, 0, collections.Counter()   # (company index, event session) -> list of (kind, category, desc, bucket)
    for f in sorted((RAW / "filings").glob("*.json.gz")):
        for x in json.loads(gzip.decompress(f.read_bytes())):
            read += 1
            i = syms.get(x.get("symbol"), isins.get(x.get("sm_isin")))
            if i is None:
                unmatched[x.get("symbol")] += 1   # no EQ or BE price all year: SME, debt-only, suspended or delisted
                continue
            at = dt.datetime.strptime(x["an_dt"], "%d-%b-%Y %H:%M:%S")
            t = bisect.bisect_left(sdate, at.date())
            if t < T and sdate[t] == at.date() and at.time() >= CLOSE_T:
                t += 1
            if t >= T - 1:
                continue
            bucket = "before open" if at.time() < dt.time(9, 15) and sdate[t] == at.date() else "in session" if sdate[t] == at.date() else "after close"
            k, cat = kind(x)
            filings.setdefault((i, t), []).append((k, cat, x["desc"], bucket))
    busy = np.zeros((n, T), bool)
    for (i, t), fs in filings.items():
        if any(k != "fold" for k, *_ in fs):
            busy[i, t] = busy[i, t + 1] = True

    # sigma, z, band closes and volume for every stock and session at once
    SIG, V20 = np.full((n, T), np.nan), np.full((n, T), np.nan)
    with np.errstate(all="ignore"):
        for t in range(60, T):
            W = np.where(busy[:, t - 60:t], np.nan, ar[:, t - 60:t])
            sd = np.nanstd(W, axis=1, ddof=1)
            keep = (np.isfinite(W).sum(1) >= 40) & (np.isfinite(P["close"][:, t - 60:t]).sum(1) >= 50) \
                   & (np.nanmedian(P["turn"][:, t - 60:t], axis=1) >= 1e7)
            SIG[:, t] = np.where(keep, sd, np.nan)
            V20[:, t] = np.nanmedian(P["vol"][:, t - 20:t], axis=1)
        Z = np.full((n, T), np.nan)
        Z[:, :-1] = (ar[:, :-1] + ar[:, 1:]) / (SIG[:, :-1] * np.sqrt(2))
        at_band = np.isfinite(r) & ((P["close"] == P["high"]) | (P["close"] == P["low"])) \
                  & (np.min(np.abs(np.abs(r[..., None] * 100) - BANDS), axis=-1) <= 0.1)
        BAND = np.zeros((n, T), bool); BAND[:, :-1] = at_band[:, :-1] | at_band[:, 1:]
        VOL3 = np.zeros((n, T), bool); VOL3[:, :-1] = np.fmax(P["vol"][:, :-1], P["vol"][:, 1:]) >= 3 * V20[:, :-1]

    def reaction(i, t):
        if not np.isfinite(Z[i, t]):
            return None
        return round(float(Z[i, t]), 3), int(BAND[i, t]), int(VOL3[i, t]), int(abs(Z[i, t]) >= 3 or BAND[i, t])

    first = bisect.bisect_left(sdate, dt.date(2025, 11, 1))
    rows, align = [], {b: [] for b in ("before open", "in session", "after close")}
    for (i, t), fs in filings.items():
        ks = [k for k, *_ in fs]
        audited = [(k, c, d) for k, c, d, _ in fs if k in RANK]
        top = max((RANK[k] for k, *_ in audited), default=None)
        day = ("reverse" if "reverse" in ks else "act" if top == 2 else "needs_reading" if {"vague", "model_dependent"} & set(ks)
               else {0: "fold", 1: "note"}[top])
        res = any(c == "results" and k == "act" for k, c, _ in audited)
        subj = audited[0][2] if len({d for *_, d in audited}) == 1 and len(fs) == len(audited) else "mixed"
        cat = next((c for k, c, _ in audited if RANK[k] == top), "")
        upper = int(day == "act" or (day != "reverse" and bool({"vague", "model_dependent"} & set(ks))))
        rx = reaction(i, t)
        rows.append([days[t], sym[i], day, upper, int(res), subj, cat, fs[0][3], *(rx or ("", "", "", ""))])
        if res and day == "act" and 5 <= t < T - 6 and np.isfinite(s := SIG[i, t]):
            align[next(b for k, c, d, b in fs if c == "results")].append([abs(ar[i, t + k]) / s if np.isfinite(ar[i, t + k]) else np.nan for k in range(-5, 6)])
    near = np.zeros((n, T), bool)  # company-days with no filing on the day before, the day, or the day after
    for (i, t) in filings:
        near[i, max(0, t - 1):t + 2] = True
    for i, t in zip(*np.nonzero(~near & np.isfinite(Z))):
        if t >= first:
            rows.append([days[t], sym[i], "none", 0, 0, "", "", "", *reaction(i, t)])
    OUT.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["date", "symbol", "day", "upper_act", "results", "subject", "category", "bucket", "z", "band", "vol3", "reacted"])
    w.writerows(sorted(rows, key=lambda x: (x[0], x[1])))
    (OUT / "reaction_days.csv.gz").write_bytes(gzip.compress(buf.getvalue().encode(), 9, mtime=0))
    with np.errstate(all="ignore"):
        traded = np.nanmedian(P["turn"][:, first:], axis=1)
    files = np.zeros(n, bool); files[[i for i, _ in filings]] = True   # ETFs and companies that file elsewhere (MCX) can't be held for news
    top500 = [sym[i] for i in np.argsort(-np.where(files, np.nan_to_num(traded), -1.0))[:500]]
    (OUT / "reaction_meta.json").write_text(json.dumps({
        "align": {b: np.nanmean(np.array(v), axis=0).round(3).tolist() + [len(v)] for b, v in align.items() if v},
        "top500": top500, "sessions": days[first:], "filings": read, "adjusted": int(adj[:, first:].sum()),
        "matched": read - sum(unmatched.values()), "unmatched_symbols": len(unmatched),
        "results_a_year_top500": float(np.median([sum(1 for (i, t), fs in filings.items() if i == syms[s] and t >= first and any(c == "results" for _, c, *_ in fs))
                                                  for s in top500]) * 250 / max(1, T - first)),
        "split_check": {k: bool(adj[isins[i], days.index(d)]) for k, i, d in (("NESTLEIND 2025-08-08", "INE239A01024", "2025-08-08"),
                                                                              ("HDFCBANK 2025-08-26", "INE040A01034", "2025-08-26")) if i in isins}}))
    print(len(rows), "company-days;", sum(1 for x in rows if x[2] != "none"), "with filings")

if __name__ == "__main__":
    main()
