# Evals

Run from the repo root; each prints its result and the last run is saved next to it. `run_classify.py`, `run_results.py` and `run_quotes.py` use real data. `run_network.py` checks the Network core (see `docs/NETWORK_CORE.md`). `run_security.py` needs no model and no network.

## Filing triage: `run_classify.py`

24 real filings from the portfolio's last 30 days: 14 that NSE's subject line doesn't settle (so the model sees them) and 10 settled by rules. Category and tier were labelled by reading each filing against the policy in `finn/classify.py`.

Last run (`classify_result.txt`): category 22/24, tier 21/24. One filing that should have been an act wasn't (a KFin Technologies results press release filed as a "Press Release", which the model read as an ordinary update; the results filing itself was an act). Two were acts that shouldn't have been: follow-up paperwork for a TCI buyback already announced. FINN doesn't yet know that a filing repeats an earlier one.

Two labels were changed after the full letters were read, and both changes helped the score, so they are listed:
- Sun Pharma, "Outcome of Board Meeting", 12 Oct. First labelled a note. The letter approves up to ₹10,000 cr of NCDs, about 18% of a year's revenue. Changed to act.
- TCI, "Outcome of Board Meeting", 29 Sep. The subject line mentions only a China subsidiary, first labelled a note. The same letter approves a ₹150 cr buyback. Changed to act.

24 filings is small. It catches regressions; it doesn't prove the policy.

## Results numbers: `run_results.py`

For each of the 18 holdings, the latest quarter's first cut parsed from NSE's XBRL is compared with screener.in's quarterly table, which is compiled separately from the same filings. Agreement within 1% counts.

Last run (`results_result.txt`): 62/70. The 8 misses, and why:
- HDFC Bank PBT and PAT: screener uses a different consolidation line for the bank.
- L&T EBITDA: L&T's financial-services arm puts its interest cost inside operating expenses, so the standard EBITDA formula and screener's operating profit differ.
- Maruti and TCI PBT: the companies' own filings show their share of associates and JVs below PBT; screener adds it in.
- DCM Shriram revenue: gross versus net of excise duty.
- Cyient EBITDA and PBT: within 1.5%; the cause isn't found yet.

FINN shows the number the company filed. Where a definition matters, that is the one to defend.

## Quote checking: `run_quotes.py`

The check that keeps the promise ledger honest. 15 promises are sampled from the built ledgers, and for each the script makes doctored versions.

Last run (`quotes_result.txt`):

| Case | Should | Result |
|---|---|---|
| Real quote | pass | 15/15 |
| One word dropped, commas removed | pass | 15/15 |
| A number changed | fail | 10/10 caught |
| "not" added | fail | 12/12 caught |
| Halves of two real sentences from different pages stitched | fail | 15/15 caught |
| Several words swapped for synonyms | pass if meaning holds | 7/13 pass |

The synonym case is strict by choice. A quote with three or four words changed fails the check and the promise is dropped. Losing a real promise costs less than showing a quote management never said.

## The grades

Whether "kept" and "missed" are right. `sample_grades.py` prints a fixed sample of 20 graded promises with the quote, the verdict, the evidence and the quarterly numbers. Each was checked by hand in [grades_review.md](grades_review.md): 17 hold. One was marked kept while its window was still open. One was a past action ("we took a price hike in January") read as a promise and graded against an unrelated quote. One was graded on evidence about a different divestment; the first pass missed it, and it was corrected by hand on 31 Oct. Twenty is a small sample, so the grades are a first pass with the evidence one tap away.

Three rules the grading prompt states are now also code, applied after every grade (`finn/ledger.py`, `recheck`; `pipeline/recheck_ledgers.py` over the committed ledgers), so a model's grade can't break them: a growth or margin target whose period hasn't ended is not due, whatever one quarter shows; a promise past its date with nothing said since is past due, unless a later call said it again; a grade resting on a figure the results don't report is unmeasured. A check moves a grade only to not due or unclear, never to kept. `run_recheck.py` tests each rule on made-up rows, then checks that a second pass over the 22 committed ledgers moves nothing and that none counts a growth or margin target kept before its period ends (last run in `recheck_result.txt`).

## Security and privacy: `run_security.py`

No model calls and no network: every HTTP request goes to a stub that records it and refuses it, and the guard's resolver and connection are swapped for fakes, so "nothing was fetched" is checked, not assumed. Last run: 108/108 (`security_result.txt`).

| Group | What it checks |
|---|---|
| imports | `finn/network` imports no model, HTTP or research module; the model modules don't import the network |
| filed fields | no profile file and no code that reads one; through the API, no earlier job or school of a filing person the investor doesn't know shows a year |
| identity answers | `op: views` with no answers is `network.json` byte for byte; an answer is applied only to a pair the engine asked about (500 made-up keys build nothing; a real one past the 200th is dropped), rebuilt once per answer set, and neither written nor logged |
| key | sent as a header, never in a URL; an unreachable model is a fixed code; no part of the key in the error |
| no key | sources answers `live: false`; call and grade answer `no_key`; nothing fetched |
| errors, limits, logs | fixed codes only; 400 for bad JSON, an unknown op or a non-object; 413 over the size caps; 200 identity answers and 300-character questions at most; 429 after 6 grades from one IP in ten minutes; a failed question's text never reaches the log |
| guard | loopback, private, link-local and IPv6 loopback are refused; a public name is reached by its checked IP; a name that rebinds to a private address is refused |
| pdf | a redirect to 127.0.0.1 or with a user name, a fourth redirect, `file:`, `ftp:` and odd ports are refused; a stream over the cap and a zip bomb stop; an honest PDF downloads |
| grade | an unlisted URL and another company's call are dropped; periods, name and numbers are the server's; 40 promises a call and 600 characters a field; 7 calls refused; NSE retried once; an empty list answers `unavailable` |
| search, headers | `robots.txt` and `noindex` on `/data/`; the content, referrer and permissions policies |
| terms, planes | private text needs paid terms and is never cached; answering tools take no URL, refuse private tools and keep nothing of a question |
| inject | a classify index read twice is left unread, since one filing's text may pose as another's |
| gate | in a pull request, a hand-edited `gate.json` passes no changed validated step, a step marked validated by hand fails, an unvalidated step changed without `--accept`'s record of who and why fails, a lowered floor fails, and an eval that tries to fetch a page missing from the fixture fails rather than skips |

What it can't show: the per-IP limit is per serverless instance, so it slows one client and doesn't stop many. That needs the firewall rule in `docs/NEEDS_FROM_USER.md`.

## Ingestion, the ledger of ADR 2: `run_ingest.py`

Checks on real archive rows from 5 Dec 2025 (checked in as `fixtures/`), with every fetch and model call stubbed (`finn/ingest/`, ADR 2):
1. two polls store each filing once;
2. a cosmetic change makes no revision, and a real one makes revision 2, which re-runs;
3. two failures then a success end done, five end dead, and `not_pdf` is dead at once, after one attempt counted at claim;
4. an expired lease is reclaimed and done once, and the late worker writes nothing;
5. a partial batch leaves the missing filings pending;
6. with no model key every model step parks or blocks, nothing is fetched, and a key unparks them;
7. a new read prompt re-runs only what read touches;
8. results in any order give one fact per (symbol, quarter);
9. the archive holds the snapshot's 286 filings;
10. explain parked keeps the rule tier, as `triage.enrich` does;
11. a fallback marks the run degraded;
12. a replay sizes a filing against the four quarters before its own, not screener's latest, and a miss isn't stored;
13. a degraded read is re-asked an hour later, at most twice, and an answer that differs re-runs tier;
14. a quiet drain reads no event, even after a re-ask answered the same, and a new step version plans every event again;
15. a run whose workers die five times ends dead, each death counted;
16. two drains at once read each filing once, and a racing planner can't reset a leased run;
17. a re-ask that fails keeps the degraded answer and its tier;
18. a re-ask that answers the same re-runs nothing downstream;
19. a claim takes one batch, 20 to read and 4 otherwise, leased for 30 minutes;
20. a filing on 1 Oct is for the quarter to 30 Sep;
21. a results filing whose XBRL lags waits a quarter of its age, 15 minutes to 6 hours, before NSE is read again;
22. sizing reads the four earlier quarters as their own filings gave them; one filed after the day falls back to screener's restated table, which isn't stored;
23. a step parked for terms waits through a drain with a key alone, and runs once the terms are paid;
24. a run is worked only on the inputs it was planned for: a tier claimed while its read is re-asked waits, then carries the reading;
25. one filing whose reply can never be read ends dead alone, the 19 beside it are read, and a model that is down is asked once;
26. a filing revised while its read is parked sends only its newest revision to the model;
27. a filing sized after a later one of the same quarter doesn't read a result made public between them;
28. a model that garbles every reply costs 3 calls for 20 filings, not 39, and each filing counts one try;
29. a read reply item off the schema (no line, a tier of "URGENT", a made-up category) is unread, and the drain runs on;
30. no halving call starts after the lease's last safe moment, and no filing counts more than one try a claim;
31. a filing is sized the same in any drain order: with results capped, size waits for the earlier quarters' results the ledger holds;
32. three polls at once store each filing once, and none fails.

Each of checks 12 to 32 fails when the fix it guards is undone in the code. Check 16 runs two drains at once, on every gate run. Check 9 needs the 19 MB archive and prints skip without it. Last run: 32/32 (`ingest_result.txt`). A live whole-market day, with no model key: `ingest_day.txt` (`python3 pipeline/ingest.py day 2026-11-12`).

## Price reaction: `run_reaction.py`, and the text model: `run_c2.py`

A year of every NSE filing and price (`docs/PRICE_REACTION.md`). The company-day table is `reaction_days.csv.gz`, rebuilt by `pipeline/build_reaction.py` from the archive (`pipeline/archive.py`). The Benjamini–Hochberg family was fixed from counts alone and committed before any rate was computed (`ba7c30e`). Results: `reaction_result.txt` and `c2_result.txt`.

## Answering: `run_answer.py`

The checked workflow (`finn/answer/`, ADR 3) on 26 questions written before search existed (`answer_questions.json`, authorship stated). Offline, with the model stubbed, it covers:
- guardrails: unknown tool, URL argument, bad period or page, private tool, result cap;
- doctored items, with controls that must pass: another page, a changed number, swapped words, a wrong direction, an unknown metric, one bad item among good ones, a stitched quote, a cut inside a word or number, a dropped sign (a minus, a Unicode minus or an accounting bracket);
- whole sentences: a quote that leaves out "not", "crore" or "bps" is shown with them, since the screen shows the sentences it sits in;
- the meter: an answered call priced at its model's rate, a failed call keeping what it paid, a model with no price an error, and ADR 3's keep rule passing at 2.9× and failing at 3.1×;
- recall at 5, an end-to-end run, and tokens per question.

Last run: 68/68 (`answer_result.txt`), and recall at 5 is 17/20. `--live` needs a model key; a free one is enough. It counts an answer as grounded only if its first three items hold the labelled answer, numbers and units in order, and reports being on the labelled page apart. The questions and labels were written by the coding agent; the gate validates nothing on them until a person signs them off. `--live --agent` adds two runs with the agent on, and prints the keep rule.

## The agent: `run_agent.py`

Checks on the agent's bounds (`finn/answer/agent.py`), each with a scripted planner, so what is measured is the code around a model:
- grounding: a quote must be found on a page the agent read; a doctored one, and one whose page isn't a number, are rejected;
- limits: a looping planner stops at 6 steps with its repeats not run; 25 calls asked at once run 10; a step that wouldn't fit the token budget isn't sent; the API's own token count is used, priced at the planner's rate;
- the meter: in `llm.generate`, with HTTP stubbed, a cut-off reply's retry and the reply itself are both counted and priced, and a retry that could pass the budget isn't sent;
- refusals: a private tool, a URL, an unknown tool and a bad period go back as codes, and it recovers;
- a lead into another company's calls, headed with that company; a number's sentence written by code;
- no model key, or a planner that can't be reached, is unavailable, never "Not in the calls I read", and so is the answer the investor sees; a fallback planner is degraded;
- off unless `FINN_AGENT=1`; the trace holds nothing of the question.

Each bound was broken on purpose and its check failed. Last run: 27/27 (`agent_result.txt`). Whether a real planner helps is the keep rule, which needs a model key.

## The gate: `gate.py`

It runs every offline eval against floors in `gate.json`, and checks a fingerprint of every model step's prompt template, schema, model and fallback chain (ADR 4). A skip prints its reason and never counts as a pass. The evals read page text from `fixtures/pages.json.gz` (0.5 MB, rebuilt by `fixtures/make_pages.py`), so they run where NSE is blocked, and an eval that tries to fetch a page fails.
- `--live` runs classify twice and the 26 questions twice, fresh, against floors fixed before any live run, and can validate those two steps. People, explain and the agent have no automatic validator yet.
- `--base REF`, for a pull request: what is validated, and the floors, come from REF's `gate.json`, not the tree's. A floor may rise, never fall; a changed validated step passes only by a live run in the same job.
- `--accept STEP --why "…"` records a changed unvalidated step with who accepted it, the day and why, and refuses a validated one. `--seed` rebuilds the fingerprints.

CI is written to run `claims.py` and the gate on every pull request (with `--base`) and `--live` nightly (`.github/workflows/gate.yml`). It hasn't run on GitHub yet: the public branch is one commit, with no pull request behind it.

`run_quotes.py` samples a pinned list (`quotes_sample.json`, the promise ledgers at the commit that recorded 74/80). Sampling live ledgers had drifted to 68/81.
