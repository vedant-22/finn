# Plan: `writeup`

> **Amendment from `architecture-x` (13 Nov, revised after its fourth result review), read first.** The architecture changed under this plan:
> - **Take every count from its result file or from ARCHITECTURE as it then stands, never from this amendment.** `claims.py` checks them.
> - **The covering note's architecture paragraph** is ARCHITECTURE's "In 200 words". It leads with the live market day, gives the interrupts a week as a range with where each end comes from, and never leads with the act/fold ratio without "almost all on results".
> - **Already done in `architecture-x`:** the note's and the brief trace's contradictions ("no agent acts alone"; data "stays on the phone") are gone; README's architecture section matches the current diagram and links the five ADRs and the price study.
> - **Left for `writeup`:** README's evals table gains run_ingest, run_answer, run_agent, run_reaction, run_c2 and the gate, each with a claim in `claims.py`; the note and the trace rewritten as this plan says, the trace's architecture rows pointing to ARCHITECTURE §1–5, the ADRs, `docs/PRICE_REACTION.md` and `evals/gate.py`.
> - **"Next"** carries the rule reviews from PRICE_REACTION (orders, monitoring agency reports, investor presentations) and the keyed runs: `gate.py --live`, then the agent against its keep rule, then the GitHub settings in NEEDS_FROM_USER.
> - **INTERVIEW_DEFENSE.md stays out of the public snapshot.** It's the user's preparation, not a submission document; the user may override.

Roadmap task 2. The covering note, README, walkthrough, brief trace, checklist, needs list and link tags, written for this brief and for the app as it is on the `network` branch.

## v1 (11 Nov)

### Why this raises the result
The grader reads the email first, may open the link on a phone, and only then the repo. Today every one of those layers describes the stage-4 submission: the subject line is the old one ("ENAM - IIT screening - 2027"; this brief wants "IIT Kanpur – Founding AI Engineer - 2027"), the link is finn-ledger, the app it describes has a reader, "Read the brief" and "You're up to date" (section 11 replaced them with Today's cards, a full view, folds and an end band; the tabs are Today, Book, Look up), and the Network, a third of what is graded, isn't mentioned at all. The brief also asks two things nothing answers yet: the architecture "in your writeup" (it exists only as `docs/ARCHITECTURE.md`) and "say clearly in your writeup which [profiles] you used and how you'd do it for real". The share tags in `web/index.html` still point at finn-ledger and describe only promises.

### What I found (11 Nov)
- Live https://finn-network.vercel.app still serves `index-B42OWfM3.js` (the old build: network moments in, the architecture fixes not). No `GEMINI_API_KEY` there.
- Stale: `docs/COVERING_NOTE.md` (all of it), `README.md` (top, screenshots, "What it does", left out; the architecture, models, evals and run sections are from 11 Nov and stay), `docs/WALKTHROUGH_SCRIPT.md` (all beats), `docs/BRIEF_TRACE.md` (traced an older brief: "three sources", "one or two workflows", old subject; no Network or architecture rows), `docs/FINAL_CHECKLIST.md` (October passes), `docs/NEEDS_FROM_USER.md` (old subject; mixes done, stale and blocking items), `docs/DECISIONS.md` (point of view and interaction model are stage 4's), `web/index.html` og tags.
- Numbers in circulation that disagree or are unsourced: "$0.09 a company" (note) against "about $0.10" (ARCHITECTURE, README); "286 filings, 43 could interrupt" (30 days to 28 Oct); "62 of 70 within 1%"; "17 of 20 grades hold"; "225/225, 0 false matches"; "43 contacts, 7 profiles, 84 namesakes"; "22 companies"; "18 holdings, 14 sectors".

### The organising decision
**Three depths, one set of facts.** The email stands alone: someone who reads only it knows what FINN is, what the Network does with one example, the architecture in five lines, which profiles were used and how it would be done for real, what was left out and what's next. The README goes one level down; ARCHITECTURE, NETWORK_CORE and the trace go to the bottom. No document contradicts another. Every number and named example comes from one **claims table** (in this file's execution log: claim, source file or command, value on the day); a number that can't be sourced is cut.

**The point of view, one sentence, used verbatim in the note, README, DECISIONS and og description:** "FINN shows the few things that need you today, whether management kept its word, and who you know who can explain it." Followed by the reason it ends: most days it should be quiet.

### A. `docs/COVERING_NOTE.md` (the email; body at most 1,000 words, first person, plain)
- **To** assessment@enam.com. **Subject** exactly `IIT Kanpur – Founding AI Engineer - 2027` (en dash after Kanpur, hyphen before 2027).
- **Links:** the app (open on a phone; filings are a snapshot to 28 Oct; the network is invented and labelled), the repo, the build history (attached), the architecture diagram (attached PNG and in the repo).
- **Point of view** (≤ 90 words): the sentence; seven interaction models walked through the investor's day; why this one (it ends; a feed doesn't; chat hands the filtering back).
- **What I built** (≤ 260): Push (Today: the count, a card per thing, the line it crossed and moving it, the full view, the folds, the end band with next-call questions); Pull (Book and a company's promise ledger, Look up, any NSE symbol read live, quotes checked on the page); the Network (one person beside the event, Syngene's example; Who to ask on a company; the five direct questions with one example each; no model touches it; 225 checks).
- **The network profiles** (≤ 100, its own heading because the brief asks for it): what is invented, what is real and from where, what is hidden, how it is labelled; for real: a LinkedIn export's fields, careers by the contact's consent or a licensed provider, never scraped, retention.
- **Architecture** (≤ 180): two sides; the pipelines; privacy; which steps use which model and why, and that no agent acts on its own (the live read is a fixed sequence the phone runs, each step checked by code); cloud; link to ARCHITECTURE.md and the diagram.
- **Decisions and trade-offs** (≤ 7 numbered, ≤ 230): the ledger as the spine; quotes checked by code; XBRL not a model; a name alone never confirms a person; no model sees the network; size decides loudness; model routing and cost.
- **Left out on purpose** (≤ 90) and **Next** (≤ 90), matching the roadmap's open tasks so later tasks only move lines between them.
- **How I worked with the tools** (≤ 90): a reading guide to the build history (specs, every task planned and reviewed by three critics before code, blind panels on screenshots deciding what went live, evals as gates, things the model proposed that I removed).
- Signature as now.

### B. `README.md`
Top rewritten: the sentence, the live link, three new screenshots retaken at 390×844 from the local preview (`today.png`: a card with its network line; `view.png`: a full view with Who to ask; `lookup.png`: a direct network question answered). "What it does" rewritten for Today, the full view, the folds and band, Book and company, Look up, and a new **The Network** part (where it shows, the five questions, how the synthetic data is labelled). "Data sources" names the four. "What I left out" synced with the note. Architecture, models, evals and run sections kept; their numbers checked against the claims table. Old images deleted if nothing links them.

### C. `docs/BRIEF_TRACE.md`, rebuilt
From `pdftotext -layout` of both PDFs, every line that asks for, suggests or values something. Columns: # | the line, quoted | what FINN does | where (screen and element) | status (done, done but weak, missing by choice, missing) | the roadmap task that changes it. New rows for the four sources, the profiles line, every Network line (the five scenarios, "woven into", "quiet advantage", "notices what the investor wouldn't"), the four architecture bullets and the diagram, tools and cost, the build history, the subject. Honest statuses: "notices what the investor wouldn't" is done but weak (`network-loop`); business snapshot and contingent liabilities missing (`annual-report`); push is a snapshot, not a background push (by choice).

### D. `docs/WALKTHROUGH_SCRIPT.md`, rewritten (about 2:30)
Beats on the current app: Today ("2 need you", the Syngene card and its "Ask …" line, the window); a card's full view (results, the CFO's background, Who to ask, against their word, ask in place); the From your network fold and the band's next-call questions; Book, a company, a quote's page; Look up: a second-degree question ("Who knows HDFC Bank's new MD?") and any company read live (ASTRAL; if the key isn't on the link, the beat uses a prebuilt company outside the book and says so in the setup). Setup notes for a clean start. `web/test/e2e/walkthrough.py` (≤ 80 lines, flows.py's helpers) does the taps and asserts every on-screen string the script quotes; it runs on the local preview now and on the live link in `final`.

### E. Link tags
`web/index.html`: og:url and og:image to finn-network; og:description to the sentence. `web/scripts/og.py` and the og.png it makes: regenerate if its text is the old tagline. URL mentions in `web/scripts/icons.py` and `web/test/e2e/README.md`. Build, grep `dist/index.html`, flows.py on the local preview. One deploy attempt (visible change); if refused, it goes to NEEDS.

### F. `docs/NEEDS_FROM_USER.md`, `docs/FINAL_CHECKLIST.md`, `docs/DECISIONS.md`
- NEEDS becomes **Before you send, in order**: deploy; the key (from a project with billing off); the firewall rule; push `network` to the repo and make it public; export every build session; send (to, exact subject, body from the note, attachments). Then optional cleanup. Done and stale items removed.
- CHECKLIST: one table for this submission against "What to submit" plus README, walkthrough, secrets, base-design name, synthetic labels, links; rows that depend on the deploy or the key say "waits on deploy". October passes stay in git history.
- DECISIONS: the point-of-view line and the interaction-model entries brought to the current app (cards and the full view replaced the reader in section 11; the Network beside the event); the old design paragraph marked superseded by `DESIGN.md`.

### Verification
1. Claims table filled before the note is written; every number in the note, README, trace and walkthrough appears in it, one value each (grep).
2. Note body ≤ 1,000 words (`wc -w`), every section within its budget.
3. Links: every relative link in the README, note, trace and checklist resolves to a tracked file; every https URL returns 200 (the repo expected 404 while private, recorded).
4. `walkthrough.py` passes at 390×844 on the local preview; `flows.py` passes; `npm test`; build.
5. Screenshots looked at once each.
6. Hard rules: the base-design name absent from tracked files (pass 4's check); "synthetic" or "invented" stated in the note, README, walkthrough and on screen; no finn-ledger in what the grader reads except as history.
7. Style: no em dashes in my prose (the subject keeps the brief's dash), no padding; a local scan only, no text sent to an outside service.
8. Cold read: one fresh subagent gets only the note and answers: what FINN is, what the Network does, which profiles, where a model runs, what was left out, what to try first on the phone. A miss is fixed in the note.

### Order (commit after each)
1. Claims table. 2. Covering note. 3. NEEDS. 4. README and screenshots. 5. Brief trace. 6. Walkthrough and walkthrough.py. 7. Link tags, build, flows, deploy attempt. 8. DECISIONS. 9. Checklist pass, cold read, roadmap done, STAGE `plan network-loop`.

### Not in this task
App behaviour; ARCHITECTURE.md beyond syncing a number; INVESTOR.md and the history logs (PROGRESS, MOTION_NOTES, NETWORK_PROGRESS).

## Round 1 critiques of v1 (11 Nov): 6.5, 6, 6
- **Grader (6.5).** Section budgets add to 1,130 against a 1,000 cap. Architecture should sit under the brief's four bullet names, with name matching under pipelines and storage, retention, consent and access under privacy. Cost and efficiency (bonus points) get one line; give them a costed paragraph. "Left out" mixes choices with unfinished work: split off **Weak today**. "Any NSE symbol read live" is false while the link has no key. The build history is 90 words, and `~/ENAM-FINN/HOW_I_WORKED.md` and `EMAIL_TO_SEND.txt` (outside the repo, 3 Nov, old subject) are stale. `network` is 57 ahead of origin/main and 9 behind, so a plain push leaves the old README where the grader lands. Give the email a three-tap path to try first.
- **Investor and designer (6).** The sentence lists the three tabs, and "who you know who" stumbles. The difference (quiet, it ends) belongs in the sentence. The Network is about 300 words into the email: open with the 28 Oct morning (Syngene, the CFO gone, "Ask Dr. Leena Joshi"). All three screenshots are network screens and none shows the ledger, and the Look up answer is the contact-list mode phase 1 moved away from. The walkthrough has eight or more beats and should be five, ending on the end band. Say "a replay of 28 Oct" beside the link, check the home-screen name, icon and preview card, and say plainly that FINN names the person and stops.
- **Staff engineer and security (6).** Nothing ties a claim to the link: live today shows HDFC Bank's real new CEO with an invented 2011–2016 job, has no CSP and no noindex, and `/api/grade` gives 500. Tag each claim repo, live, needs deploy or needs key, and end NEEDS with a pre-send gate that fails loudly. The key has to go in before the deploy, because env vars apply only on a redeploy. profiles.json gives real people roles their filings never state ("Engineer" at Fiat, "Manager" at Citi) and normalised degrees, and that file goes public with the repo. Diff it field by field and say only what is true. The claims grep checks that a number is in the table, not that it's right, and misses number words. walkthrough.py will drift unless it reads its strings from the script, clears storage and probes for the key. Scan the history export for keys, and commit the note and NEEDS together.

## v2 (11 Nov)

Unchanged from v1 unless stated: why, what I found, three depths and one set of facts, the subject line, not in this task.

### The sentence (note, README, DECISIONS, og description)
"FINN stays quiet until something in your book needs you. Then it brings the event, holds it against what management promised, and names the person you know who can explain it." Each part is true of Today's two cards on 28 Oct (step 1 checks it). The proof the quiet is real is one sourced number: how many of the window's sessions had nothing past the default lines (claims table; it's used only if it holds up).

### Every claim carries its condition
The claims table lives in `evals/claims.py` (≤ 120 lines), not in prose. Each claim has the phrase as written, how its value is got (computed from `web/public/data/*.json` or the eval outputs where that's cheap, otherwise a pinned file and line), and a condition: `repo`, `live`, `needs-deploy` or `needs-key`. Run, it (a) prints every value, (b) fails if a phrase isn't in its document as written, and (c) fails on any numeral or number word in the note without a claim (allowed: dates, the subject's 2027, 390×844, quarter and year names). It runs at step 1, again at step 9, and again in `final`. Writing about conditions: the note is written for the link after the user's pre-send steps, and NEEDS says not to send until the gate passes.

### Real people: say only what is true, and scrub the docs
Step 1 diffs `data/network/profiles.json`'s five attached people field by field against `data/network/filings.json`, and checks what the renderer and `/api/network` show of each field. The writeup then says exactly that. For example, "on screen they carry only what their filing states; the data file still holds invented years and roles until `network-loop` strips them", or "screens show invented roles" if they do, with a line under Weak today. `ARCHITECTURE.md`'s "employers and roles are as the filings state them" is corrected if the diff disproves it. The grader-facing docs are scrubbed of invented facts about real people (NETWORK_CORE's "ICICI Securities under him, 2011 to 2016" is one): grep the five names in every tracked `.md`. NEEDS asks for the repo push after `network-loop`, so the public file holds no invented facts about real people; if 15 Nov comes first, the honest line stays.

### A. `docs/COVERING_NOTE.md`: body ≤ 1,000 words (hard), section targets ±20%
- To, the exact subject, then the links: the app, "a replay of the 28 Oct market close; the network is invented and labelled"; the repo (the `network` default branch); the build history (attached, with `docs/BUILD_HISTORY.md`); the diagram (attached and inline).
- **28 Oct, as FINN told it** (70): the morning in short. Syngene +12.2% on 43.5× volume, profit down 52%, the CFO gone, and the card's grey line naming the person you know who ran chemistry there. L&T is the second card. Then nothing else needs you.
- **The point of view** (50): the sentence, and why it ends. The seven interaction models get one clause and a link to DECISIONS.
- **Try it first** (30): three taps from walkthrough.py's path.
- **What I built** (240): Push (80: the count, cards, the line each crossed and moving it, the full view, the folds, the band with next-call questions); Pull (70: a company's ledger, the quote on its page, Look up, any NSE symbol read live, "needs-key"); the Network (90: Who to ask on a company, the five direct questions in one line each with their real reach, no model, the checks. It names the person and stops).
- **The network profiles** (70): invented and labelled; what step 1's diff found; for real, a LinkedIn export's four fields, careers by the contact's consent or a licensed provider, never scraped, kept 12 months after last use.
- **Architecture**, under the brief's names (180, about 45 each). *Data pipelines*: sources, refresh, storage, and the name-to-person match (a name alone never confirms). *Security and privacy*: two sides, what's stored and for how long, consent and access for real. *LLMs and agents*: which step, which model and why, and no agent acting on its own (the live read is a fixed sequence the phone runs, code checking each step). *Cloud*: what runs where. Diagram inline.
- **Cost** (60): what needs no model (XBRL, the network, ledger answers); what does (flash-lite reads, one flash grading call a company); one cache for everyone; the cost per company; $0 spent; grading on flash because pro returns 429 on the free tier.
- **Decisions and trade-offs** (110, five): the ledger as the spine; quotes checked by code; XBRL, not a model; size decides loudness; a brief that ends over a feed or chat.
- **Left out on purpose** (40): background push, accounts and storage, BSE-only names, real profiles. **Weak today** (50): annual reports unread, so no business snapshot; 17 of 20 grades checked by hand; the network names a person and stops; whatever step 1 finds on real people. **Next** (50): the open roadmap tasks, then a real deployment.
- **How I worked with the tools** (40): one line and a link to BUILD_HISTORY.

### B. `README.md`
As v1, with these screenshots, retaken at 390×844 from the local preview (and again from live in `final`): `today.png` (Syngene's card with its network line), `view.png` (a full view framed so Against their word and Who to ask share the frame), `company.png` (a company's ledger with Who to ask). Look up's answer is described, not shown. "What I left out" splits like the note's.

### C. `docs/BUILD_HISTORY.md` (new, ≤ 600 words)
A reading guide to the attached history. How the work ran: specs; each task planned, reviewed by three critics in at least two rounds, then executed; blind screenshot panels deciding what went live; evals as gates. Then the sessions by date (October from `~/ENAM-FINN/HOW_I_WORKED.md`, read only; November from the commit log and the session files' dates). Then four course corrections, each with its commit: velocity skew removed (`43c6259`), the chart scale replaced by the settle, a panel round that wasn't promoted, and the profile years hidden after the architecture review. No base-design name.

### D. `docs/BRIEF_TRACE.md`: as v1, plus a condition column (`repo`, `live`, `needs-deploy`, `needs-key`).

### E. `docs/WALKTHROUGH_SCRIPT.md` (about 2:20, five beats)
1. The Syngene card and the name (to 0:25). 2. Its full view: results, then the promise, then why that person (to 1:10). 3. Move a line and watch the count change (to 1:25). 4. A company's ledger, a quote and its page (to 1:55). 5. Back to Today, the end band and "Ask first", stop (to 2:20). An optional 15-second "any company" beat runs only if the key probe passes. Each beat has an `On screen:` line of backticked strings. `walkthrough.py` (≤ 80 lines, flows.py's helpers) reads them from the script, starts with storage cleared, does the taps, and checks each string after its beat. It probes `/api/call` and skips the optional beat with a note when there's no key.

### F. Link tags and the pre-send gate
- `web/index.html`: og:url and og:image to finn-network, og:description to the sentence. og.png regenerated if its text is the old tagline. The home-screen name and icon checked in the manifest. The URL mentions in `web/scripts/` and `web/test/e2e/README.md`.
- `web/test/e2e/live.py --presend` adds three checks to the existing ones (new build, headers, noindex, robots, grade, network answers, finn-ledger unchanged): a company outside the 22 gets its calls listed (the key works); `api.github.com/repos/vedant-22/finn` says public with default branch `network`; no invented year about a real person in `/data/network.json`.
- Build, grep `dist/index.html`, flows.py on the local preview. One deploy attempt; if refused, NEEDS.

### G. `docs/NEEDS_FROM_USER.md` (committed with the note)
**Before you send, in order:** 1. the key: `npx vercel env add GEMINI_API_KEY production`, from a project with billing off. 2. Deploy: `~/ENAM-FINN/deploy_network.sh`, after the key, since env vars apply only on a redeploy. 3. The firewall rate rule. 4. The repo, after `network-loop`: `git push origin network`, then `gh repo edit vedant-22/finn --default-branch network --visibility public --accept-visibility-change-consequences` (main stays as the October submission). 5. `python3 web/test/e2e/live.py --presend` must print no FAIL. 6. The build history: export every session, then `grep -l 'AIza\|GEMINI_API_KEY='` the export and fix anything it finds. `docs/BUILD_HISTORY.md` replaces `~/ENAM-FINN/HOW_I_WORKED.md`, and `~/ENAM-FINN/EMAIL_TO_SEND.txt` is stale, so don't use it. 7. Send to assessment@enam.com with the exact subject, the note as the body, and `docs/img/architecture.png` and the history attached. Then the optional cleanup. Done and stale items removed.

### H. CHECKLIST and DECISIONS: as v1. The checklist rows take the conditions, and DECISIONS takes the new sentence.

### Verification (v1's, changed)
1. `evals/claims.py` passes at steps 1 and 9.
2. Note ≤ 1,000 words.
3. Links resolve, with the repo condition recorded.
4. walkthrough.py, flows.py, `npm test` and the build pass.
5. Each screenshot looked at once.
6. Hard rules, plus the five real names grepped in tracked docs for invented facts.
7. Style, scanned locally only.
8. The cold read, now with "what are the three taps" and "what would you not trust yet".

### Order (each step committed)
1. The profile diff, claims.py, and the doc scrub of invented facts. 2. The note and NEEDS together. 3. README and screenshots. 4. BUILD_HISTORY. 5. Link tags, `live.py --presend`, build, flows, the deploy attempt. 6. Walkthrough and walkthrough.py. 7. Brief trace. 8. DECISIONS and ARCHITECTURE corrections. 9. Checklist, claims.py again, the cold read, roadmap done, STAGE `plan network-loop`.

## Round 2 critiques of v2 (11 Nov): 8.5, 8, 8
- **Grader (8.5).** Round 1 is fixed. Three things remain. The four corrections read as the system fixing itself; the brief asks how *you* course-correct and what you accept or rewrite. Each should say who caught it, quote what the user told the model, and say what was kept or rewritten by hand, with October's human calls carried over and one of them named in the note. The gate contradicts the fallback: `--presend` fails on invented years, yet the plan sends anyway if `network-loop` misses 15 Nov. Make that a warning and write the fallback sentences now. The export folder still holds October's HOW_I_WORKED.md, so NEEDS should swap in BUILD_HISTORY.md before zipping.
- **Investor and designer (8).** Round 1 is fixed. "Stays quiet until" suggests FINN reaches out, but background push is left out, so say something true of an app you open. Quote the card's line exactly. The section targets add to 990 before the links, so aim at about 900. If invented roles reach a screen, a Weak today line isn't enough for an official app: hide them in this task.
- **Staff engineer and security (8).** Round 1 is mostly fixed. claims.py must fail when the computed value differs from the number in the phrase, and the unclaimed-number check must cover more than the note. profiles.json, with its invented facts about five real executives, is in `network`'s history (since `6d13250`), so making the repo public publishes them even after `network-loop`. Push a one-commit snapshot as the default branch, or say so. The ARCHITECTURE correction has to land before the note links it.

## v3 (11 Nov): changes to v2
1. **The sentence**, true for an app you open: "FINN shows the few things in your book that need you today, and then it ends. Each comes held against what management promised, with the person you know who can explain it." The quiet-sessions number follows it only if claims.py sources it.
2. **The note's opening quotes the card's grey line verbatim**, checked against the local build by claims.py. The body targets about 900 words (What I built 200), with a hard cap of 1,000.
3. **Real people, step 1.** If the diff finds any profile field a filing doesn't state (a role, a degree's form, a year) reaching a screen or an `/api/network` answer, this task hides it the way the architecture task hid the years: the renderer and the API keep only what the filing states. `evals/run_security.py` extends its profile-years check to every profile field, and the change is deployed with step 5. The rest of the data clean-up stays in `network-loop`. ARCHITECTURE's sentence on profiles is corrected in step 1, before the note links it.
4. **The public repo holds no invented facts about real people, history included.** `network`'s history keeps profiles.json from `6d13250` on, so the grader's repo is a one-commit snapshot. In `final`, after `network-loop` has stripped the data, a local branch `submission` is made from `network`'s tree (`git checkout --orphan`, one commit, plain message) and checked: the five real names carry no field their filing doesn't state. NEEDS step 4 becomes `git push origin submission`, made the default and public. Main stays as the October submission, and the November history is in the build-history export, which goes to ENAM only. The `final` row in ROADMAP gets this step. If 15 Nov comes before `network-loop`, `final` makes the snapshot anyway from a tree whose profiles keep only filed fields, so the step doesn't wait on the whole task.
5. **claims.py, v3:** (d) each claim's computed or pinned value must equal the number in its phrase. (c), the unclaimed-number check, fails on the note, README, walkthrough and BUILD_HISTORY. On ARCHITECTURE and the trace it prints the unclaimed numbers, which are cleared by hand (the trace quotes the brief's own "15–20" and "~2×").
6. **The gate has two levels.** FAIL blocks the send: new build, headers, noindex, robots, grade, network answers, the key reads a new company, repo public with default branch `submission`, finn-ledger unchanged, no unfiled profile field in `/data/network.json` or an answer. WARN doesn't block: invented years or roles left in the data's unshown fields, until `network-loop`. The fallback sentences are written now, beside each `needs-key` and `needs-deploy` claim, in a fold in the note's source (an HTML comment, so it never reaches the email). If the key never comes, `final` swaps them in: "On this link, reading a company FINN hasn't read yet is switched off; the 22 it has read work fully."
7. **BUILD_HISTORY's corrections are the user's.** Each says who caught it (the user, a critic, an eval), quotes the user's own words where a session file has them (read-only from the sessions' transcripts; nothing invented, and with no quote it's said plainly that a critic or eval caught it), and says what was kept or rewritten. It carries October's human calls from HOW_I_WORKED.md (v4 as the benchmark, the fonts cut). The note's 40 words name one. NEEDS step 6: put `docs/BUILD_HISTORY.md` in the export folder in place of October's HOW_I_WORKED.md before zipping, and scan the export for `AIza` and `GEMINI_API_KEY=`. The export goes to ENAM only, never into the public repo.
8. **Order:** step 1 becomes the profile diff, any hiding and its eval, the ARCHITECTURE correction, the doc scrub, and claims.py. The other steps are as v2.

## Round 3 critiques of v3 (11 Nov): 9, 9, 8.5
- **Investor and designer (9):** nothing substantial. "With the person you know" suggests every card has one. If a 28 Oct card has nobody, say "where there is one". With a one-commit repo, say the full history is in the export.
- **Grader (9):** BUILD_HISTORY cites hashes that won't exist in a one-commit repo. Cite sessions, or ship a `git bundle` of `network` in the ENAM-only export, and say why the public repo is one commit. Once fixed, nothing substantial.
- **Staff engineer and security (8.5):** `git checkout --orphan` moves the shared worktree off `network`, which the deploy script refuses, and a cut-off leaves it stranded. Use `git commit-tree` instead. Hashes: cite dates and sessions. A stripped-profile fallback must rebuild network.json and rerun the evals so the public repo reproduces its own numbers. Fallback sentences in an HTML comment would travel in a pasted email, so keep them in claims.py. The key check has no path through when the key never comes, so add `--no-key`. Once fixed, nothing substantial.

Each fix is the reviewer's own remedy, applied as given in FINAL below. With them, all three found nothing substantial left.

## FINAL (v4, 11 Nov)

Self-contained: execute from this section alone. The subject, the link and the conditions are fixed here.

### Goal
The email, README, walkthrough, brief trace, build-history guide, checklist, needs list and share tags, written for this brief and for the app on `network`. Every claim is true on the link once the user's pre-send steps pass, and a gate fails loudly if they haven't. Three depths, one set of facts: the email stands alone, the README goes one level down, ARCHITECTURE, NETWORK_CORE and the trace go to the bottom, and none contradicts another.

### Step 0
Run the roadmap's standing live check. If the hash isn't `index-B42OWfM3.js`, run live.py and flows.py on the live link first, and log the result in `docs/plans/architecture.md`.

### The sentence (note, README, DECISIONS, og description)
"FINN shows the few things in your book that need you today, and then it ends. Each comes held against what management promised, with the person you know who can explain it." Add "where there is one" after "promised" if either 28 Oct card has no person. One sourced number for the quiet follows it, if claims.py can source it: how many of the window's sessions had nothing past the default lines.

### Step 1: facts first (one commit)
- **Real people.** Diff `data/network/profiles.json`'s five people attached to filings field by field against `data/network/filings.json`. Check what the renderer and `/api/network` show of each field. Hide any field a filing doesn't state (a role, a degree's form, a year) from every screen and every answer, the way the architecture task hid the years. Extend `evals/run_security.py`'s profile-years check to every profile field. This is a visible change, so it's deployed with step 5. Correct ARCHITECTURE's sentence on profiles to what the diff shows. Grep the five names in every tracked `.md` and remove invented facts about them, NETWORK_CORE's "ICICI Securities under him, 2011 to 2016" among them.
- **`evals/claims.py`** (≤ 120 lines). Each claim carries: the phrase as written and the document it's in; its value, computed from `web/public/data/*.json` or eval output where that's cheap, otherwise pinned to a file and line; a condition, one of `repo`, `live`, `needs-deploy` or `needs-key`; and, for `needs-key` and `needs-deploy` claims, its fallback sentence. It fails if (a) a phrase is missing from its document, (b) the value differs from the number in the phrase, or (c) the note, README, walkthrough or BUILD_HISTORY holds a numeral or number word with no claim. Allowed without a claim: dates, the subject's 2027, 390×844, quarter and year names, and the brief's own numbers inside quotes. For ARCHITECTURE and the trace it prints the unclaimed numbers, and they're cleared by hand. The known disagreements are settled here: the cost per company ($0.09 against about $0.10), and the 286 / 43, 62 of 70, 17 of 20, 225 / 225, 43 / 7 / 84, 22 and 18 / 14 counts.

### Step 2: `docs/COVERING_NOTE.md` and `docs/NEEDS_FROM_USER.md` (one commit)
**The note.** First person, plain words. The body runs from the subject to the signature, links included: target about 900 words, hard cap 1,000, section targets in brackets.
- **To** assessment@enam.com. **Subject** exactly `IIT Kanpur – Founding AI Engineer - 2027`.
- **Links** (40): the app, "a replay of the 28 Oct market close; the network is invented and labelled"; the repo; the build history (attached); the diagram (attached and inline). One line: the public repo is one commit, so invented facts about real people stay out of public history. The full history is in the attached bundle.
- **28 Oct, as FINN told it** (70): Syngene +12.2% on 43.5× volume, profit down 52%, the CFO gone, then the card's grey line quoted exactly as on screen. L&T second. Nothing else needs you.
- **The point of view** (40): the sentence and why it ends. The seven interaction models get one clause and a link to DECISIONS.
- **Try it first** (30): three taps, from walkthrough.py's path.
- **What I built** (180). Push (70): the count, the cards, the line each crossed and moving it, the full view, the folds, the band with next-call questions. Pull (60): a company's ledger, the quote on its page, Look up, any NSE symbol read live (`needs-key`). The Network (70): Who to ask on a company, the five direct questions in a line each, no model, the checks. It names the person and stops.
- **The network profiles** (60): what is invented and labelled, what step 1 found and hid. For real: a LinkedIn export's four fields, careers by the contact's consent or a licensed provider, never scraped, kept 12 months after last use.
- **Architecture** (160, about 40 each), under the brief's names. *Data pipelines*, with the name-to-person match (a name alone never confirms). *Security and privacy*: the two sides, what's stored and how long, consent and access for real. *LLMs and agents*: which step, which model and why. No agent acts on its own: the live read is a fixed sequence the phone runs, and code checks each step. *Cloud*. The diagram inline.
- **Cost** (50): no model for XBRL, the network or ledger answers; flash-lite reads, and one flash grading call a company; one cache for everyone; the cost per company; $0 spent; grading on flash because pro returns 429 on the free tier.
- **Decisions and trade-offs** (80, five): the ledger as the spine; quotes checked by code; XBRL, not a model; size decides loudness; a brief that ends over a feed or chat.
- **Left out on purpose** (40): background push, accounts and storage, BSE-only names, real profiles. **Weak today** (50): annual reports unread, so no business snapshot; 17 of 20 grades checked by hand; the network names a person and stops; anything step 1 couldn't fix. **Next** (50): the open roadmap tasks, then a real deployment.
- **How I worked with the tools** (40): one correction named, and a link to BUILD_HISTORY. Signature as now.

**NEEDS: before you send, in order.**
1. The key, from a project with billing off: `npx vercel env add GEMINI_API_KEY production`.
2. Deploy with `~/ENAM-FINN/deploy_network.sh`. It goes after the key, because env vars apply only on a redeploy.
3. The firewall rate rule.
4. The repo, after `final` has made `submission`: `git push origin submission`, then `gh repo edit vedant-22/finn --default-branch submission --visibility public --accept-visibility-change-consequences`. Main stays as the October submission.
5. `python3 web/test/e2e/live.py --presend` must print no FAIL. If you've decided against the key, the next session swaps in claims.py's fallback sentences and the gate runs with `--no-key`.
6. The build history. Export every session, and replace October's HOW_I_WORKED.md in the export folder with `docs/BUILD_HISTORY.md`. Add `git bundle create ~/ENAM-FINN/finn-network.bundle network`, which goes to ENAM only, never the public repo. Scan the export for `AIza` and `GEMINI_API_KEY=`. `~/ENAM-FINN/EMAIL_TO_SEND.txt` is stale: don't use it.
7. Send to assessment@enam.com with the exact subject. The body is the note. Attach `docs/img/architecture.png`, the history and the bundle.
Then the optional cleanup. Done and stale items removed.

### Step 3: `README.md` (one commit)
Top: the sentence, the live link with "a replay of 28 Oct", and three screenshots retaken at 390×844 from the local preview (again from live in `final`):
- `today.png`: Syngene's card with its network line.
- `view.png`: a full view framed so Against their word and Who to ask share the frame.
- `company.png`: a ledger with Who to ask.

Then:
- "What it does" for Today, the full view, the folds and band, Book and company, and Look up, with a part on the Network: where it shows, the five questions, how the synthetic data is labelled.
- "Data sources" names the four.
- "What I left out", split as the note's is.
- One line on why the public repo is one commit.
- The architecture, models, evals and run sections kept, their numbers in claims.py.

Old images go if nothing links them.

### Step 4: `docs/BUILD_HISTORY.md` (new, ≤ 600 words)
How the work ran: specs, each task planned with three critics over at least two rounds and then executed, blind screenshot panels deciding what went live, evals as gates. Then the sessions by date: October from `~/ENAM-FINN/HOW_I_WORKED.md` (read only), November from the commit log and the dates of the sessions' transcript files. Then four or five corrections. Each says who caught it (the user, a critic, an eval), quotes the user's own words where a transcript has them (nothing invented), says what was kept or rewritten, and is cited by date and session, with its hash resolving in the bundle. Include October's human calls: v4 as the benchmark, the fonts cut. No base-design name. One line on the one-commit repo and the bundle.

### Step 5: share tags, the gate, deploy (one commit)
- `web/index.html`: og:url and og:image to finn-network, og:description to the sentence. og.png regenerated with `web/scripts/og.py` if its text is the old tagline. The manifest's name and icon checked. The URL mentions in `web/scripts/` and `web/test/e2e/README.md` updated.
- `web/test/e2e/live.py --presend`. FAIL on: new build, headers, noindex, robots, grade, network answers, finn-ledger unchanged; a company outside the 22 gets its calls listed (skipped with `--no-key`, which instead checks that the link says reading is off and that the note carries the fallback); `api.github.com/repos/vedant-22/finn` public with default branch `submission`; no unfiled profile field in `/data/network.json` or an answer. WARN on invented fields left in the data but never shown, until `network-loop`.
- Build, grep `dist/index.html`, `npm test`, flows.py on the local preview. One deploy attempt (this step and step 1 are visible). If refused, it goes to NEEDS and doesn't hold STAGE.

### Step 6: `docs/WALKTHROUGH_SCRIPT.md` (about 2:20) and `web/test/e2e/walkthrough.py` (≤ 80 lines)
Five beats:
1. The Syngene card and its name (to 0:25).
2. Its full view: results, the promise, why that person (to 1:10).
3. Move a line and watch the count (to 1:25).
4. A company's ledger, a quote and its page (to 1:55).
5. Today's end band and "Ask first", stop (to 2:20).

An optional 15-second "any company" beat, only if the key probe passes. Each beat has an `On screen:` line of backticked strings. walkthrough.py, using flows.py's helpers, reads them from the script, clears storage, does the taps and checks each string. It probes `/api/call` and skips the optional beat with a note when there's no key. Setup notes for a clean start.

### Step 7: `docs/BRIEF_TRACE.md`, rebuilt
From `pdftotext -layout` of both PDFs: every line that asks for, suggests or values something. Columns: # | line, quoted | what FINN does | where (screen and element) | status (done, done but weak, missing by choice, missing) | condition | the roadmap task that changes it. Rows for the four sources, the profiles line, every Network line, the four architecture bullets and the diagram, tools and cost, the build history, the subject. "Notices what the investor wouldn't" is done but weak (`network-loop`). Business snapshot and contingent liabilities are missing (`annual-report`). Background push is missing by choice.

### Step 8: DECISIONS and ROADMAP
DECISIONS: the sentence, and the interaction-model entries brought to the current app (cards and the full view replaced the reader in section 11; the Network beside the event). The old design paragraph is marked superseded by `DESIGN.md`. ROADMAP's `final` row (already added at FINAL time) carries the snapshot step.

### Step 9: close
`docs/FINAL_CHECKLIST.md` becomes one table for this submission: "What to submit", plus the README, walkthrough, secrets, base-design name, synthetic labels, links and real-people rows, each with its condition and "waits on deploy" where true. claims.py, walkthrough.py and flows.py are run again. **Cold read:** one fresh subagent gets only the note and answers what FINN is, what the Network does, which profiles, where a model runs, what was left out, the three taps, and what it wouldn't trust yet. A miss is fixed in the note. Then the roadmap row is marked done, with the deploy state, STAGE is set to `plan network-loop`, and everything is committed.

### What `final` does with this (in ROADMAP)
The snapshot: `git branch -f submission $(git commit-tree network^{tree} -m "FINN for the Founding AI Engineer brief")`, with no checkout. If `network-loop` didn't finish, it first commits on `network` profiles keeping only filed fields, rebuilds `network.json`, reruns the evals, and writes the new counts into claims.py and the docs. Then the five real names are checked for unfiled fields in the tree, and `--presend` is run.

### Verification, in sum
claims.py at steps 1 and 9. The note's word count. Every relative link resolves to a tracked file, and every https URL's status is recorded with its condition. walkthrough.py, flows.py, `npm test` and the build. Each screenshot looked at once. Hard rules: no base-design name in tracked files, "invented" or "synthetic" stated in every document and on screen, no finn-ledger in what the grader reads except as history. No em dashes in my prose; the subject keeps the brief's dash. Style is scanned locally, and no text goes to an outside service. The cold read.

### Files
`docs/COVERING_NOTE.md`, `docs/NEEDS_FROM_USER.md`, `README.md`, `docs/img/{today,view,company}.png`, `docs/BUILD_HISTORY.md`, `docs/WALKTHROUGH_SCRIPT.md`, `docs/BRIEF_TRACE.md`, `docs/FINAL_CHECKLIST.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` (the profiles sentence), `docs/NETWORK_CORE.md` (the scrub), `docs/ROADMAP.md`, `evals/claims.py`, `evals/run_security.py`, `web/index.html`, `web/public/og.png`, `web/scripts/*`, `web/test/e2e/{live.py,walkthrough.py,README.md}`, plus the renderer and `api/network.py` if step 1 hides a field.

### Not in this task
App behaviour beyond hiding unfiled profile fields; the data clean-up (`network-loop`); INVESTOR.md and the history logs (PROGRESS, MOTION_NOTES, NETWORK_PROGRESS).

## Execution log
- Step 0 (11 Nov): the user had deployed `220d293` (`index-BqOq4beW.js`). `live.py` 16/16 after fixing the test's no-key route (`#/c/MARICO`, not `#/read/`); `flows.py` 40/40 on the live link. Logged in `architecture.md`.
- Step 1: the profile part landed in `220d293` (last session). The five real names in tracked docs now say only what their filings say. `evals/claims.py` added (`15bcd12`). It settled: about $0.10 a company ($0.095 over 21 built, not $0.09 over 19); rules settle 211 of 286 filings (74%; the 85% was a code comment, now corrected in README, ARCHITECTURE, DECISIONS and `finn/classify.py`); security 79/79, not 74/74; four of the five attached profiles hold unfiled fields, not three (ARCHITECTURE corrected); the unsourced "2.5M tokens, $2.20 while building" row cut. The quiet-sessions number was dropped: only 1 of 21 sessions in the window had nothing past the default lines, which says nothing about the brief ending. The note uses 286 filings, 43 that would interrupt, instead.
- Step 2: note 997 words (subject to signature). NEEDS rewritten as the seven pre-send steps; stale items dropped (the two old commits it named no longer exist in any branch). The repo is public on `main` only, which holds no network data.
- Step 3 (12 Nov): README rewritten for the app on `network` (`de03359`): the sentence, the link as a replay of 28 Oct, three screenshots at 390×844, What it does with a part on the Network, the four sources, left out split as the note's, the one-commit line. The unlinked `ask.png`, `brief.png` and `results.png` removed. `company.png` shows a ledger but not the company's name or Who to ask: reframed in step 5, when the preview is up.
- Step 4 (12 Nov): `docs/BUILD_HISTORY.md`, 600 words. Every hash resolves on `network`; the one quote is the user's spec (`NETWORK_SPEC2.md`). claims.py now covers it: reviewers and rounds counted from the plan files, 74% from the data, model names allowed. Live still `index-BqOq4beW.js`.
- Step 5 (12 Nov): share tags and description carry the sentence and point at finn-network; og.png regenerated from the local preview (Today, "2 need you"; no italics, the app's Inter; `bypass_csp` because the CSP blocks the injected card). `company.png` retaken: Who to ask on a company is about 670 px tall, so it can't share a frame with the ledger; the frame is L&T's name, the tally and its first promise, and the Network stays in `today.png` and `view.png`. `live.py --presend` and `--no-key` added. `npm test` 27/27, flows.py 40/40 on the preview. **The deploy went through** (`2ac18e6`): live.py all passed, flows.py 40/40 on the link; `--presend` fails only on the key and the repo (user steps 1 and 4), with a WARN for 14 unfiled profile fields left in the data, never shown.
- Found for `network-loop`: L&T's Who to ask says "Nobody in your network has worked inside Larsen & Toubro" above Anand Raghavan, whose line says "Also Project Director, Heavy Civil at Larsen & Toubro, 2001–2016". The cover line ignores a contact's past role at the company.
- Step 6 (12 Nov): `docs/WALKTHROUGH_SCRIPT.md` rewritten for the app on `network`: five beats, about 2:20, plus the optional any-company beat. Every `On screen:` string was copied from the running app, and spoken lines carry no numbers. `web/test/e2e/walkthrough.py` (73 lines) reads the strings from the script, does the taps the note's "Try it first" names and checks each one: 33/33 on the preview and on the live link, optional beat skipped (no key). A planted string fails it. It probes `/api/sources` rather than `/api/call`, since that answers `live: false` with no model call. claims.py: all claims hold (the note's quotes are now covered by the on-screen strings).
- Step 7 (12 Nov): `docs/BRIEF_TRACE.md` rebuilt from `pdftotext -layout` of the 8 Nov brief and its reference: 63 rows from the brief, 8 from the reference, each with status, condition and the task that changes it. Every quote checked as a substring of the PDFs' text. Facts checked against the code while writing: prices come from NSE's bhavcopy (not Yahoo), contacts carry jobs, schools, how you know them and when you last spoke, reconnect reasons are a former employer's filing or a new role in one, chunking is a page cap. claims.py's unclaimed numbers in the trace cleared by hand: each equals a claimed value or is a section, row or UI label.

### Final night, 15 Nov (`NETWORK_SPEC4.md`, FINAL NIGHT): the writeup made true of the app as it is now
No design change; documents only. Live check: the link serves `index-BmhQZqw8.js` (the `content-port` deploy), the same as `web/dist`, and the annual-report data it serves matches the repo.
- **Note** (`96a472a`): "marked Sample data" on the link line; the verdict shown as the app's words (Done, Missed, No update); *LLMs and agents* says a free question about a company is a checked workflow, tested offline, not yet in Look up, key-gated and run once the GEMINI_API_KEY is added. Cut to stay at the cap: the infrastructure sentence of *Where I'd take it next* (in ARCHITECTURE already) and the ledger decision's repeat of the point of view. 950 words; slop scan passes but for the subject's dash, which is the brief's.
- **README** (`96a472a`): the status words as the app shows them; the pill "Sample data · 28 Oct" and "sample data fixed at 28 Oct"; *Weak today* gains what waits on the key: the free question (built and tested offline, not behind Look up) and the annual-report model fallback (designed in ADR 6, not built). The "Demo network: ..." line is still what the app prints, so it stays.
- **Trace, DESIGN, ARCHITECTURE, DECISIONS, CONTEXT** (`5f44ea1`): row 36's words; row 5 says what waits on the key; rows 15, 33, R4 and R5 are `live`, since the fold is on the link. `claims.py` retires 'demo · 28 oct' and 'opening the ledger'.
- **Walkthrough** (`7694054`): beat 1 shows `Sample data · 28 Oct`, beat 4 shows `Done`; `walkthrough.py` all passed on the link.
- **NEEDS** (`f109a19`): step 2 says what the link serves now and that `writeup` needs no deploy; step 1 names what waits on the key.
- **BUILD_HISTORY** (`2a1b430`): the sessions of 12 to 15 Nov, every hash resolving.
- **Not done here, for `final`:** the three README screenshots predate the masthead pill; `final` retakes them from the link. BUILD_HISTORY's older lines still fail the scanner's list-of-three density (pre-existing; `polish`).
- **On the link, 15 Nov:** `live.py` all passed; `walkthrough.py` all passed; `a11y.py` 0 failed. `flows.py` stopped twice, at different places: first after 62 checks, waiting for the From your network fold after a reload; then after 71, where the Crompton page's pattern was read after a fixed 2.5 s and a later wait timed out. Probed directly on the link, both render in under a second (the pattern with its filed reason; the fold after a reload with a Same person answer), so these are the fixed waits on a cold start that CONTEXT warns of, not the app. `final`'s checks are `claims.py`, `walkthrough.py` and `live.py`, so the waits are left for `polish`.

### Result review, 15 Nov (one round, then stop): 8 / 8 / 8.5
Three reviewers on the committed documents, each told the design is frozen and the note capped. Every one said ship once its first fix is in.
- **ENAM grader, 8.** Cold read from the note alone answered everything but *when* a model runs with no key on the link, and *why* other symbols are off. Fixes: say models ran when the snapshot was built (taken); say what of the "company you didn't pick" line works now (taken as "Four companies outside the book already open.", claimed; the pinned no-key sentence is kept word for word, since `claims.py`, `live.py --presend` and NEEDS step 1 all hold it); move "a name alone never confirms" into *Data pipelines* (answered: the Network paragraph says it, and the cap is spent). Its cuts were taken in part: Push's first sentence (the 28 Oct section already shows a card), the fund's-own sentence of *next*, "Nothing else needed you."
- **Investor and designer, 8.** The free-question sentence read as if the key switches it on (taken: "its keyed eval runs once the key is added", and "not yet in the app"). The note implied every company gets a claims figure (taken: *Weak today* says 8 of 21, the claim now covers the note). README's server line was narrower than the app's sheet (taken: about ten minutes, pinned to `api/call.py`, and the host's hour of logs).
- **Staff engineer and security, 8.5.** Checks 1, 3, 5 true; README's heading called a designed-only fallback "key-gated" (taken: "one built and key-gated, one only designed"); an investor's own question also needs no-training terms (taken in README); the trace's `live` line named the old deploy (fixed before the review landed); NEEDS step 2 now says `claims.py` changed too.
- **Stopping.** One round by the final night's order: every reviewer at 8 or above and saying ship, and each issue taken or answered. A second round would confirm wording, not move a grade.

### Ship, 15 Nov
`ship.py --write` had failed since `annual-report` committed `evals/fixtures/annual_pages.json.gz` (14 Nov), and that session never logged a passing run: the design-name scan matched 8 times in the cut pages, every one the same place name at the start of a real institution's filed name (the stock exchange in three reports' general information; two companies in related-party and freight tables). The scan already blanks the registry's institutions for this reason; it now also lets those three filed names pass, without the name written in `ship.py`. Then all passed, and `submission` is one checked commit of `network`'s tree.
