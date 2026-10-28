# Decisions

Each entry: what I chose, what I passed on, and why.

## Product

**The organising idea is a promise ledger.** FINN keeps a record of what management said it would do on its earnings calls and marks each promise kept, partly kept, missed, gone quiet or not due yet. Push and pull both hang off it: a results filing is shown against the promises it settles, and the research page is the ledger first and the numbers second.
Passed on: a feed with summaries (what MarketPing, Stox AI and Alpha Tribe already do), a chat box, a dashboard. The brief says the thing ENAM values most is "what was promised vs. what was actually delivered", so I made that the spine instead of one tab out of eight. Full ideation in `docs/ideation.md`.

**Push is mostly folding.** Of 282 filings across 18 holdings in 30 days, 45 can interrupt, 110 get one line and 127 are folded into a count. The tier policy is written at the top of `finn/classify.py` and `finn/triage.py` so it can be argued with.

**Size things against the company.** Any filing with a rupee amount in it (a tax demand, a deal, a debt raise) is read for that amount and divided by the company's trailing revenue. Under 0.5% it becomes a one-line note. A ₹27 cr GST notice at Blue Dart is noise; ₹10,000 cr of NCDs at Sun Pharma is not.

**Management changes are ranked by who moves.** CEO, MD, CFO and executive directors interrupt. Business heads and independent directors get a line. Company secretaries are folded.

**Bios come from the filing, not LinkedIn.** The brief suggests LinkedIn as an example. SEBI's disclosure rules make companies file a "brief profile" of every incoming director and KMP, so the company's own filing already has the background, and scraping LinkedIn breaks its terms. Trade-off: the profile is only as good as what the company writes.

**Unusual moves say whether a filing explains them.** A 5× volume day after results is expected; a 5× volume day with no filing is the one to look at. Thresholds (volume multiple, price move, which filing types can interrupt) are set by the investor in "Your lines" and change Today immediately.

**Promises need a number or a concrete deliverable and a time frame to be graded.** Everything else ("we remain confident of strong growth") is counted as talk and shown as a number, never graded. This came from the fresh critic's pre-mortem: a ledger full of vague items would be either empty or wrong.

**The book is sorted weakest word first.** It is the view a PM would want before a review: which management teams are drifting from what they said. The sort uses the kept share with one kept and one not-kept added, so a company with one quiet promise does not outrank one with six.

## Grounding and trust

**Every quote is checked by code against its page in the PDF.** The model returns a quote and a page; `finn/sources/pdf.py:verify_quote` looks for it. Small copying slips pass. A changed number, an added "not", or two sentences stitched from different pages fail, and the promise is dropped. Evidence quotes used in grading get the same check, and a grade whose evidence fails is downgraded to "can't tell". Results in `evals/quotes_result.txt`.

**Results numbers come from the exchange's XBRL, not from a model.** NSE publishes every results filing as XBRL. FINN parses Revenue, PBT and PAT from it and works out EBITDA as PBT before exceptional items + finance cost + depreciation − other income. A model reading a PDF table can misread a column, and it costs money for no gain. Banks get interest earned and pre-provision profit; NBFCs get net interest income, because EBITDA means nothing for a lender.

**Pull uses primary sources only, enforced by what goes into the prompt.** The model sees transcript text (from NSE or the company's own copy linked by screener.in) and financial tables screener compiles from filed results. Screener's own prose and "AI summary" are never fetched into a prompt. Every prompt says to use only the material given.

**The API never fetches a URL the client sends.** `/api/call` takes a symbol and a call period and looks up the document itself. Otherwise the endpoint could be pointed at anything.

## Data

- **Announcements:** NSE's corporate-announcements API, one call per day, cached. NSE's subject line settles about 85% of classifications for free.
- **EOD prices:** NSE's daily bhavcopy (one official file per day for every stock) instead of yfinance. One request covers the whole book, and Yahoo was rate-limiting from this machine.
- **Transcripts:** NSE filings first; screener's links as the fallback because some companies (L&T, Maruti, Astral) file only a cover letter on NSE that points to their website.
- **Snapshot, not live push.** The push data is rebuilt by `pipeline/build_push.py` after market close and served as a static file, labelled with the time it was built. A live feed would need a scheduler that NSE doesn't block; I didn't want the demo to depend on that.

## Models and cost

- **Routing:** `gemini-3.5-flash-lite` for bulk work (classifying vague filings, reading management-change letters, sizing deals, extracting promises from each transcript). `gemini-3.5-flash` only for grading promises against delivery, which is the one step that needs reasoning across documents.
- **Free tier reality:** the free tier allows 20 `gemini-3.5-flash` requests a day. Pro models have zero free quota. When flash is out, grading falls back to flash-lite automatically, and the usage line on each company page shows which model did the grading. If billing is turned on, set `FINN_SMART_MODEL` to a stronger model; only one call per company uses it.
- **Caching:** every model call is cached on disk by prompt hash; PDFs and NSE responses are cached too. Rebuilding the whole snapshot after a code change costs almost nothing.
- **Per company:** about 6 model calls and 60–100k tokens, roughly $0.05–0.15 if billed at list prices.

## Design

Working-paper look: pale green paper and blue-black ink, with auditor's tick marks drawn in coloured pencil. One typeface (Archivo) using its width axis instead of a second family. Details in `DESIGN.md`. I passed on dark mode and a chat input. Both pull toward a trading terminal, which is the wrong world for a long-only fund.

## Deviations from my working guidelines

- **Ideation without the `novel-idea-hunter` skill.** I did the slop list and the 25 candidates by hand, then used one fresh sub-agent critic on the winner. The skill is a long multi-phase research workflow; the brief already pins the domain and the users, so I spent the budget on the build.
- **Eval labels revised twice, openly.** Two classification labels were changed after reading the full letters (see `evals/README.md`). Both changes made the classifier look better, so I wrote down why.
