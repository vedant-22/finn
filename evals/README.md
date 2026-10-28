# Evals

Three scripts, all on real data. Run from the repo root; each prints its result and the last run is saved next to it.

## Filing triage: `run_classify.py`

24 real filings from the portfolio's last 30 days: 14 that NSE's subject line doesn't settle (so the model sees them) and 10 settled by rules. I labelled category and tier by reading each filing against the policy in `finn/classify.py`.

Last run (`classify_result.txt`): category 22/24, tier 21/24. One filing that should have interrupted didn't (a KFin Technologies results press release filed as a "Press Release", which the model read as an ordinary update; the results filing itself did interrupt). Two interrupted that shouldn't have: follow-up paperwork for a TCI buyback that had already been announced. FINN doesn't yet know that a filing repeats an earlier one.

Two labels were changed after I read the full letters, and both changes helped the score, so here they are:
- Sun Pharma, "Outcome of Board Meeting", 12 Oct. I first labelled it a note. The letter approves up to ₹10,000 cr of NCDs, about 18% of a year's revenue. Changed to interrupt.
- TCI, "Outcome of Board Meeting", 29 Sep. The subject line only mentions a China subsidiary, which I labelled a note. The same letter approves a ₹150 cr buyback. Changed to interrupt.

24 filings is small. It catches regressions; it doesn't prove the policy.

## Results numbers: `run_results.py`

For each of the 18 holdings, the latest quarter's first cut parsed from NSE's XBRL is compared with screener.in's quarterly table, which is compiled separately from the same filings. Agreement within 1% counts.

Last run (`results_result.txt`): 62/70. The 8 misses, and why:
- HDFC Bank PBT and PAT: screener uses a different consolidation line for the bank.
- L&T EBITDA: L&T's financial-services arm puts its interest cost inside operating expenses, so the standard EBITDA formula and screener's operating profit differ.
- Maruti and TCI PBT: the companies' own filings show their share of associates and JVs below PBT; screener adds it in.
- DCM Shriram revenue: gross versus net of excise duty.
- Cyient EBITDA and PBT: within 1.5%; I haven't found the cause.

FINN shows the number the company filed. Where a definition matters, that's the one I'd rather defend.

## Quote checking: `run_quotes.py`

The check that keeps the ledger honest. 15 promises are sampled from the built ledgers, and for each the script makes doctored versions.

Last run (`quotes_result.txt`):

| Case | Should | Result |
|---|---|---|
| Real quote | pass | 15/15 |
| One word dropped, commas removed | pass | 15/15 |
| A number changed | fail | 10/10 caught |
| "not" added | fail | 12/12 caught |
| Halves of two real sentences from different pages stitched | fail | 15/15 caught |
| Several words swapped for synonyms | pass if meaning holds | 7/13 pass |

The synonym case is where I chose to be strict. A quote with three or four words changed fails the check and the promise is dropped. Losing a real promise costs less than showing a quote management never said.

## The grades

Whether "kept" and "missed" are right. `sample_grades.py` prints a fixed sample of 20 graded promises with the quote, the verdict, the evidence and the quarterly numbers. I checked each by hand in [grades_review.md](grades_review.md): 18 hold. One was marked kept while its window was still open. One was a past action ("we took a price hike in January") read as a promise and graded against an unrelated quote. Twenty is a small sample, so read the grades as a first pass with the evidence one tap away.
