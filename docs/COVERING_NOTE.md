**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Hello,

Here is my submission for the FINN build challenge.

- App (open on a phone): https://finn-ledger.vercel.app
- Code: https://github.com/vedant-22/finn
- AI build history: attached (Claude Code session export)

**What I built**

You open FINN and the first screen says "2 need you". Under it, one grey sentence names the two companies and how far the filings run ("to 9:21 pm, 28 Oct").

Each card is one event: the month's price line, what happened ("Q2 FY27 results and a new CFO"), one sentence, and the line it crossed ("Past your ±4% and 2× lines, 43.5× volume"). Read more grows the card into its full view. There you get the results table against last quarter and a year ago, the people who left or joined with their background, and the promises management made that bear on it.

The rest of the window waits below in two folds, Worth a look and Routine filings. The page ends on a blue band with one question for each company's next call. In the 30 days to 28 October your 18 holdings filed 286 times. 43 of those could have interrupted you.

Book shows management's record across your holdings, with the companies that broke the most promises first. Look up takes any NSE symbol or a plain question. If FINN hasn't read a company yet, it reads its last five earnings calls in about a minute and writes down every promise that had a number and a date, with the quote and its page.

**The point of view**

An investor should spend a few minutes with FINN and then be done. A feed never tells you that you've seen everything. FINN counts what needs you, shows you that, and puts the rest where you can find it. Of the seven ways of using it I tried on paper, chat lost first: an empty box hands the filtering back to you. Alerts and Ask survived inside the brief: your lines decide what interrupts you, and Ask sits on every item.

The second idea is that every event is held against management's word. Your brief says promised versus delivered is what you value most. I agree. It's the difference between summarising a company and judging it, so the promise ledger is the spine of the product.

**Design**

The look comes from my fourth version, the cleanest of them: white paper, warm panels for cards and quotes, and ENAM's blue for what you can tap. Inter sets every title and figure. A serif sets only the sentence under a title and management's own words. Motion is there only when it explains something. A card grows into its page, so you always know where you came from. A fold slides open while the rest of the page moves out of its way.

Each round, three critics who saw only screenshots scored the new build against that fourth version and against what was live. It went live today, after all three picked it as the one they'd open every morning.

**Key decisions and trade-offs**

- Every quote the model returns is checked by code against its page in the PDF. If a number changed or a "not" appeared, the quote is dropped. I'd rather lose a real promise than show a fake one.
- Results figures come from NSE's XBRL filings, so no model reads them off a PDF. They match screener's figures within 1% on 62 of 70 numbers.
- Only promises with a number or a concrete deliverable and a date get graded. "We remain confident" is counted and left alone.
- Gemini 3.5 flash-lite does the bulk reading. Flash makes one grading call per company. A full company costs about $0.09 at list prices. Reads are cached, and promise questions are answered from the stored ledger with no model call at all.

**What I left out on purpose**

Background push is out. FINN notices a newer snapshot when you open it, but it can't wake your phone. The data is a snapshot built after the market closes and labelled as one, so there's no live feed. I also skipped annual reports, BSE-only companies and accounts. I checked only 20 grades by hand (17 hold), which is too few to quote an accuracy.

**Where I'd take it next**

First, a bigger grade eval, and the two fixes it already points to: keep a promise "not due" until its deadline passes, and drop past actions when extracting. Then annual reports, starting with related-party transactions and contingent liabilities. That's where the numbers and the story tend to part ways. After that, a real morning push from a scheduled job, sent only when something crosses one of your lines.

**How I used AI**

I built FINN with Claude Code, and the full session history is attached. I set the specs and design rules it worked to, and I made the product calls. Inside the product, Gemini reads transcripts and grades promises. Code does the fetching and the arithmetic, and it checks every quote.

Thank you for reading.

Vedant Tiwari
IIT Kanpur · vedant22@iitk.ac.in
