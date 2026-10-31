# Brief trace

Quoted lines keep the brief's own punctuation and words. Every line in the two brief PDFs that asks for, suggests or values something, read line by line from `pdftotext -layout` on 31 Oct. "Where" names the screen and element the investor meets it in. Status is one of: done, done but weak, missing. Rows marked weak or missing on the frontend are stage 4 work (design/STAGE4_PLAN.md).

The "where" and status columns describe the live app (stage 4, promoted 31 Oct after it beat v4 and v5 with a blind critic). The last column says what stage 4 changed, and for rows that were weak or missing in v5, what was wrong then.

## Main brief

| # | Line | What FINN does | Where | Status | What stage 4 changed |
|---|---|---|---|---|---|
| 1 | "What we're evaluating: How you build, what you choose to build, and the creativity and judgment behind it" | Decisions log, covering note, build history | docs/DECISIONS.md, covering note | done | Point of view leads DECISIONS and the note |
| 2 | "We run lean — a small team makes high-conviction decisions and lives with the outcomes." | 18 holdings; the product ranks management by whether they kept their word | Book | done | INVESTOR.md designs from this person's day |
| 3 | "An investor today is drowning in information ... most of it doesn't matter." | Triage puts each filing in act, note or fold; routine paperwork folds | Brief: "2 to read" and the line under it | done | |
| 4 | "The scarce skill is not aggregating information. It's filtering it: surfacing the few things that actually matter and burying everything else, beautifully." | Act/note/fold tiers, stories merge related filings, routine collapsed into one line | Brief: alerts, "Worth a line", routine filings in a count; the reader | done | v5: Today still reads as a long list of everything in the window. The brief shows the few items one at a time and buries the rest behind one line |
| 5 | "Build something that becomes part of a daily investor's workflow — a product they reach for through the day" | A brief you finish; new since your last visit is marked; it ends on "You're up to date" | Brief: the reader and "You're up to date" | done | v5: nothing marks what's new since the last visit and nothing ends the session. A brief you finish, with "since you last looked" and a done state |
| 6 | "...that saves them time and shows them only what's important." | Tiers and stories; the done page counts what was read, kept and set aside | Reader: the done page; Brief: the line under the count | done | v5: time saved is never shown. The done state says what was cleared and what was skipped |
| 7 | "FINN ... a mobile-first financial investment agent." | Responsive web app, PWA manifest | Whole app | done | Native-feeling shell, safe areas, splash, all states |
| 8 | "Push — it proactively tells you what changed and why you should care." | Alerts at the top of the brief with the line that set each off; with permission, a system notification on opening a newer snapshot | Brief: "Crossed your lines"; a system notification if allowed | done | v5: no notification-style alert, nothing reaches out. Alerts presented as phone notifications, each showing the line that set it off |
| 9 | "Pull — you ask it to research or analyse something on demand." | Ask in place on every item, and as a tab; live research for any NSE symbol | Reader: Ask FINN on every item; Ask tab; Company | done | v5: pull is a separate tab, not part of the daily flow. Ask from any item in the brief; pull lives inside the same flow |
| 10 | "The frontend — the product, the interaction model, the design — is deliberately yours. That's where we most want to see how you think." | A brief you finish (docs/DECISIONS.md) | Whole app | done | v5: no stated interaction model. Stage 4's whole point: one-sentence point of view as the app's spine |
| 11 | "Portfolio: choose your own mock portfolio of 15–20 NSE/BSE-listed companies ... different sectors and sizes" | 18 holdings, 14 sectors, large to small | Book | done | |
| 12 | "Ad-hoc research: ... a handful of companies (say 3–5), which can be outside your portfolio" | DIXON, TITAN, PIDILITIND, POLYCAB ready | Ask: suggested questions and companies | done | Keep |
| 13 | "Build the engine to generalise ... works on any NSE ticker where the data is available. We may point it at a company you didn't pick." | Live research through api/sources, api/call, api/grade | Ask: any symbol, then "Read SYMBOL" | done | Ask box takes any ticker |
| 14 | "Three sources. Get them working; don't over-engineer them" | EOD prices, NSE filings, screener.in fundamentals and transcripts | Backend | done | Unchanged |
| 15 | "Price & volume (end-of-day) for your portfolio" | 40-plus sessions per holding in push.json | Brief: a month of closes under each alert; reader; Company header | done | Price line draws itself on the alert |
| 16 | "Corporate announcements / filings ... A classification of announcement types is provided ... use it, adapt it, or ignore it" | The 17 categories, renamed in plain words | Brief, Your lines | done | |
| 17 | "Company fundamentals — annual reports and concall transcripts ... on screener.in" | Transcripts and financials from screener.in | Company | done | |
| 18 | "Give us part of a real investor's daily workflow, built beautifully." | Brief, reader, Book, Company, Ask | Whole app | done | v5: v5 is less clean than v4. Beat v4 on cleanliness (STAGE4_PLAN) |
| 19 | "What you choose to build, and how, is the signal." | Decisions log | docs | done | |
| 20 | "Push is the app telling you what changed without being asked." | The brief opens on what crossed your lines | Brief: "Crossed your lines"; system notification | done but weak: no background push; the data is a snapshot built after the close, and a notification is raised when the app opens on a newer one | v5: nothing is pushed; the investor has to open the app and scan. Lock-screen style alerts at the top of the brief, Web Notifications if allowed |
| 21 | "A windowed digest. For a time window I choose — by default the last 24 hours, but let me pick the period" | 24 hours by default, or 3 days, Week, Month; the count rolls when it changes | Brief: the window under the count | done | v5: chips sit apart from the content. The window as a control on the brief itself, items settle in or out when it changes |
| 22 | "show me every corporate filing/announcement across my portfolio" | Every filing in the window is reachable | Brief: "Worth a line" and the routine count; reader: "The rest" | done | Every filing stays one tap away in "the rest" |
| 23 | "filtered and prioritised so I see what matters first and the routine stuff is collapsed or hidden" | Order: results, management, deals, legal, funds; routine folded | Brief: the reader, newest first | done | |
| 24 | "Triggered alerts. Tell me the moment something crosses a threshold" | Unusual moves and material filings against Your lines, as alert rows | Brief: "Crossed your lines" | done | v5: presented as cards, not alerts. Notification-style alerts, each naming the line it crossed |
| 25 | "a material announcement of a type I care about (results, M&A, management change, and so on)" | Your lines: which kinds of filing may interrupt | Your lines sheet, opened from an alert's line | done | Edit the line from the alert itself |
| 26 | "volume more than ~2× its recent average, or a price move beyond ±X% in a day" | 2× volume vs 20 sessions, ±4% default | Your lines sheet; the alert names the line it crossed | done | |
| 27 | "Make the threshold configurable: the point is that I decide what 'unusual' means and the app watches for it." | Steppers for volume and move, saved on the phone; the brief recounts behind the sheet | Your lines sheet, opened from an alert's line | done | v5: the sheet is reached from a menu, and the effect is not shown. Thresholds shown on each alert and adjustable there; the count of alerts updates live |
| 28 | "Management change → don't just say 'CFO resigned.' Pull a short background/bio of the incoming person" | People extracted from the filing: background, previous roles, education | Reader: management change, or "Also that day" under results | done | Keep, cleaner |
| 29 | "(e.g. from LinkedIn)" | Background from the company's own filing, not LinkedIn | Reader: Background, credited to the filing | done | |
| 30 | "Quarterly results → ... headline numbers — Revenue, EBITDA, PBT and PAT — this quarter vs. last quarter (QoQ) and vs. the same quarter a year ago (YoY)" | XBRL from NSE: four lines, QoQ and YoY; banks get their own lines | Reader: the results table | done | Figures roll to value |
| 31 | "For every other announcement type, decide what earns my attention: a one-line summary next to the filing, or just the filing surfaced at the right priority." | One line on notes, plain titles on folded paperwork | Brief: "Worth a line" | done | |
| 32 | "Pull is on-demand analysis of a company, grounded in its fundamentals (annual reports + concall transcripts)." | Ledger from transcripts, numbers from filed financials | Company | done | |
| 33 | "Treat them as a menu: pick what you build and how deep you go." | Chose narrative vs numbers as the core | Company | done | |
| 34 | "Business snapshot — what the company does, its segments, revenue mix." | Name, sector, size only | Company header | missing (by choice) | Left out: screener's standard tables have no segment split; noted in covering note |
| 35 | "Financial snapshot — current headline numbers (revenue, margins, PAT, key ratios)" | Last quarter, P/E, market cap | Company: "The numbers" fold | done | |
| 36 | "Trajectory — the multi-year direction" | Six years of revenue and PAT bars, CAGR | Company: "The numbers" | done | |
| 37 | "Balance sheet — debt, leverage, working-capital cycle, funding structure." | Debt to equity, borrowings, cash conversion cycle | Company: "The numbers" | done | |
| 38 | "Cash quality — cash-flow trend and cash conversion" | Cash conversion over five years, one-line read | Company: "The numbers" | done | |
| 39 | "Narrative vs. numbers — where management's story and the actual financials agree or diverge." | Promise ledger: quote, page, verdict, evidence | Company: "Their word" | done | Becomes the centre of company research and of Ask |
| 40 | "Guidance — what management has explicitly guided on headline numbers (growth, margins, capex)." | Open promises with a number and a date | Company: promises "Still running" | done | |
| 41 | "Bull vs. bear — a tight case each way." | Two or three lines each, from the filings | Company: For and Against | done | |
| 42 | "take the last four quarters and, against management's own headline guidance ... tell me what was promised vs. what was actually delivered." | Last four calls read; each promise graded kept, partly, missed, gone quiet, not due | Company: "Their word", Book | done | |
| 43 | "This is the difference between summarising management and analysing them — and it's the kind of thing we value most." | The word ranks the book; Ask answers book-wide questions | Book: weakest word first; Ask: "Who missed a promise?" | done | v5: only reachable as a list. A book-wide "who keeps their word" view in the daily flow; Ask answers in before-and-after form |
| 44 | "ground it in the primary sources ... No broker notes, no news ... don't lean on the model's own outside knowledge" | Prompts take only filing text; quotes checked against the page; "not found in the filings" | Company sources, every promise links its page | done | Ask answers keep page citations |
| 45 | "Push-side enrichment like a person's professional background is a different thing and completely fine." | Background from the filing | Reader: Background | done | |
| 46 | "How the investor interacts with all of this is entirely up to you, and we strongly encourage you to experiment." | Seven interaction models walked through the investor's day; a brief you finish chosen | App shell: Brief, Book, Ask | done | v5: a tabbed app, no experiment. Seven models explored and scored, one chosen (design/STAGE4_EXPLORE.md, DECISIONS) |
| 47 | "Chat, voice, a copilot, a dashboard, or something we haven't thought of — try more than the obvious." | Ask on every item and as a tab, typed or spoken; Listen reads the brief aloud; alerts as notifications | Reader: Ask FINN; Ask tab with a mic; Brief: Listen | done | v5: missing. Ask on every screen; voice read-back of the brief |
| 48 | "Everything mobile-first." | Designed at 390×844 | Whole app | done | Tested at 390 and 320 |
| 49 | "The best submissions will show a point of view about how an investor should interact with this, not just what data to show." | "FINN is a brief you finish." | docs/DECISIONS.md, covering note, the whole app | done | v5: missing. One sentence, top of DECISIONS and covering note, and the app built on it |
| 50 | "core, concise, beautifully presented, and interactive" | Flat paper, one idea per block (DESIGN.md) | Whole app | done | v5: v4 read cleaner. STAGE4_PLAN's cleanliness rules |
| 51 | "It should save the investor time and show them what's important" | Tiers; a brief that ends | Brief and the done page | done | v5: weak. Finishable brief with time saved |
| 52 | "feel like a product someone thought hard about, not a model filling a template" | Hand-written copy, own design | Whole app | done | Slop scans on every string |
| 53 | "Density and design both count." | One idea per block; the rest one tap away | Whole app | done | v5: Company stacks many folds. One idea per block; the rest one tap away |
| 54 | "No restriction on models ... Pick the right tool for each step" | flash-lite for bulk, flash for grading | README cost table | done | Ask uses cached ledger first, model only if needed |
| 55 | "This is comfortably doable on free tiers" | Gemini free tier | | done | |
| 56 | "Efficiency earns bonus points ... Smart model routing ..., caching, and chunking" | Routing, cached snapshot, per-call chunking, cost table | README | done | |
| 57 | "We grade creativity, product sense, judgment, and architecture — not completeness." | | | done | |
| 58 | "Thin-but-working beats broad-but-broken. A focused prototype that nails one or two workflows beautifully" | The morning brief, and "did they do what they said" | Brief and the reader; Ask and Company | done | Two workflows: the morning brief, and "did they do what they said" |
| 59 | "A demo that doesn't run is the worst outcome." | Cached snapshot, plain errors, Try again | | done | Live link changes only after section 7 |
| 60 | "Build the smallest thing that proves you can build the real thing well." | | | done | |
| 61 | "The mobile-first prototype — a deployed link ... make it easy for us to try on a phone." | https://finn-ledger.vercel.app, installable | | done | |
| 62 | "The GitHub repository" | https://github.com/vedant-22/finn | | done | |
| 63 | "Your AI build history" | Session exports, sent by the user | NEEDS_FROM_USER | done (user sends) | |
| 64 | "A short writeup ... what you built, the key decisions and trade-offs, what you deliberately left out, and where you'd take it next." | docs/COVERING_NOTE.md | | done | Rewritten to lead with the point of view |
| 65 | "Submit ... to assessment@enam.com with the subject line 'ENAM - IIT screening - 2027'" | | NEEDS_FROM_USER | done (user sends) | |

## Reference document

| # | Line | What FINN does | Where | Status | What stage 4 changed |
|---|---|---|---|---|---|
| R1 | Announcement categories, "use it, adapt it, or ignore it" | All 17 used, with plain labels; "unclassified" reads "Paperwork" | Your lines, Brief | done | |
| R2 | results: "Quarterly/annual results, the board meeting approving them, results decks ... ads confirming results were published" | All merged into one results story per company | Reader: results item, its sources | done | |
| R3 | M&A: "including investing in a subsidiary, or selling a stake in one" | Deals; amount and share of revenue where the filing gives one | Brief | done | |
| R4 | management_change: "a CEO, CFO, MD, or director joining, resigning, or retiring" | Seniority decides act or note | Reader: management change | done | |
| R5 | insider_trading, pledging: promoter buying, selling or pledging | Categories exist; none in this snapshot's window | Your lines | done | Empty is fine |
| R6 | unclassified: "Routine, low-relevance paperwork ... that doesn't materially move the stock" | Folded | Brief: routine count | done | |
| R7 | "Concall ... The transcript is where you find guidance, tone, and what analysts are pressing on." | Promises from the transcripts; "Ask on the next call" questions | Company | done | |
| R8 | "Primary vs. secondary data ... The pull/analysis side ... must use primary data only." | Enforced in prompts and quote checks | Company | done | Ask uses the same rule |
| R9 | Revenue, EBITDA, PBT, PAT, margin, QoQ, YoY | Exactly these in the results card, EBITDA margin shown | Reader: results table | done | |
| R10 | D/E, working-capital cycle, cash conversion, FCF, ROCE | All shown | Company numbers | done | |
| R11 | Contingent liabilities, RPTs, auditor's qualification | Not read | | missing (by choice) | Left out: annual-report parsing is where we'd go next |
| R12 | "Material announcement — A disclosure significant enough to potentially move the stock" | The act tier | Brief | done | |
| R13 | "Guidance — Management's own stated forward expectations" | Promises with a number and a date | Company ledger | done | |
