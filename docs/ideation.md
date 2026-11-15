# Ideation

## The slop list (what most entrants will ship)
1. Chat box over a company ("Ask FINN anything").
2. Dashboard of cards: price, P/E, news, sentiment.
3. A feed of every filing with an AI summary under each.
4. Importance score 1-10 on every filing.
5. Sentiment gauge (bullish/bearish needle).
6. Daily "AI morning brief" paragraph.
7. Category chips over a feed (Results, M&A, Dividend...).
8. Research page with eight generated tabs, one per menu item in the brief.
9. RAG chatbot over the annual report.
10. Voice assistant that reads the digest aloud.
11. WhatsApp/Telegram bot that forwards summaries.
12. Swipe-to-triage filings (Tinder for news).
13. Portfolio heatmap treemap.
14. Bull/bear debate between two AI personas.
15. "Copilot" side panel with suggested questions.
16. Stock "health score" donut.
17. Candlestick charts with AI annotations.
18. Notification centre with unread badges for everything.
19. Kanban of filings (to read / read / archived).
20. Knowledge graph of companies, people and peers.
21. AI-generated price targets or buy/sell calls.
22. Earnings calendar with countdowns.
23. Word clouds of concall transcripts.
24. Gamified streaks for reading your digest.
25. "Explain like I'm five" toggles on every number.

## Candidates (method → user moment → mechanism)
1. **Promise ledger** (analogy: a credit bureau, applied to management). Moment: results land for a holding. Mechanism: extract dated, measurable promises from the last four concalls; when results arrive, mark each kept, missed or pending; when a promise stops being mentioned, mark it "went quiet". The digest ranks filings by whether they touch a live promise.
2. **Silent by default** (inversion). Moment: 9am, nothing material happened. Mechanism: home screen is one line, "Nothing needs you", with routine filings folded into a count. Only crosses-threshold items break the silence.
3. **Concall diff** (analogy: code review). Moment: new transcript filed. Mechanism: compare topics and claims with last quarter's transcript and show what was added, dropped, and softened.
4. **Thesis tripwires** (changing who writes the rules). Moment: investor buys a stock. Mechanism: write one-line thesis and kill criteria; FINN watches filings and EOD data for them.
5. **Broadsheet edition** (analogy: a newspaper). Moment: 7am. Mechanism: one typeset page per day, front page = the one thing that matters.
6. **Management CIBIL score** (analogy: retail credit). Same mechanism as 1, presented as a credit report per CEO.
7. **Promoter actions vs promoter words** (narrative vs behaviour). Moment: promoter pledge rises after a confident call. Mechanism: line up pledge/insider filings against tone and claims in transcripts.
8. **Read-across** (changing who it serves first: the peer). Moment: a peer reports. Mechanism: map guidance and commentary from one company onto portfolio peers in the same segment.
9. **Ten-second close** (constraint: 10 seconds a day). Moment: 3:45pm. Mechanism: one card per day, the single biggest change across the book.
10. **Hearing room** (analogy: court). Moment: before a concall. Mechanism: FINN prepares the three questions management must answer, based on missed promises.
11. **Concall prep sheet** (changing when it acts: before the event). Moment: night before a call. Mechanism: last quarter's promises plus open questions, one page.
12. **Weather map of the book** (analogy: forecasting). Mechanism: each holding as a pressure system. Pretty, empty.
13. **Annual report time machine**. Mechanism: compare the chairman's letter across five years for drift.
14. **Auditor's red pen**. Mechanism: scan AR notes for qualifications, contingent liabilities, RPT growth.
15. **Voice memo in, ledger out**. Mechanism: the analyst dictates after a call; FINN files it against promises.
16. **Filings as mail** (analogy: email triage). Mechanism: inbox zero for filings.
17. **Portfolio stand-up** (analogy: engineering stand-up). Mechanism: each company "reports" yesterday/today/blockers.
18. **Unusual-move explainer**. Mechanism: volume spike → find the filing that explains it, or flag "no filing explains this".
19. **Guidance calendar**. Mechanism: every promise has a due date; show what falls due this quarter.
20. **Margin of safety tracker**. Mechanism: price vs a user-set fair value. Valuation call, outside brief.
21. **Capex follow-through**. Mechanism: track announced capex from approval to commissioning across filings.
22. **Management turnover radar**. Mechanism: KMP churn rates over two years.
23. **One-question research** (constraint: one question only). Mechanism: pull mode answers only "did they deliver?".
24. **Scorecard for the investor** (inversion: judge the user). Mechanism: track how the investor's own calls aged.
25. **Ledger close at Diwali** (analogy: bahi-khata chopda pujan, when traders open new books). Mechanism: an annual reset of the promise book.

## Killed
- Feature, not product: 3, 9, 14, 18, 19, 21, 22 (kept as parts of a bigger idea where they fit).
- Mostly summarising or decoration: 5, 12, 16, 17, 25.
- Outside the brief or untestable in four days: 8 (needs segment mapping across companies), 13 (five annual reports per company), 15, 20, 24.
- Slop-adjacent: 6 (gimmick framing of 1), 16 (mail clone).

## Prosecuted
**A. Promise ledger (1 + 2 + 18 + 19).**
Closest thing: guidance trackers in US terminals (AlphaSense, Koyfin-style estimate tables) track numeric guidance from sell-side models, not from the company's own words. Indian filing apps (MarketPing, Stox AI, Alpha Tribe) classify and summarise filings and alert on WhatsApp; none tie a filing back to what management promised. Fatal flaw risk: promise extraction is noisy, and many promises are vague ("strong growth"). Answer: only keep promises with a metric and a horizon; show the vague ones as "soft talk" counted but not graded. Pre-mortem: demo flops if transcripts can't be fetched for the ticker the evaluator types. Answer: show which documents were found, degrade to financial snapshot only, and say so.

**B. Concall diff (3).** Strong narrative signal, but needs two transcripts per company per quarter and is hard to show on a phone. Folds into A as the "went quiet" status.

**C. Thesis tripwires (4).** Good, but depends on the user writing a thesis on day one. Empty state is the whole product. Folds into A as configurable thresholds.

**D. Hearing room (10).** Lovely moment, but it only exists the night before a call. Becomes a section of the A company page: "Ask them on the next call".

**E. Silent by default (2).** Not a product by itself. It is how A's push side should behave.

## Scored against the brief
| | Creativity | Product sense | Judgment (filtering) | Architecture | Narrative vs numbers |
|---|---|---|---|---|---|
| A Promise ledger | high | high | high | high | it is the product |
| B Concall diff | high | mid | mid | mid | partial |
| C Tripwires | mid | high | high | low | low |
| D Hearing room | high | mid | low | mid | partial |

**Chosen: A, the promise ledger**, with E's silence, C's thresholds, B's "went quiet" and D's questions folded in. Runner-up: B, which lost because it shows change in words without saying whether the numbers followed.

## The insight
A long-term investor doesn't need to know everything that happened today. They need to know whether management is still doing what it said it would, and every filing is either evidence for that or noise.

## Fresh critic on the chosen idea (sub-agent that saw only the concept)
Fatal flaw it named: promise extraction on messy transcripts will either invent promises or come back nearly empty. Pre-mortem: a judge types a ticker and gets two trivial promises or a misattributed page; the quiet digest reads as "nothing works"; XBRL quirks give a wrong PAT.

What I changed because of it:
- Every promise and every piece of evidence carries a verbatim quote. Code checks that the quote exists on the cited page of the PDF. If it doesn't, the item is dropped. Citations are verified, not trusted.
- Only promises with a metric or a concrete deliverable and a time frame are graded. Everything else counts as "soft talk", shown as a number, never as a claim.
- If nothing qualifies, the ledger says so in one line.
- Results numbers come from the exchange's XBRL, not a model, with the basis (consolidated or standalone) shown and the filing linked. An eval script checks them against hand-read values.
- Quiet is a state, not the default look: the digest always leads with what crossed a line in the chosen window, and folds the rest into counts you can open.
