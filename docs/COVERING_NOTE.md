**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Hello,

Here is my submission for the FINN build challenge.

- App (open on a phone): https://finn-ledger.vercel.app
- Code: https://github.com/vedant-22/finn
- AI build history: attached (Claude Code session export)

**The point of view**

FINN is a brief you finish. Each morning it hands you the few things that changed in your book, holds each one against what management promised, and lets you go.

Before building the screens I walked an investor's day through seven ways of using FINN: chat, voice, a dashboard, a copilot on every screen, alerts as phone notifications, a book-wide scoreboard of management's word, and a brief you finish. The brief won because it ends. A feed never tells you that you've seen everything, so you keep scrolling. Knowing you're done is what saves the time. Chat lost because a blank box hands the filtering back to you, and a dashboard is aggregation, which you say isn't the scarce skill. The two runners-up live inside the brief: alerts open it, and Ask sits on every item.

**What I built**

You open FINN and it says "2 to read", names the two companies, and adds up the rest ("4 more worth a line; 3 routine filings set aside"). Under that is anything that crossed a line you set: a ±% day, a volume multiple, a kind of filing. Each alert shows the line that set it off, and tapping that line lets you move it. "Read the brief" opens one item per screen. You mark each one done or keep it for later, and the brief ends on "You're up to date" with what it set aside. Tomorrow picks up where you left off.

Every item is held against management's word. Results show revenue, EBITDA, PBT and PAT against last quarter and a year ago, then the promise that quarter settles: what they said, on which call and page, what was delivered, and the verdict. A management change shows who is coming in and where they worked before, from the profile the company files with the exchange. A move says whether any filing explains it. In the 30 days to 28 October the portfolio filed 286 times; 43 of those could interrupt you.

Pull lives inside the same flow. You can ask about any item where you are ("Did L&T deliver on margins?"), or open Ask and type or say a question about a company or the whole book. Promise questions are answered from the ledgers FINN has already built, with no model call, so they still work when the model is out of quota. Any other NSE symbol is read live in about a minute: FINN reads the last five earnings calls, writes down every promise that had a number and a date, and marks each one kept, partly kept, missed, gone quiet or not due yet, with the quote and its page.

**Key decisions and trade-offs**

1. I made the promise ledger the spine of the product instead of one research tab among eight. Your brief says promised versus delivered is what you value most, and I agree it's the difference between summarising management and judging them.
2. Every quote the model returns is checked by code against its page in the PDF. A changed number, an added "not", or two sentences stitched together are caught and dropped. I'd rather lose a real promise than show one management never made.
3. Results numbers come from NSE's XBRL, not from a model reading a PDF. They agree with screener's figures within 1% on 62 of 70 numbers; the rest are differences in definition, listed in the evals.
4. Only promises with a number or a concrete deliverable and a date get graded. "We remain confident" is counted, not judged.
5. Size decides loudness. A tax demand or a deal under 0.5% of a year's revenue becomes a one-line note.
6. Cheap model for reading, stronger model for judging. Flash-lite does the bulk work; flash does one grading call per company. A full company costs about $0.09 at list prices, and I've paid nothing, because it all fits in Gemini's free tier.
7. The design is flat white paper in ENAM's blue, with no boxes around anything that isn't a control. Titles, names and figures are in a book serif, management's quotes sit on a warm panel, and a verdict is one word in its colour. I compared it against two earlier versions of my own with a fresh critic who saw only screenshots, and it went live only once it beat both on cleanliness and on beauty.

**What I left out on purpose**

Background push (FINN raises a phone notification when you open it on a newer snapshot, but doesn't wake the phone on its own), a live feed (push data is a snapshot built after market close and labelled as such), annual reports (the ledger reads transcripts and filed numbers), BSE-only companies, and accounts. I checked only 20 grades by hand (17 hold), which is too few to quote an accuracy.

**Where I'd take it next**

- A bigger grade eval, and the two fixes it points to: stay "not due yet" until the deadline passes, and drop past actions at extraction.
- Annual reports, read in chunks: MD&A, related-party transactions, contingent liabilities, auditor's remarks. These are where the numbers and the story part ways.
- A real morning push, sent from a scheduled job only when something crosses one of your lines.
- Repeat promises across companies in a sector, so a claim of "industry-wide demand" can be checked against what peers said.

Thank you for reading.

Vedant Tiwari
IIT Kanpur · vedant22@iitk.ac.in
