# Plan: `notice` (the Network as a quiet sixth sense)

Planning session 13 Nov, evening IST. Deadline 15 Nov. One execution session, one deploy.

## Goal and success criteria

The brief's last word on the Network: "a quiet advantage, not a contact list. Show us what it notices that the investor wouldn't." Our own score for that line is 6 (`docs/NETWORK_PROGRESS.md`), and the same file says why the others stop at 7: "FINN names the person and stops."

Done means:
1. **It notices by joining, not listing.** Three new things on the demo day that no investor would assemble by hand, each a rule with evidence, each ending in one person and one question.
2. **One bold moment**: before a meeting, a person's path with the investor's own people on it, and the one question each could answer. No new screen.
3. Every new line is true to the data: a real person carries only what a filing says; nothing rests on a profile's invented years; a current insider is never "Ask".
4. Nothing breaks: `run_network.py` (225 today) all pass with the new checks added, `npm test` 27/27, `flows.py`, `walkthrough.py`, `claims.py`, `live.py`; 320 and 390 wide with no sideways scroll.
5. Reviewers score creativity and "what it notices" at 9.5 or more.

## First principles: what is a notice?

A notice is a **join the investor would not do by hand**. Today's engine does single joins (a contact is in a filing; a contact overlapped a filing person; a contact worked where an event happened). The three joins it does not do:

| Join | What it yields | Why a person misses it |
|---|---|---|
| **question × person** | FINN already raises questions (rules on a person's filing; the next-call questions). It already ranks people. It never pairs them. | You know Nitin ran IDFC's treasury. You don't recall it the morning a filing says a new CFO was "Interim CFO, IDFC". |
| **filing × filing** | Two filings, each too small to show, that together are a pattern. | Push judges a filing alone, and rightly folds a compliance officer's exit. Read with the audit head's move the day before, it isn't small. |
| **scarcity × silence** | Who is irreplaceable to this book, and going cold. | A contact list has no idea that one person is your only view inside a holding. |

## What was found in the demo data (measured this session, not assumed)

- **Home First's new CFO, Rinkoo Somani** (filed 27 Oct; the filing lists Dani family office and "Interim CFO, IDFC Limited"). Today FINN shows one person (Gaurav Sinha, Dani family office) and two questions with nobody attached. The network holds three more people it never mentions here: Nitin Agarwal (Head of Treasury, IDFC, 2012–2019) for "why only interim?"; Meera Krishnan (CFO of Aavas, a competitor) for "no lending background"; Kavita Deshmukh (Home First's own Chief Risk Officer, 2014–2020). Nitin is today printed as "Ruled out: both at IDFC, in different years", which rests on a profile's invented years and throws away the one person who can answer the question.
- **Crompton**: Head of Internal Audit, Risk & Control ceased on 15 Oct (reason filed: moving to a new role in the company); Compliance Officer resigned 16 Oct (personal reasons; FINN folded this filing); results filed 16 Oct. Two checking seats in two days. No notice today.
- **HDFC Bank**: the new MD & CEO (filed 1 Oct) and the new Chief Compliance Officer (filed 30 Sep, folded) both list ICICI Bank as a previous employer in their filings. No notice today. The same month's exits (compliance: tenure completed; legal: superannuation; MD: tenure completed) are routine by their own stated reasons and must stay silent.
- **Keep-warm is generic**: "A reason to call Arvind Pillai: CEAT approved results." What it doesn't say: Arvind is the *only* person in the network who has worked inside CEAT, and it has been five years. And Ramesh Iyer (purchasing) is offered a tax-tribunal order as his reason, which fits nothing he did.
- **Tried and dropped**: matching a filing's words to a theme to find a scarce expert. On this data it reads "input tax *credit*" as lending and "*equity* shares" as private equity. Too noisy to ship.

## Options considered

| Option | For | Against | Verdict |
|---|---|---|---|
| A. A network map (graph) | The brief names it | A hairball; contradicts "no screen of its own"; shows structure, not what to do | No |
| B. A calendar-driven card ("Thursday: Home First") | Strongest "sixth sense" | Needs an invented calendar, changes Today's count and order, new card type in one session | Design-only, stated as next |
| C. **The path with your people on it** | It is the brief's own scenario ("career path, overlaps with my network, and anything worth asking about") as one figure; a map of one life, not of the network; lives where the brief's own example lands (the incoming CFO's card) | Real people's filings give no years, so the figure must not imply an order it doesn't have | **Yes** |
| D. Draft the message to the contact | Closes the loop | Needs a model on private contact data; the core has none by design | No. "Copy the call sheet" instead |
| E. Second-order events across a supply link | Clever | 8 hand-kept links; relevance needs judgment rules can't make (a transmission order isn't cement demand) | No |
| F. "Was in the chair then" (event period × tenure) | The brief's "who has lived through what" | Only one filing line in the data carries a period | Design-only |

## What will be built

### 1. One question each (the spine) — `finn/network/engine.py`

`questions(p)` gains an `about` on each question: the employer it concerns, `trade` (the missing line of business), `predecessor`, `firm` (a director's day job) or `company`.

New `prep(p)` for a person arriving or in a seat (never for someone leaving): **stations**, each with at most one **pin**; a pin is a contact, how they stand to that station, and exactly one question.

| Station | Who is pinned (first that holds) | Tag | The question |
|---|---|---|---|
| The new seat | Best former insider by the existing relevance ranking. A current insider is shown as "You know", with the existing caution and **no question**. | Worked here | A raised question about the company (the exits cluster) if there is one; else "What does the {finance} seat at {Home First} need most?" |
| Each earlier employer the filing lists | A contact with a link to the person there (existing `links.between`); else a contact who worked there at all, with no claim that they overlapped | Strong / Fair link; else "Was there" | A raised question about that employer ("Why was the IDFC role only interim?"); else by vantage: "What was {Rinkoo} like to work for / to work beside / to have on the team / in the boardroom?"; for "Was there": "How is {Rinkoo} remembered at {IDFC}?" |
| A gap ("no lending employer in the filing") | A contact holding the same function in that trade, competitor first (`who_to_call` with the function as focus) | Same seat, a competitor | "What does a CFO need to know about lending that {Rinkoo} will be learning?" |
| A director's day job | A contact at that firm | link label | The raised question ("Does Samara Capital hold, or deal with, anything connected to CEAT?") |

Rules that keep it honest and small:
- At most 4 pins a person; a contact appears once, at their best station; a station with nobody stays bare (silence is shown, not filled).
- A raised question nobody can answer goes to **In the room** (ask the person). The predecessor question goes to a contact only on a fair link to the predecessor.
- Stations come in the filing's own order under the new seat, with the caption "Earlier roles as the filing lists them. It gives no years." Years appear only when they come from the filing or the investor's own record.
- "Was there" replaces "Ruled out … in different years" inside `prep`: knowing the institution is a different claim from knowing the person, and it survives the `final` task's removal of profile years. `reach` and identity are untouched.
- No pronouns for anyone in generated lines (names only). No words of suspicion.

Demo result this must produce (checked in evals):

```
HOME FIRST FINANCE · NOW      Chief Financial Officer, from 27 Oct
  Kavita Deshmukh · Worked here    Chief Risk Officer, 2014–2020.
    What does the finance seat at Home First need most?
DANI FAMILY OFFICE            Group CFO
  Gaurav Sinha · Strong link       Chief Investment Officer there.
    What was Rinkoo like to work beside?
IDFC LIMITED                  Interim CFO
  Nitin Agarwal · Was there        Head of Treasury, 2012–2019.
    Why was the IDFC role only interim?
NOT ON THE PATH: LENDING      No lending employer in the filing.
  Meera Krishnan · Same seat, a competitor    Chief Financial Officer at Aavas Financiers.
    What does a CFO need to know about lending that Rinkoo will be learning?
```

### 2. Where it shows — `web/src/Network.tsx`, `styles.css`, `api/network.py`, `finn/network/ask.py`, `pipeline/build_network.py`

One component, `Path`: a hairline down the left, a dot a station (filled for the new seat), the station in small capitals, the role under it, the pin indented (name in ink, tag, grey basis, the question in the existing question style). No new colour, type size or motion; it rises in with the section like the rows do.

- **Push, the full view of an arrival's card**: heading **Who was there**, sub-line "The path is the filing's. The people are yours.", the path, then **In the room**, then **Copy the call sheet** (the end band's Copy pattern; plain text: name, then the question), then the synthetic note. Cards about anything else keep "Who to ask" unchanged.
- **The Today card's line** for an arrival with two or more pins: today's line, then "3 more can each answer one question."
- **Look up**: "Who is Rinkoo Somani?" and "Brief me before I meet Home First" answer with the same component (the API's `diligence` and `team` answers carry `prep`). "Brief me before I meet Home First" becomes one of the four starters.
- **Pull, a company**: under Who to ask, one link when the company has someone new in a seat: "Before you meet them", to the same answer.
- In "Who to ask" everywhere else, a raised question sits under the person who can answer it instead of in a separate "Worth asking" list (Syngene: "Dr. Leena Joshi … Why are so many senior people leaving at once?").

### 3. Patterns across filings — `engine.py` `patterns(symbol)`, into `notices`, `company()` and the filing blocks

- **Checking seats** (new): two or more of finance, audit, risk, compliance, legal or company secretary change hands at one company within 30 days, in separate filings, counted once a person. A reason filed as retirement, superannuation or end of tenure doesn't count. Line: "Crompton: two of the seats that check the numbers changed hands in two days." Evidence: each seat, date and the filing's stated reason; "Results were filed on 16 Oct." when results fall inside the window. Pointer: the best former insider, never a current one (Deepa Nair, not Shweta Bansal, who works there now).
- **Same house** (new): two or more arrivals at one company within 45 days whose filings list the same previous employer, where that employer is a competitor (shares the company's trade) and not its own group. Line: "HDFC Bank's new MD & CEO and its new Chief Compliance Officer both come from ICICI Bank." Evidence: the two filings and days apart. Pointer: the contact with the longest time there (Meera Krishnan, ten years), with "What do ICICI Bank's people do differently?"
- **Exits cluster** (exists): unchanged rule, same shape of output.
- When a pattern used a filing Push had folded, the evidence says so: "One of the two was folded on its own."

A pattern shows in the fold, in the company's Who to ask sub-line (where the exits line already sits), and in the full view of a card for that company.

### 4. Keep-warm by who is irreplaceable — `engine.py` `warm`

- **The only one**: when a quiet contact is the single person in the network who has worked inside a holding, that is the line: "Arvind Pillai is the only person you know who has worked inside CEAT." Evidence: role and years, "You last spoke in Oct 2021.", then the occasion ("CEAT reported on 14 Oct.").
- **The occasion must fit the person**: an event in the contact's own line of work outranks results; an event that fits nothing they did (a tax order for a purchasing head) is not offered. With no fitting occasion and no scarcity, the contact is not in the list.
- **Their own work**: when the person to ask about an event has been quiet nine months or more, the notice says both: "DCM Shriram commissioned the Bharuch chloride plants on 30 Sep, in the business Harsh Vardhan Singh ran until 2021. You last spoke in Sep 2022."

### 5. Seen without a tap — `Network.tsx` `NetNoticed`

The closed "From your network" fold shows its first notice as its one grey line (the fold already takes a `line`). Order: patterns, then a contact in a filing, then the rest by weight. Six at most, as now.

## Edge cases and failure modes

| Case | Handling | Check |
|---|---|---|
| A person with no earlier employer in the filing and nobody inside | `prep` is None; the card says what it says today | all 42 filing people: pins ≤ 4, no contact twice, one question a pin |
| A contact who is the filing person (Rajat Shah) | Never pinned on their own path; the card keeps "who you know" | eval |
| A namesake (three in the demo) | Pins come only through `links` and careers, never names; ruled-out notes stay | existing 51 identity checks plus one on `prep` |
| A current insider | "You know", caution, no question; never a pattern's pointer | eval over every pin and pattern |
| The same person in several filings (Yesha Gandani is in two) | Counted once by person id | eval |
| Routine successions (HDFC Bank's three) | Stated reasons exclude them | eval: HDFC fires "same house" only |
| One person holding two seats, or moving within the company (Blue Dart) | One person is one seat; a move inside the company counts as the seat changing hands, and the reason is printed | eval on Blue Dart: silent |
| Same group as "same house" (an Aditya Birla trainee at UltraTech) | Group excluded | fixture |
| A giant shared employer that isn't a competitor | Silent | fixture |
| Profile years (invented) | `prep` never prints them and never rules a person out on them | eval: no year in a station from a profile; run again with `profiles.json` emptied and the Home First path is the same |
| A line that implies wrongdoing by a named real person | Facts, dates and the filing's own reason only; banned-word list (flag, suspicious, fled, purge, exodus, quietly) | eval over every notice and pin |
| Pronouns | None generated | regex eval |
| Long names at 320 px | Tag wraps under the name, as rows do now | `flows.py` at 320 and 390 |
| `network.json` grows | Measure; keep under 150 KB (111 KB now) | build prints size |
| Walkthrough strings change | `WALKTHROUGH_SCRIPT.md` updated in the same commit | `walkthrough.py` |

## Verification

- `evals/run_network.py`: a new group, "Prep, patterns and warmth", about 45 checks: the Home First path exactly as above; CEAT's director (Aman Khurana gets the Samara question); HDFC's MD (Sanjay pinned; the predecessor question In the room; Rahul "You know"); invariants over all 42 people; five synthetic fixtures (31 days apart: silent; routine reasons: silent; same group: silent; one person twice: once; two insiders: no "only"). Every existing check still passes.
- `web/test/e2e/flows.py`: Home First's full view shows Who was there, four pins, four questions, In the room absent; "Brief me before I meet Home First" shows the same; the fold's line is visible closed; Copy the call sheet puts the names and questions on the clipboard; 320 and 390, no sideways scroll, no NaN or undefined.
- `npm test`, `walkthrough.py`, `evals/claims.py`, `evals/gate.py` offline, `live.py` after the deploy.
- One screenshot each at 390×844 of the path and the fold, looked at before the reviewers.

## Order of work (each step ends green and committed; stop after any step and the app is whole)

1. Engine: `about`, `prep`, evals. Build `network.json`.
2. `Path` in the full view, Look up and the company link; the card line; Copy. `flows.py`.
3. Patterns: checking seats, same house; evals; shown in fold, company and full view.
4. Warm: the only one, fit, their own work; evals.
5. The fold's line and order.
6. Docs that describe the app: `DESIGN.md` (The Network), `docs/NETWORK_CORE.md` (table, notices, tests), `docs/NETWORK_PROGRESS.md` (re-scored honestly), README and covering note where they name the Network's moments or 225, one walkthrough beat, the brief-trace rows for the Network's scenarios, `claims.py`.
7. All tests; deploy once with `~/ENAM-FINN/deploy_network.sh` (if refused, don't retry: `NEEDS_FROM_USER.md`); `live.py` and `flows.py` on the link.
8. Result review by three reviewers (grader, investor and designer, staff engineer) on the built thing; fix below 9.5; record scores here.
9. Roadmap row done. STAGE: `execute writeup | opus` if it is still 13 Nov IST, else `plan final | opus` (the roadmap's rule). Commit. End.

If time runs short, cut from the bottom of 2–5: step 5, then 4, then "same house". Steps 1 and 2 are the task.

## Not doing, and said so in the docs

- No model anywhere in this. The questions are rules and templates; a model would write better ones and would need the contact list in a prompt.
- No calendar card, no message drafting, no memory of calls made, no Yes / No on a possible namesake (`network-loop`).
- No theme-from-filing-text notices (measured: too noisy).

## Files

`finn/network/engine.py`, `finn/network/ask.py`, `api/network.py`, `pipeline/build_network.py`, `data/network/filings.json` and `web/public/data/network.json` (rebuilt), `evals/run_network.py`, `evals/network_result.txt`, `web/src/Network.tsx`, `web/src/styles.css`, `web/test/e2e/flows.py`, the docs in step 6. `data/network/investor.json` is not changed: every example above is already in the demo network.

---

# Review round 1 (on v1, 14 Nov)

| Reviewer | Score | Creativity | What it notices |
|---|---|---|---|
| ENAM's grader | 8 | 8 | 7 |
| Investor and designer | 7.5 | 7.5 | 7 |
| Staff engineer and security | 7.5 | | |

What they found, and what v2 does about it (each checked against the data before it was accepted):

1. **The path rested on a profile's invented years** (engineer; measured: with `profiles.json` emptied Gaurav falls from a strong link to an undated one, the stations reorder to the filing's real order, IDFC then Dani, and CEAT's Samara station disappears because Samara is in no filing's `previous`). v2: the path reads the filing only; no dated overlap is ever claimed; the day-job station is dropped.
2. **Three of the four showpiece questions would embarrass the investor** (investor, grader): "no lending employer" printed under IDFC; "only interim" put to someone who may never have met her; "what does the seat need most" is filler. v2: the gap is the company's own trade (housing finance); a contact who was merely at the institution gets a question about the institution from where they sat; "why interim" goes to the room.
3. **"Same house" is obvious, and wrong in detail** (all three): everyone knows where HDFC Bank's MD came from; the compliance appointment was filed before his and starts 4 Jan 2027 with an internal officer holding the seat until then. v2: cut.
4. **"Checking seats" said more than the filings do** (grader, engineer): no successor is filed, so nothing "changed hands"; a compliance officer doesn't "check the numbers"; 8 of 15 companies filed a people change on a results day, so the results line is base rate dressed as a signal; the pointer (a sales head) broke the plan's own fit rule. v2: departures only, filed titles and filed reasons in the line, no results line, a pointer chosen by function.
5. **The path was a list** (investor): four stations of five lines each run past one screen. v2: the question leads, in ink; one grey line under it; one caption; the gap is a hollow dot.
6. **"The only one" would fire for 8 holdings** and repeat the "going cold" notice (engineer). v2: one a day, and it takes that holding out of the other line.
7. **A stronger join was free** (grader): one contact who answers two of the month's questions. Checked: Nitin Agarwal ran treasury at IDFC Limited (Home First's path) and is CFO at Orient Electric, Crompton's competitor (the function fit for its audit and compliance exits). v2 builds it in place of "same house".

Not taken: "the IDFC role was interim because of the 2024 merger" (grader, from memory). It is not in any filing in the repo, so no line may rest on it.

---

# Plan v2

Planning session 14 Nov, 04:00 IST. Deadline 15 Nov. One execution session, one deploy, and only on a green e2e run.

## Goal and success criteria

As v1, with these made exact:
1. Three new notices fire on the demo day **from real filing data by rule**, each a join no investor does by hand, each ending in one person and one question: the path, control seats, one call for two answers. (A fourth, the only one, if time allows.)
2. The bold moment is the scripted **diligence prep before a meeting**: "Brief me before I meet Home First" answers with the path, and the same path is in the arrival's full view.
3. **Nothing new rests on a profile.** Every new line is byte-identical with `profiles.json` emptied (asserted for all 42 people). A real person carries only what the filing says: titles, dates, stated reasons. A current insider is never asked a question.
4. Every rule's firing count over all 18 companies is asserted in the evals, not only its demo case.
5. Nothing breaks: `run_network.py` (225 today) with the new group, `npm test` 27/27, `flows.py`, `walkthrough.py`, `claims.py`, `gate.py` offline, `live.py`; 320 and 390, no sideways scroll.
6. Reviewers: aim 9.5; three rounds at most, stop on a plateau (the spec's stopping rule).

First principles and the options table stand as in v1, with "same house" moved to rejected and **one call, two answers** added: the join **person × several questions**, which a person misses because each question arrives on a different day under a different company.

## What will be built

### 1. The path (`prep`) — `finn/network/people.py`, `engine.py`

`people.py` keeps what the filing lists, untouched by any profile: `p.listed`, the filing's `previous` in its own order as (employer, role). `prep(p)` reads only the filing event, `p.listed` and the contacts' own records (the investor's, so their years may be shown). It never reads a profile stint, never claims two people overlapped, and exists only for someone arriving or in a seat.

A **station** is the new seat, each listed employer, and at most one gap. A station carries at most one **pin**: a contact, a tag, one question. The question is written for what that contact can know **without having met the person**:

| Station | Who is pinned (first that holds) | Tag | The question |
|---|---|---|---|
| The new seat | The best former insider by the existing ranking. A current insider is shown as "You know" with the existing caution and **no question** | Worked here | By the two functions: different, "Where do {risk} and {finance} pull against each other at {Home First}?"; same, "What does the {finance} seat at {Home First} have to hold the line on?"; contact's function general, "What should a new {CFO} at {Home First} fix first?" |
| A listed employer | A contact who works there now | There now | "What is {Rinkoo} remembered for at {the Dani family office}?" |
| | else a contact who worked there | Was there | Functions differ: "What did the {finance} seat at {IDFC Limited} carry, seen from {treasury}?"; same or unknown: "Who at {IDFC Limited} worked closest with {Rinkoo}?" |
| The gap: no listed employer in the company's own trade (the existing rule, worded by `co.themes[0]`, so "housing finance", not its root "lending") | A contact holding the same function at a competitor (`who_to_call` with the function as focus) | Same seat, a competitor | "What catches a new {CFO} out in {housing finance}?" |

- **In the room**: every raised question about the person (interim, predecessor, the gap when nobody is pinned) is for the person, not a contact. "Why was the IDFC role only interim?" becomes "Why was the IDFC Limited role an interim one?" everywhere.
- At most 4 pins; a contact once, at their best station; a station with nobody stays bare; no pronouns; names only; no word of suspicion.
- The seat line says "filed 27 Oct" (the filing states no effective date; where one is stated, "from {date}").
- The existing "Ruled out … in different years" note is not shown inside the path; `reach`, identity and the existing checks are untouched.

Demo result, asserted exactly in the evals (order is the filing's):

```
Who was there
The path is the filing's, and it gives no years. The people are yours.

●  HOME FIRST FINANCE · Chief Financial Officer, filed 27 Oct
     Where do risk and finance pull against each other at Home First?
     Kavita Deshmukh · Worked here · Chief Risk Officer, 2014–2020
●  IDFC LIMITED · Interim CFO
     What did the finance seat at IDFC Limited carry, seen from treasury?
     Nitin Agarwal · Was there · Head of Treasury, 2012–2019
●  DANI FAMILY OFFICE · Group CFO
     What is Rinkoo remembered for at the Dani family office?
     Gaurav Sinha · There now · Chief Investment Officer
○  No housing finance employer in the filing
     What catches a new CFO out in housing finance?
     Meera Krishnan · Same seat, a competitor · Chief Financial Officer, Aavas Financiers

In the room
     Why was the IDFC Limited role an interim one?
[ Copy the call sheet ]
```

### 2. Where it shows — `web/src/Network.tsx`, `styles.css`, `api/network.py`, `finn/network/ask.py`, `pipeline/build_network.py`

One component, `Path`: a hairline down the left; a filled dot a station, a hollow dot off the line for the gap; station and role on one small-capitals line; **the question in ink**; name, tag and basis on one grey line. No new colour, type size or motion. Four pins, the heading, the one caption, In the room and Copy fit in 560 px of height at 390 wide (measured in `flows.py`).

- **Push, an arrival's full view**: "Who was there" replaces "Who to ask" when the path has two or more pins. Other cards are unchanged.
- **The Today card's line** for that arrival is replaced, not lengthened: "Four of your people are on Rinkoo Somani's path." This is the notice reaching the investor unasked.
- **Look up**: "Brief me before I meet Home First" (a starter, replacing the weakest of the four) and "Who is Rinkoo Somani?" answer with the same component.
- **Pull, a company** with someone new in a seat: one link under Who to ask, "Before you meet them", to the same answer.
- **Copy the call sheet**: plain text, a name then the question, then In the room.
- Elsewhere, a raised question about a company sits under the person who can answer it (Syngene's exits question under Dr. Leena Joshi) and the separate "Worth asking" list goes.

### 3. Control seats — `engine.py` `patterns(symbol)`

Rule: two or more **different people leave** seats in audit, risk, compliance, legal, company secretary or finance at one company, with effective dates 30 days apart or less, in separate filings. A stated reason of retirement, superannuation or completed tenure doesn't count. (`roles.function` is extended only if it can't already tell these seats apart; its existing checks must hold.)

- Line, from filed titles only: "Crompton: the Head of Internal Audit, Risk & Control and the Compliance Officer both left their seats within two days."
- Evidence: each name, title, date and **the filing's own reason, verbatim, including the internal move** ("Nikhil Thakkar ceased on 15 Oct. Reason filed: transitioning to a new role within the Company."); "No successor is filed for either." only when computed true; "FINN folded one of the two filings on its own." No results line.
- For the next call (joins the existing next-call questions): "Who holds internal audit and compliance at Crompton now, and who do they report to?"
- Pin, by function fit and never a current insider: `who_to_call` with focus on finance, audit, risk and legal, whose own function is one of them. On the demo: Nitin Agarwal, CFO at Orient Electric, a competitor: "How does Crompton's finance and control bench look from Orient Electric?" If nobody fits, it says so and names no one.
- Measured on all 18 companies: fires once, Crompton. HDFC Bank's two are excluded by their stated reasons. Both facts are asserted.
- The exits cluster is unchanged. A pattern shows once a screen: in the fold, in the company's Who to ask sub-line, in the full view of that company's cards; the fold's `skip` covers the new kinds.

### 4. One call, two answers — `engine.py`, inside `notices`

Rule: over the window's open questions (the pins of every arrival's path, each pattern's pin, each event's person to ask), a contact who is the answer at **two or more different companies**, and a current insider at none, gets one notice. One a day: the contact with the most answers, then the strongest tie.

- Line: "One call, two answers: Nitin Agarwal."
- Evidence: one clause a company, each from its own notice ("Home First's new CFO came through IDFC Limited, where Nitin ran treasury. Crompton lost two control seats in two days, and Nitin is CFO at a competitor."), then when they last spoke.
- The execution session prints every contact the rule finds before fixing the copy; the evals assert who fires on the demo day and that the count is one. Fixtures: two questions at one company (silent); a current insider (silent).

### 5. Seen without a tap — `Network.tsx` `NetNoticed`

The closed "From your network" fold shows its first notice as its one grey line. Order: patterns, one call, a contact in a filing, then by weight. Six at most.

### 6. The only one — `engine.py` `warm` (cut first if time is short)

- One a day: among quiet contacts (nine months or more) who are the single person in the network to have worked inside a holding, the longest silence. "Arvind Pillai is the only person you know who has worked inside CEAT." Evidence: role and years; "You last spoke in Oct 2021."; the occasion only if one fits. That holding leaves the existing "going cold" line, so nothing is said twice.
- The occasion must fit the person: an event that fits nothing the contact did (a tax order for a purchasing head) is not offered, and with no fitting occasion the contact leaves the keep-warm list.
- v1's "their own work" wording is dropped.

## Edge cases and failure modes

v1's table stands, with these changes:

| Case | Handling | Check |
|---|---|---|
| Profile years | `prep`, patterns and one-call never read a profile | every new output for all 42 people and 18 companies is identical with `profiles.json` emptied |
| A filing with no `previous` (HDFC Bank's first MD filing) | Stations are the seat alone; the fuller filing for the same person is used when there are two | eval on Anup Bagchi: one path, from the filing that lists employers |
| A listed employer not in the registry | A bare station, no pin | invariant |
| An internal move counted as leaving a control seat (Crompton's audit head) | Counted, and the filed reason is printed in full in the evidence | eval: the reason string is in `why` verbatim |
| Routine successions (HDFC Bank) | Stated reasons exclude them | eval: HDFC Bank fires no pattern |
| One person, two filings (Yesha Gandani) | Once, by person | eval |
| Juxtaposition that insinuates | A pattern line may hold only the company, filed titles, a count and a span of days; the evidence only names, titles, dates and filed reasons; no results date; banned words as v1 | eval over every pattern |
| One-call names someone thin | Each answer must already be a pin by its own rule; a current insider anywhere is out | fixtures; firing list printed and asserted |
| Blue Dart, same group, long names, walkthrough strings, `network.json` size | as v1 | as v1 |

## Verification

- `evals/run_network.py`, new group "Path, patterns and one call", about 45 checks: the Home First path exactly as above; invariants over all 42 people (pins ≤ 4, a contact once, one question a pin, no question to a current insider, no year on a filing person's station, no pronoun, no banned word); the emptied-profiles equality; firing counts over all 18 companies for control seats (1), one call (1), the only one (1); fixtures (31 days apart: silent; routine reasons: silent; one person twice: once; a successor filed: the "no successor" sentence absent; one company, two questions: silent; two insiders: no "only"). All 225 existing checks pass, with the reworded interim question updated where it is asserted.
- `web/test/e2e/flows.py`: Home First's full view shows Who was there, four pins and four questions inside 560 px; the Today card's new line; "Brief me before I meet Home First" shows the same path; the closed fold's line is visible; Copy puts names and questions on the clipboard; 320 and 390, no sideways scroll, no NaN or undefined.
- `npm test`, `walkthrough.py` (with the new beat), `claims.py`, `gate.py` offline; `live.py` after the deploy.
- One screenshot each at 390×844 of the path and the closed fold, looked at before the result review.

## Order of work (each step ends green and committed)

1. `p.listed`, `prep`, the reworded questions, evals. Build `network.json`.
2. `Path` in the full view, Look up, the company link, the card line, Copy. `flows.py`.
3. Control seats: rule, evals, fold, company and full view.
4. One call, two answers: rule, evals.
5. The fold's closed line, order and `skip`.
6. The only one and the fit rule.
7. Docs that describe the app: `DESIGN.md` (The Network), `docs/NETWORK_CORE.md`, `docs/NETWORK_PROGRESS.md` re-scored honestly, README and covering note where they name the Network's moments or the check count, the walkthrough beat "Brief me before I meet Home First" (`WALKTHROUGH_SCRIPT.md`, `walkthrough.py`), the brief-trace rows for the Network, `claims.py`. `docs/ARCHITECTURE.md` and the ADRs only where a count they quote changes.
8. Every test. If all green, deploy once with `~/ENAM-FINN/deploy_network.sh` (wait for the new asset hash; if refused, don't retry: `NEEDS_FROM_USER.md`). Then `live.py` and `flows.py` on the link. Never deploy a red build.
9. Result review by three reviewers on the built thing, three rounds at most, scores recorded here.
10. Roadmap row done. STAGE: `plan network-loop | opus` (the overnight order). Commit. End.

If time runs short, cut from the bottom of 3–6: step 6, then 4, then 5. Steps 1 and 2 are the task; step 3 is the second thing a grader will repeat.

## Not doing, and said so in the docs

As v1, plus: no "same house" notice (obvious to its reader); nothing from a results date; no dated overlap between a filing person and a contact until a filing gives years.

## Files

As v1, plus `finn/network/people.py` and, if needed, `finn/network/roles.py`.

---

# Review round 2 (on v2, 14 Nov)

| Reviewer | Round 1 | Round 2 | Creativity | What it notices | Verdict |
|---|---|---|---|---|---|
| ENAM's grader | 8 | 9 | 8.5 | 8.5 | "Good enough, ship it." |
| Investor and designer | 7.5 | 9 | 9 | 8.5 | "With these three changes: good enough, ship it." |
| Staff engineer and security | 7.5 | 9 | | | "Good enough, ship it." Confirmed by running it: with profiles emptied the Home First path is as v2 prints it; control seats fires once. |

What was still raised, all taken into FINAL:
1. The Today line overcounts: Meera is the gap, not on the path (grader, investor). Count station pins: three.
2. Two path questions aren't sayable: "carry, seen from treasury" is template-speak, and a former insider is asked in the past tense (investor).
3. Crompton's pin question asked a competitor for an opinion; ask what only that seat sees (investor).
4. The one-call evidence said "lost two control seats", which brings back what section 3 took out (grader, engineer).
5. One call would pick Meera Krishnan, not Nitin (engineer, measured: Meera is pinned at Home First and on ICICI Bank's station at HDFC Bank, with the stronger tie). Count companies, template the evidence, assert whoever the rule picks.
6. The seat question breaks on board seats ("Where do operations and board pull against each other?"), and about five arrivals show a path, not one (engineer). A plain fallback, and the exact seat question asserted for every path shown.
7. If time runs short, cut the fold's closed line before one call (grader).

**Stopped after round 2 at 9 / 9 / 9** (average up 1.3 from 7.7). Below 9.5, and stopping is right: all three said to ship, what they raised is wording and one tie-break, all folded in below, and the rest of the grade is in the execution.

---

# FINAL plan

**The FINAL plan is Plan v2 above with the amendments in this section. Where the two differ, this section wins.** Sections of v2 not named here stand as written (goal, where it shows, control seats' rule, seen without a tap, the only one, edge cases, verification, files).

## A. The path's questions (replaces the table and the demo result in v2 §1)

| Station | Who is pinned (first that holds) | Tag | The question |
|---|---|---|---|
| The new seat | The best former insider by the existing ranking. A current insider: "You know", the existing caution, **no question** | Worked here | Both functions among the line functions (finance, treasury, risk, operations, sales, legal and the like) and different: "Where did {risk} and {finance} pull against each other at {Home First}?" Same function: "What did the {finance} seat at {Home First} have to hold the line on?" A board seat: "What should a new {independent director} at {CEAT} ask about first?" Anything else: "What should a new {role} at {company} fix first?" |
| A listed employer | A contact who works there now | There now | "What is {Rinkoo} remembered for at {the Dani family office}?" |
| | else a contact who worked there | Was there | Both functions among the line functions and different: "What did {treasury} need from the {CFO} at {IDFC Limited}?" (the listed role, shortened, without "interim" or "acting"). Otherwise: "Who at {ICICI Bank} worked closest with {Anup}?" |
| The gap (no listed employer in `co.themes[0]`) | A contact holding the same function at a competitor | Same seat, a competitor | "What catches a new {CFO} out in {housing finance}?" |

The seat pin is always a former insider, so its question is in the past tense. Every template is a string in one table in `engine.py`, so the evals can enumerate them.

Demo result, asserted exactly (order is the filing's; identical with `profiles.json` emptied):

```
Who was there
The path is the filing's, and it gives no years. The people are yours.

●  HOME FIRST FINANCE · Chief Financial Officer, filed 27 Oct
     Where did risk and finance pull against each other at Home First?
     Kavita Deshmukh · Worked here · Chief Risk Officer, 2014–2020
●  IDFC LIMITED · Interim CFO
     What did treasury need from the CFO at IDFC Limited?
     Nitin Agarwal · Was there · Head of Treasury, 2012–2019
●  DANI FAMILY OFFICE · Group CFO
     What is Rinkoo remembered for at the Dani family office?
     Gaurav Sinha · There now · Chief Investment Officer
○  No housing finance employer in the filing
     What catches a new CFO out in housing finance?
     Meera Krishnan · Same seat, a competitor · Chief Financial Officer, Aavas Financiers

In the room
     Why was the IDFC Limited role an interim one?
[ Copy the call sheet ]
```

**Every path that shows is checked, not only this one.** The execution session prints the path of every arrival with two or more pins (the engineer's estimate is five, among them CEAT's and Home First's new directors and HDFC Bank's MD), reads each question aloud, fixes the template table until none is odd, and then asserts each one's exact seat question in the evals. A path whose questions can't be made sayable by a template is not shown; the card keeps "Who to ask".

## B. The Today card's line (replaces the line in v2 §2)

It counts the pins at stations, not the gap: "Three of your people are on Rinkoo Somani's path." Shown when there are two or more station pins; otherwise the card's line is today's. The full view shows the path when it has two or more pins of any kind.

## C. Control seats' pin question (replaces the question in v2 §3)

Built from the seats that were left, asking what only a competitor's finance head sees: "Are Crompton's audit and compliance people in the market?" The next-call question stands.

## D. One call, two answers (replaces v2 §4)

Rule: over the window's open questions (the pins of every path shown, each pattern's pin, each event's person to ask), a contact pinned at **two or more different companies**, and a current insider at none of them, gets one notice. One a day: most companies, then the strongest tie. The rule is not tuned towards a name.

- Line: "One call, two answers: {name}." (or three).
- Evidence: one clause a company, from a template for each kind of pin, using that notice's own words and nothing stronger:
  - worked here: "{Company}'s new {role}: {First} was {role} there."
  - there now or was there: "{Company}'s new {role} lists {employer}, where {First} {is / was} {role}."
  - the gap: "{Company}'s new {role} lists no {trade} employer; {First} holds the same seat at {employer}."
  - control seats: "{Company}: two control seats were left within {n} days; {First} is {role} at {employer}, a competitor."
  - an event: that notice's existing line.
  Then when they last spoke.
- Measured in review: two contacts qualify on the demo day, Meera Krishnan (Home First's gap; ICICI Bank on the path of HDFC Bank's new MD) and Nitin Agarwal (IDFC Limited on Home First's path; Crompton's control seats). The rule picks Meera on tie. The evals assert both qualify, that exactly one notice is raised, and who it names. Nitin still stands at both of his places.
- The juxtaposition eval (company, filed titles, counts, spans of days, filed reasons; no results date; no banned word) covers this evidence too.
- Fixtures: two questions at one company (silent); a current insider at one of the two (silent).

## E. Order of work and the cut (replaces the last paragraph of v2's order)

Steps 1 to 10 as v2. If time runs short, cut in this order: step 6 (the only one), then step 5 (the fold's closed line and order), then step 4 (one call). Steps 1 and 2 are the task; step 3 is the second thing a grader will repeat. Whatever is cut is said in `docs/NETWORK_PROGRESS.md`, and no document describes something that wasn't built.

## F. Standing rules for the execution session

- First: the roadmap's standing live check.
- Every new line fires from the real filings by rule. If a rule doesn't fire as this plan says, the plan's copy is wrong, not the data: assert what the rule does, and change the copy.
- No model, no key needed. Deploy once, only after every test is green; a refused deploy goes to `docs/NEEDS_FROM_USER.md` and doesn't hold STAGE.
- Result review: three reviewers, three rounds at most, stop on a plateau; scores recorded here.
- Then roadmap row done and STAGE `plan network-loop | opus`.

---

# Execution (14 Nov)

Standing live check first: the link served `index-BqOq4beW.js`, the 11 Nov build, so nothing else had been deployed.

All six steps of the plan were built; nothing was cut. Commits: `7d796ee` (the path in the engine), `a774aa7` (Who was there, the card's line, Look up, Pull, Copy), `91664c9` (control seats, one call, the only one, the fold), `0bf0dd2` (docs, the walkthrough beat, claims).

Where the result differs from the plan's copy, and why (rule F: assert what the rule does, change the copy):
- **"Home First Finance", not "Home First".** The app's own short name for the holding is "Home First Finance", so the seat question reads "Where did risk and finance pull against each other at Home First Finance?". "Brief me before I meet Home First" still resolves.
- **The filed reason is printed as filed**, capital and all: "Reason filed: Transitioning to a new role within the Company."
- **The folded-filing sentence is exact about what was folded**: "Read alone, the Compliance Officer's filing was folded as routine." (the resignation was filed twice, so "one of the two filings" would have been wrong).
- **Five paths show**, as the engineer estimated: Home First's CFO (4 people asked) and its new director, CEAT's new director, Havells' new SBU head, HDFC Bank's MD. Each seat question is asserted. One template was fixed after reading them aloud: a rank and a seat ("Executive Vice President & SBU Head") is asked about as the seat ("a new SBU Head").
- **A path needs two people to ask.** With one, the card keeps Who to ask; `prep` returns nothing.
- **Before a meeting, management comes before the board**: a director's path is drawn only when no executive has a new seat (CEAT).
- **One call picked Meera Krishnan**, as round 2 measured; Nitin Agarwal also qualifies and is asserted as the other.
- **The path's height**: heading to Copy is 557 px at 390 wide, asserted at 560 in `flows.py`. The question is 15 px, not 16, to fit.
- **The Home First card is in the 3-day window**, not the 24-hour one. On the first screen the notice is the closed fold's line, "One call, two answers: Meera Krishnan."
- `vite preview` now proxies `/api` to `pipeline/dev_api.py`, so `flows.py` can put a question to the Network locally.

Tests on that build: `run_network.py` 299/299 (225 before; 74 new), `run_security.py` 105/105, `gate.py` offline 9 pass 0 fail, `claims.py` all hold, `npm test` 27/27, `flows.py` 61/61, `walkthrough.py` with the new beat, `sweep.py` (22 company pages at 320 and 390). The result review then changed some of the copy above; see round 1 below.

## Result review, round 1 (14 Nov, on `0bf0dd2`)

| Reviewer | Score | Creativity | What it notices |
|---|---|---|---|
| ENAM's grader | 7.5 | 7.5 | 7 |
| Investor and designer | 7.5 | 8 | 7.5 |
| Staff engineer and security | 7 | | |

What they found, all fixed in `62af7f5` and each now a check:
1. **Two voices on one screen** (grader, investor): the older "overlapped at" lines, which read the invented profile years, sat beside a path that says the filing gives none. Where a person has a path, it now replaces that line in the fold (a `path` notice, not "one call from"), on the company page and in the meeting answer. Left on purpose: a direct "Who knows …?" (`network-loop`).
2. **A referral, not a question** (grader, investor): "Who at X worked closest with Y?" is now "Did you work with Anup at ICICI Securities, or know who did?"; with two lines of work, "Were you at IDFC Limited with Rinkoo, and what did treasury need from the CFO?".
3. **Crompton's question insinuated, and contradicted the filed reason** (grader, investor): "Are Crompton's audit and compliance people in the market?" is gone. The line says what each filing says happened ("moved to another role in the company", "resigned"), and the competitor's CFO is asked about the seats where that contact sits: "Who do audit and compliance report to at Orient Electric?". The contact is listed once.
4. **The fold's first notice had no question and nothing could be tapped** (investor): one call prints the question for each company; a path or a pattern in the fold is a link.
5. **"Why was the role an interim one?" was pointed** (investor): "What was the interim brief at IDFC Limited?". The call sheet names the employer.
6. **Someone inside the company now could be asked** (engineer, with reproductions): at a listed employer, as the gap, and as a pattern's person when their stronger angle was a competitor. `_inside` is now checked at every site.
7. **`patterns()` off the demo data** (engineer): it crashed on underwriting seats, a later departure erased an earlier pattern, heads of a lending business counted as control seats, and a tenure cut short was dropped as routine. Seats are now read from the title, the latest window holding two or more is kept, and "before completion" overrides the routine reasons.
8. **The one-call clause could say something false** (engineer): it parsed a display string and always said "is". Pins carry role, employer and whether current.

Not taken: the investor's "Did your time cross hers" (a pronoun for a real person; the rule is names only). After the fixes: `run_network.py` 311/311 (86 in the new group), `flows.py` 65/65, `walkthrough.py`, `run_security.py` 105/105, `claims.py`, `gate.py` offline, `npm test` 27/27; the path is 557 px.

## Result review, round 2 (14 Nov, on `62af7f5`)

| Reviewer | Score | Creativity | What it notices |
|---|---|---|---|
| ENAM's grader | 8 | 8.5 | 8 |
| Investor and designer | 8 | 8.5 | 8 |
| Staff engineer and security | 8 | | |

Round 1's fixes held, except one tap below the path. What they found, all fixed and each now a check:
1. **"Who knows …?" contradicted the path and the fold's lead notice** (grader, investor): it ruled out Meera Krishnan and Nitin Agarwal "in different years" and said two people "overlapped", on the invented profiles' years. For a person with a path, the path is now the answer to the direct question too: no row, no "ruled out", and the lede says the filing gives no years. Identical with the profiles emptied.
2. **The fallback question was half a referral** (grader): "Did you work with Anup at ICICI Bank, or know who did?" is now "Were you at ICICI Bank with Anup, and what is Anup remembered for there?".
3. **The only one had no question, a routine occasion, and sat in the 24-hour fold on a 14 Oct filing** (grader, investor): it needs a reason now. Where an arrival's path already asks that contact (CEAT's new director asks Arvind Pillai), it is said on that path's notice, once. Otherwise the reason is the filing that fits, dated, with one question. Reasons to call are dated by their reason as well, and the fold shows only what is dated inside the window (standing blind-spot notes wait to be asked).
4. **Havells' question for the room overclaimed** (investor): "having not worked in one" is gone. "What carries over from Compass Group India and Britannia Industries to consumer electricals?"
5. **A pattern could state a move the filing doesn't** (engineer, with reproductions): "moved to another role in the company" is said only when the filing says the move is within the company and the action is not a resignation.
6. **"Same seat" on the line of work alone** (engineer): an assistant manager in finance at a competitor was "the same seat" as a new CFO. It is the line of work and the rank.
7. **The reason classifier** (engineer): "no disagreement with the management" is a denial, a death is not a departure to read into, "long-term" is not a completed term, and with no date stated the evidence gives the filing's date and says so.

After the fixes: `run_network.py` 326/326 (101 in the new group), `flows.py` 68/68, `walkthrough.py`, `sweep.py`, `run_security.py` 105/105, `claims.py`, `gate.py` offline, `npm test` 27/27. The average rose 0.67 and the lowest score rose, so a third and last round follows.

## Result review, round 3, the last (14 Nov, on `e5363c1`)

| Reviewer | Round 1 | Round 2 | Round 3 | Creativity | What it notices | Verdict |
|---|---|---|---|---|---|---|
| ENAM's grader | 7.5 | 8 | 8 | 8.5 | 8 | "Fix them and ship, with no further review round." |
| Investor and designer | 7.5 | 8 | 8.5 | 9 | 8.5 | "This is good enough, ship it." |
| Staff engineer and security | 7 | 8 | 8 | | | "Fix these three, each with a check, then ship." |

All three confirmed that round 2's fixes hold. What they found, each checked against the data before it was taken, all fixed in `d5294e4` and each now a check:
1. **CEAT's path missed its one real question** (grader): the filing's own profile opens "Founder & CEO of Samara Capital Group", and the investor knows a former principal there, but the path read only the listed earlier employers. A seat the filing's profile opens with is now a station ("SAMARA CAPITAL · Founder & CEO, now"). Aman Khurana is asked "Did Samara Capital hold, or deal with, anything connected to CEAT in your time there?", and what the firm holds today is in the room. Only a title that runs or owns a firm is read, at an organisation the registry knows: it fires for one person of 42, and "Nominee Director of LIC" is not a seat at LIC. Round 1 of the plan had cut this station because it then came from an invented profile; it now comes from the filing, and is the same with the profiles emptied.
2. **A path could name an employer the filing never did** (engineer, reproduced): "HDFC Life Insurance Company Limited" became HDFC Ltd, "IDFC FIRST Bank" became IDFC Limited. For a filing's words about a real person, a known name must now be the whole of what is written, give or take a suffix, a country or a division; otherwise the station keeps the filing's own words and pins nobody. No demo employer changed.
3. **A pattern counted departures that weren't** (engineer, reproduced): a change of designation ("Changed from SMP to Non-SMP category"), and a retirement filed by action with the reason as an age or not stated. Both are out. A company secretary filed after a company secretary and compliance officer left is a successor.
4. **"Ruled out … in different years" still sat under a path in the meeting answer** (engineer): gone wherever there is a path.
5. **Two answers a tap apart disagreed** (grader): "Nobody you know has worked inside" L&T and UltraTech, beside a contact whose own line says they did. Anyone who has held a seat there counts as inside, whatever their strongest angle is now. Someone the investor knows has worked inside all 18 holdings; "Where am I blind?" says so, and lists the five where nobody inside has been spoken to in two years.
6. **A generic reason to call repeated the card** (investor): "Eris Lifesciences reported results" in the fold, under a card that already says "Ask Rohit Bhargava". The fold leaves a reason to call to the card when that company has one.

Not taken, and why:
- "The 24 Oct filing is cited for the CFO" (investor). Checked on screen: the caption sits under Vineet Taneja's background, which the 24 Oct filing does give. Nothing is wrong.
- "Ask first: Kavita Deshmukh" beside a question about FY26 numbers on Today's call list (investor). True, and older than this task; it is the roadmap's "the person fits the kind of event", written down for `network-loop` in `docs/NETWORK_PROGRESS.md`.
- Five of the eleven pinned questions are the same template (grader). That is the ceiling of questions written by rule, and the documents say so.

After the fixes: `run_network.py` 341/341 (116 in the new group), `flows.py` 69/69, `walkthrough.py`, `sweep.py`, `run_security.py` 105/105, `claims.py`, `gate.py` offline, `npm test` 27/27.

**Deployed once, on the green build** (14 Nov): the link serves `index-dThe8uOm.js`; `live.py` 16/16, `flows.py` 69/69 and `walkthrough.py` passed on it.

**Stopped after round 3 at 8 / 8.5 / 8.** It is the third round, which is the cap, and the average rose 0.17 on round 2, a plateau. Below 9.5, and stopping is right: every reviewer said to ship once these were fixed, they are fixed with a check each, and what is left (questions by template, no calendar, a notice that can't raise a card) is `network-loop`'s or a model's, not another round's.
