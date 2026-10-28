**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Hello,

Here is my submission for the FINN build challenge.

- App (open on a phone): https://finn-ledger.vercel.app
- Code: https://github.com/vedant-22/finn
- AI build history: attached (Claude Code session export)

**What I built**

FINN keeps management to its word. It reads a company's last five earnings calls, writes down every promise that had a number and a date, and checks each one against what the company later reported. Each promise ends up kept, partly kept, missed, gone quiet or not due yet, with the quote and the page it came from.

The push side is built around the same idea. Across an 18-stock portfolio, a results filing shows revenue, EBITDA, PBT and PAT against last quarter and a year ago, and then the promises that quarter settles. A management change shows who is coming in and where they worked before, from the profile the company files with the exchange. Price and volume alerts use lines you set, and say whether any filing explains the move. At most five things reach the screen at once; everything else is folded. In the 30 days to 28 October the portfolio filed 286 times; 43 of those could interrupt you.

Pull works on any NSE symbol. The portfolio and four other names are prebuilt so they open instantly; any other ticker is read live in about a minute.

**Key decisions and trade-offs**

1. I made the promise ledger the spine of the product instead of one research tab among eight. Your brief says promised versus delivered is what you value most, and I agree it's the difference between summarising management and judging them.
2. Every quote the model returns is checked by code against its page in the PDF. A changed number, an added "not", or two sentences stitched together are caught and dropped. I'd rather lose a real promise than show one management never made.
3. Results numbers come from NSE's XBRL, not from a model reading a PDF. They agree with screener's figures within 1% on 62 of 70 numbers; the rest are differences in definition, listed in the evals.
4. Only promises with a number or a concrete deliverable and a date get graded. "We remain confident" is counted, not judged.
5. Size decides loudness. A tax demand or a deal under 0.5% of a year's revenue becomes a one-line note.
6. Cheap model for reading, stronger model for judging. Flash-lite does the bulk work; flash does one grading call per company. A full company costs about $0.09 at list prices, and I've paid nothing, because it all fits in Gemini's free tier.

**What I left out on purpose**

Real lock-screen notifications, a live feed (push data is a snapshot built after market close and labelled as such), annual reports (the ledger reads transcripts and filed numbers), BSE-only companies, and accounts. I checked only 20 grades by hand (18 hold), which is too few to quote an accuracy.

**Where I'd take it next**

- A bigger grade eval, and the two fixes it points to: stay "not due yet" until the deadline passes, and drop past actions at extraction.
- Annual reports, read in chunks: MD&A, related-party transactions, contingent liabilities, auditor's remarks. These are where the numbers and the story part ways.
- A morning push on the phone, sent only when something crosses a line.
- Repeat promises across companies in a sector, so a claim of "industry-wide demand" can be checked against what peers said.

Thank you for reading.

Vedant Tiwari
IIT Kanpur · vedant22@iitk.ac.in
