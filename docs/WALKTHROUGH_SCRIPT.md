# Walkthrough script

About 3:15, seven beats. Spoken lines are short: say why it matters, don't read the screen. Every `On screen:` string is checked against the app by `web/test/e2e/walkthrough.py`, which does the same taps.

## Before recording

- iPhone, or Chrome devtools at 390×844 with the device frame off. Light mode, notifications off.
- Run `python3 web/test/e2e/walkthrough.py` first. If a string fails, the app has changed and this script is stale. It also says whether the link has a model key, which decides the optional beat.
- Open https://finn-network.vercel.app once so fonts and data are cached, then clear the site's data (Settings → Safari → Advanced → Website Data on an iPhone, or devtools → Application → Clear site data) and open it again. It should open on "2 of your companies need a look today": the replay of the 28 Oct close.
- For the optional beat, open `#/c/ASTRAL` once off camera so the server has its transcripts, then clear site data again.
- Speak after each tap, not over it.

## Beats

### 1. Today (0:00–0:25)
Open the app. Hold on the first card.

On screen: `Sample data, as of 28 Oct` · `2 of your companies need a look today` · `Syngene and Larsen & Toubro. FINN checked 9 announcements and price moves, up to 9:21 pm on 28 Oct. One more is about people you know.` · `+12.2%` · `Share price jumped after its results` · `profit was ₹32 crore after a loss the quarter before, down 52% from a year earlier.` · `Past both your alert levels: a 4% move in a day, and 2 times the usual trading. It traded 43.5 times its usual amount.` · `Ask someone you know: Dr. Leena Joshi, Director, Discovery Chemistry there, 2011–2019.` · `A new CFO at Home First Finance and a new MD & CEO at HDFC Bank: one call to Meera Krishnan, CFO at Aavas Financiers, has a question for each.`

> "This is FINN. It opens on what needs me today, and then it ends. This is a replay of the 28 Oct close, and the pill up top says the data is a sample."
> "Syngene jumped on its results, and its CFO resigned. FINN says why it reached me: it passed alert levels I set. And it names someone I know who worked there."
> "The last card passed none of my alert levels, so it isn't in the count. It's about people I know: one call to Meera answers a question at Home First and one at HDFC Bank."

### 2. The full view (0:25–1:10)
Tap Read more on Syngene's card. Scroll slowly to Against what they promised.

On screen: `It traded 43.5 times its usual amount.` · `Resigns as Chief Financial Officer. No successor named.` · `From the filing, page 1` · `consolidated, ₹ crore` · `Who to ask` · `Worked there` · `Not the Deepak Jain you know.` · `Sample contacts: the people you know here are made up. Names and jobs from company filings are real.` · `Against what they promised` · `Syngene has kept 2 of 4 promises that came due.`

> "Read more opens the whole event. The filing, quoted, with its page. The results against last quarter and last year, from the exchange's own data, read by code, not a model."
> "Then who to ask. Leena worked there and knows the labs. I also know a Deepak Jain, and FINN says it isn't the same person. A name alone never counts as a match."
> "The people I know here are made up, and it says so. The people from filings are real."
> "Last, their word: what they promised on past calls, and whether they did it."

### 3. Your alert levels, and your data (1:10–1:35)
Tap Back. Scroll to the end of Today and tap Change alert levels. Tap the minus on Price move in a day twice. Then Reset to defaults, and tap Your data at the foot. Scroll it once, then Done.

On screen: `At these levels, 2 things get through in this window.` · `At these levels, 4 things get through in this window.` · `Reset to defaults` · `What stays on this phone` · `What an AI model reads` · `Only public filings, read once for everyone: never your holdings, your people, your questions or your answers.` · `FINN reads a filing as text to check, never as orders to follow.` · `Clear this phone`

> "What reaches me is my call. Lower the price level and more gets through."
> "And it tells me what it keeps. My alert levels and answers stay on this phone, and no model ever reads my holdings or my people. A filing is something to read, never an instruction."

### 4. The ledger (1:35–2:05)
Tap Holdings, then Larsen & Toubro. Scroll to Promise by promise and tap the first one.

On screen: `Larsen & Toubro. 1 of 2 promises kept.` · `Promise by promise` · `Group revenue growth 15% by FY26.` · `Missed` · `Done` · `“Our guidance for FY26 remains unchanged.` · `P. Ramakrishnan, on the Aug ’25 call, page 9` · `FY26 group revenue grew 11.8% to ₹2,85,874 crore against the 15% growth target.`

> "This is the ledger: every promise with a number and a date, from their calls, held against what they reported."
> "Here they promised growth and missed. The quote is their words, and the link opens the call on that page. A model read the call, but code checks every quote against its page. If it isn't there, FINN doesn't show it."

### 4b. The annual report (2:05–2:25)
Tap Back, then UltraTech Cement. Open The annual report, then Read the paragraph.

On screen: `The auditor drew attention to note 37(b)` · `Note 37(b) of the consolidated accounts: Competition Commission of India (CCI).` · `Neither ‘CCI’ nor ‘Competition Commission’ appears in the 5 calls FINN read (Oct 2025 to Oct 2026).` · `Consolidated report, page 253` · `Neither term is in the transcripts of the last five calls. What would settle it, and by when?`

> "The annual report, read by rules, not a model. UltraTech's auditor stresses penalties from the Competition Commission, with no provision made."
> "And on its calls, management hasn't named it once. That's the question for the next one, with the auditor's paragraph and its page."

### 5. Before a meeting (2:25–2:50)
Tap Look up, then "Brief me before I meet Home First" under Ask about people you know. Scroll slowly down the path.

On screen: `Meeting Home First Finance` · `Who was there` · `The path is the filing's, and it gives no years. The people are yours.` · `Where did risk and finance pull against each other at Home First Finance?` · `Were you at IDFC Limited with Rinkoo Somani, and what did treasury need from the CFO?` · `No housing finance employer in the filing` · `What catches a new CFO out in housing finance?` · `What was the interim brief at IDFC Limited?` · `Copy the call sheet`

> "I'm meeting Home First, and its new CFO joined a day ago. This is Rinkoo Somani's path, as the company filed it."
> "At each stop, someone I know, and the one question that person can answer. And the filing lists no housing finance job, so the last call is to a CFO who has one."
> "No model wrote this. It's rules on the filing and my own contacts."

### Optional: any company (only if the link has a key, about a quarter of a minute)
Tap Look up, type ASTRAL, open it.

On screen: `Checking promises against the numbers`

> "Any NSE company I don't hold is read live, from its own calls."

### 6. The end (2:50–3:15)
Tap Today and scroll to the end.

On screen: `That’s everything from the last 24 hours.` · `Questions worth asking` · `Why did the CFO, Deepak Jain, leave, and who covers the role until a successor joins?` · `Ask first: Dr. Leena Joshi, Director, Discovery Chemistry there, 2011–2019. Where did R&D and finance pull against each other at Syngene?` · `Which costs are moving most in engineering & construction, as Tata Projects sees it?` · `Copy the questions`

> "And then it ends. The questions for their next calls, and who to ask first: for the CFO who left, someone who worked there; for L&T's margin, someone at a competitor today, each asked about their own seat."
> "That's my day with FINN."

*(a pause, then stop)*
