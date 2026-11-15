# Network: progress

Nothing owed: `network-loop` is done (`docs/plans/network-loop.md`), and it built the three things this list asked for. Phase 3 below is the newest; all three phases are built, tested and live at https://finn-network.vercel.app. The list as it stood on 14 Nov: (1) Yes / No buttons on a name it can't place (the API already takes the answer); (2) let a network notice with no filing of its own (a contact turning up in a filing) raise a card; (3) pick the person by the kind of event on results cards too, not only on filings the engine has matched. Spec: `~/ENAM-FINN/NETWORK_SPEC2.md`.

## Phase 3: what it notices (14 Nov, the `notice` task)

The brief's last word: "Show us what it notices that the investor wouldn't." Phase 1 scored that line 6 and said why the rest stopped at 7: "FINN names the person and stops." This phase is four joins a person wouldn't do by hand, each a rule on the real filings, each ending in one person and one question. Plan, reviews and scores: `docs/plans/notice.md`.

| Join | What it yields on the demo day | Where |
|---|---|---|
| A person × the questions about them: **the path** | Home First's new CFO, as the filing lists the career: its former risk head on the seat, a former treasury head on IDFC Limited, someone at the Dani family office now, and, because the filing lists no housing finance employer, the CFO of a competitor. One question each; "What was the interim brief at IDFC Limited?" is for the room. Five paths show | The card's line ("Three of your people are on Rinkoo Somani's path."); the full view, as Who was there; a company page's "Before you meet them"; Look up: "Brief me before I meet Home First"; Copy the call sheet |
| A filing × a filing: **control seats** | Within two days, Crompton's Head of Internal Audit, Risk & Control moved to another role in the company and its Compliance Officer resigned; no successor is filed for either. Push had folded the resignation as routine. Fires at 1 company of 18; HDFC Bank's two are excluded by their own stated reasons. The person to ask is a competitor's CFO, and the question tests the pattern from that contact's own seat ("How long does it usually take to fill audit and compliance seats in consumer electricals?"), never about the people who left | The fold (the Month window leads with it, and it opens the company); Crompton's page, with the filed reasons, one person and one question; "Who holds audit and compliance at Crompton now, and who do they report to?" joins "Ask on the next call" |
| A contact × several questions: **one call, two answers** | Two contacts qualify; the rule raises one, Meera Krishnan (the closer tie), with the question for each company under the name | The fold; closed, it is the fold's one grey line on the first screen |
| Scarcity × silence: **the only one** | Arvind Pillai is the only person you know who has worked inside CEAT, last spoken to in Oct 2021, and the path of CEAT's new director already asks Arvind a question, so it is said there | The fold, on that path's notice (Month window), which opens the brief. CEAT then leaves the "going cold" line, and Arvind the reasons to call. With no arrival, it is a notice of its own: the filing that fits, dated, and one question |

Also: a reason to call must fit the person (a tax order is no longer offered as a reason to call a purchasing head); a question about the company sits under the person who can answer it (Syngene's exits question is under Dr. Leena Joshi), and "Worth asking" became "In the room", for what to put to the person.

**What keeps it honest.** The path reads the filing and the investor's own records only. It prints no year for a filing person and never says two people overlapped, and since `network-loop` the demo's invented profiles are gone from the data and the code, so nothing can rest on them. Someone inside the company now is named with the caution and never asked. A pattern's line holds only the company, filed titles, a count and a span of days; its evidence is names, titles, dates and the filing's own reasons. Nothing is cut from the plan.

**My own re-score, before the reviewers** (theirs are in the plan file):

| | Phase 1 | Now | Why not higher |
|---|---|---|---|
| Notices what the investor wouldn't | 6 | 8 | The questions are eleven templates, not written for the person. The path needs an arrival: on the 24-hour screen it is reached through the fold's line, and the Home First card is in the 3-day window |
| Changes what they do | 7 | 8 | One question for each call, and a call sheet to copy. It still doesn't draft the message or remember that you called |
| Important to the investor's day | 7 | 7.5 | The closed fold now says its first notice. A notice still can't raise a card or change Today's count (`network-loop`) |
| A quiet advantage, not a contact list | 7 | 8 | A path with one person is not shown; a station with nobody stays bare |

**Done in `network-loop` (14 Nov):** the five invented profiles are gone, so a real person carries only filed fields, and Anup's school line is back on his path; a join across filings raises one card on Today, outside the count; the person beside a question fits its kind (Home First's guidance row now names Meera Krishnan at a competitor, not Kavita Deshmukh, who left in 2020), each asked about their own seat; results are a reason to call only with their figures; a possible namesake is answered with Same person or Someone else, kept on the phone, and every view rebuilds from it. Plan, measurements and checks: `docs/plans/network-loop.md`. **Left:** no calendar, so "before a meeting" is asked, not known.

**Tested (14 Nov):** `evals/run_network.py` 341/341 (116 new: the demo results exactly, invariants over all 42 people, firing counts over all 18 companies, fixtures, the emptied-profiles equality); `npm test` 27/27; `flows.py` and `walkthrough.py` (with the new beat) on the local preview; 320 and 390 wide with no sideways scroll; the path's heading to its Copy button is 557 px at 390 wide.

## Phase 1: scored as a reviewer on a phone (10 Nov)

Scored for importance and value, not correctness. The engine and its rules were left as they are (225/225).

| | Before | After | Why |
|---|---|---|---|
| Important to the investor's day | 3 | 7 | Before: the first screen never mentioned it; the one thing that mattered today (four people left Syngene, and the investor knows someone who ran chemistry there) was the second of five grey paragraphs under two folds. After: the person is on the card. Not higher: the network still doesn't change the count or the order of Today. |
| Changes what they do | 3 | 7 | Before: no name beside the event; Syngene's full view said who it wasn't and not who to call. After: a name beside the event, and again beside the question for the next call. Not higher: FINN names the person and stops; it doesn't draft the message or remember that you called. |
| Woven into Push and Pull | 3 | 8 | Before: four blocks with their own headings. After: a line on the card, rows in the full view, a line in the end band, a fold with the other folds, a section under a company's questions, the same rows in Look up. |
| A quiet advantage, not a contact list | 4 | 7 | Before: five paragraphs of equal weight, most about companies not on today's cards. After: one grey line where someone is close enough, nothing where nobody is. |
| Notices what the investor wouldn't | 6 | 6 | Unchanged, and that is honest: the engine notices the same things. The four exits now sit beside the person who can explain them, but a contact turning up in a filing and a name it can't place wait in a fold. |
| Simple and elegant | 3 | 7 | Before: bold lead-ins running into grey paragraphs, unlike anything else in FINN. After: FINN's own hairline rows, small capitals and folds. |

**What changed**
- Cut: the "From your network" block between the folds and the end band, the "Your network" list of bolded paragraphs, the "Who to call" section under every fold of a company page.
- The unit is now one person beside the event. `forItem` in `web/src/Network.tsx` picks them: the person the engine matched to the filing; else whoever links the investor to someone the filing names (fair links and better); else the one contact closest to the company (inside it, or a competitor, supplier, customer or group company). Otherwise nothing.
- A contact who works at the company now, or left within a year, is named with "You know", never "Ask", and is never the "Ask first" in the end band. The caution is in their row.

## Phase 2: the moments

| Where | The moment |
|---|---|
| Push, a Today card | One grey line: "Ask Dr. Leena Joshi. Director, Discovery Chemistry there, 2011–2019." |
| Push, the full view | Who to ask: a row a person (name, how they stand to the company, why them, when you last spoke). Worth asking. Ruled-out namesakes as a footnote. |
| Push, the end band | "Ask first" under each question for the next calls. |
| Push, the folds | From your network, a third fold: what the cards don't already carry. |
| Pull, a company | Who to ask, straight under "Ask on the next call". It rises in with the page's other sections. |
| The direct question | Look up's "Ask your network" starters and typed questions, answered in the same rows. |

Synthetic people are labelled in every place: under Today's cards, in the fold, and at the foot of each Who to ask and each answer.

**Tested (10 Nov):** `npm test` 27/27; `web/test/e2e/flows.py` 40/40 on the local build and on the live link; no sideways scroll, no NaN or undefined at 320 and 390 on Today (24h, Month, the fold open), a full view, five company pages and four direct questions. https://finn-ledger.vercel.app is unchanged (same asset as before).

**Not done:** no Yes / No on a possible namesake; the card's person is the same for every event at a company unless the engine matched the filing itself; nothing was added to the motion (the new rows use the reveal, the folds and the card morph that were already there).

## Core (done earlier)
- `data/network/`: registry, synthetic investor and 43 contacts, and the filings the Network reads.
- `finn/network/`: names, registry, roles, people, identity, links, engine, ask (no model).
- `pipeline/build_network.py` writes `data/network/filings.json` and `web/public/data/network.json`. `api/network.py` answers questions.
- `evals/run_network.py`: 334/334 on 15 Nov (322 after `network-loop` removed the 42 profile checks with the profiles; 225 before the `notice` task). Write-up in `docs/NETWORK_CORE.md`.

## Decisions
- No model calls in the network core. Matching people is rules that can be tested.
- A name alone never confirms a person. It needs a shared employer or school, weighed by the employer's size, and no contradiction.
- Same employer counts only when the years overlap. Unknown years are kept but marked and scored low. Group companies are separate employers.
- Nothing weaker than a fair link is pushed. Weak links show only when asked.
