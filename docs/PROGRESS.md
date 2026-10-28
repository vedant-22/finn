# Progress

Next: design upgrade critic round (designer, ENAM evaluator, muted investor) on the new screenshots in docs/img vs shots/ref-bdc-390*.png, then fix. Background: `pgrep -f regrade.sh` sleeps to 12:40 IST 29 Oct, then regrades the 8 flash-lite companies (log data/regrade2.log). When it finishes: compare verdicts, rerun evals/sample_grades.py and update evals/grades_review.md, redeploy, recheck screenshots. If the job died, restart: `nohup zsh pipeline/regrade.sh > data/regrade2.log 2>&1 &`.

- [x] Brief analysis, company notes, ideation (docs/)
- [x] Engine: finn/ (sources, classify, triage, results, people, ledger, research)
- [x] Push snapshot: web/public/data/push.json (built 28 Oct 06:12 IST)
- [x] Ledgers for 18 holdings + DIXON, TITAN, PIDILITIND, POLYCAB
- [x] Frontend (Today, Book, Company, Look up, Your lines), DESIGN.md
- [x] Vercel API for live lookups; tested on ASTRAL in production
- [x] Evals: triage, results numbers, quote check (evals/)
- [x] Critic round 1 (evaluator+engineer, designer+user) and fixes
- [x] README, covering note, walkthrough script; slop_scan passes (walkthrough's long-sentence gate fails on purpose: it's spoken)
- [x] Regrade ledgers with gemini-3.5-flash (28 Oct): 11 of 19 on flash, then the 20/day limit hit; 8 on flash-lite, queued for 29 Oct 12:40 IST
- [x] Hand review of 20 sampled grades: 18 hold (evals/grades_review.md)
- [x] Redeployed and README screenshots refreshed (28 Oct ~13:05 IST)
- [x] Critic round 2 (done inline on the fresh screenshots, not with sub-agents): repeated deadlines fixed; README company shot retaken
- [x] Final checklist x2 (pass 2 28 Oct 13:20 IST); README, covering note and evals README now report the hand grade check
- [x] Publish GitHub repo: https://github.com/vedant-22/finn

## Polish log (28 Oct)
- Plain-English errors with Try again on live lookup (quota, network, timeout) and on boot; tested at 390x844 with a mocked 429
- Today says so when nothing crossed the lines
- Standard web-app-capable meta (console warning gone)
- "Your lines" sheet: grab handle, drag down to close (short drags snap back)
- Book: on equal kept share, more misses rank weaker
- Deployed and checked live 28 Oct ~12:20 IST
- Company sources footer: "N promises found, quotes checked" (was "kept after checking", which read like a verdict)
- Company screen: a failed company-file fetch shows the plain error and Try again (was stuck loading); the 'About a minute' note shows only during live research. Tested at 390x844 with an aborted request
- Today data preloads in index.html, so it downloads alongside the JS (companies.json preload dropped: not used on the first screen)
- Look up: Ready to open and Recent chips show names (companies.json is now {symbol: name}; the app still reads the old list). After the regrade, rerun the index line: build_ledgers writes it, but the running job uses the old code
- Today: the headline count rolls when switching 24h/3 days/Week/Month; tabular digits; off under reduced motion
- Company: 'Opening the ledger' with the pulsing dot if the file takes over 400 ms; heading uses the holding's name while loading. Tested at 390x844 with a delayed request
- Batch LLM calls wait out per-minute free-tier 429s (FINN_PATIENT=1, set by regrade.sh) instead of dropping to flash-lite; daily limits still drop a tier. Live API unchanged
- Promise lines drop a 'by ...' the promise already states (every date word already in it), plus 'by by' and 'by unspecified'. Checked against all 194 graded promises
- docs/DONE created 28 Oct 13:25 IST after final checklist pass 2
- Today cards: 'and N related' is now a button that lists the other filings in the story, each linked. Filing titles read cleaner everywhere: 'Press release: <title>', no wrapping quotes, 'Financial results for...' instead of ', the financial results'. Tested at 390x844; deployed and checked live 28 Oct ~13:16 IST (the Vercel CLI prints 'Not authorized' after a successful deploy; check the live bundle name)
- Book: tap a count in the tally (missed, gone quiet, ...) to list only the companies behind it; 'Show all' or a second tap clears. Tested at 390x844; deployed and checked live 28 Oct ~13:22 IST (deploy with `npx vercel --prod --yes` from app/)
- Look up takes a name as well as a symbol: 'pidilite', 'larsen', 'ceat' show a 'Did you mean' chip (word-start match on known names and symbols), and Enter opens the single match once 4+ letters are typed (so short real symbols still go through). Tested at 390x844; deployed and checked live 28 Oct ~13:27 IST
- Company: not-due promises whose verdict only restates them ('... remains ongoing', '... is pending': 85 of 157) show no verdict line; the dash mark and tally already say not due. Model text (targets, verdicts, numbers evidence, read, questions, for/against, Today promise lines) shows '₹1,450 crore' instead of 'INR1,450 crores' / 'Rs. 5600-5800 Cr'; quotes stay verbatim. Display-only (lib.ts rupees, CompanyView verdictText), so regraded ledgers get it too. Tested at 390x844; deployed and checked live 28 Oct ~13:30 IST
- Today people: 'Changed from SMP to Non-SMP' no longer reads as 'Leaves as' (now 'Stays Head of Chemistry, off the senior management list', sorted last so a real resignation shows first); backgrounds that only restate the role ('has assumed charge as...', 'Designated as SMP...') and empty reasons ('Leaving the Company', 'no other material reason') hidden. ₹ figures get Indian commas (₹5,600–5,800 crore). Tested at 390x844; deployed and checked live 28 Oct ~13:40 IST
- Book: sorted by kept share with one kept and one not-kept added, so Havells (1 gone quiet) no longer ranks weaker than Home First (6 gone quiet) or TCI (1 missed). README book shot retaken. Deployed and checked live 28 Oct ~13:45 IST
- Company page lights the tab it was opened from (Today, Book or Look up; was always Look up). Singular forms: '1 new promise', '1 statement', 'at 1 company', '1 that didn't match was thrown out'. Tested at 390x844 (Book → company → Back, Today, Look up chip); deployed and checked live 28 Oct ~13:50 IST
- Back from a company returns to the same place in Book or Today (was always the top): scroll is saved per screen and restored only on the way back from a company; tab taps still start at the top. Book's tally filter and Today's open folds survive the trip; Book starts from the in-memory company cache, so the list is full height at once. Tested at 390x844 (Book 1100 → company → Back = 1100; Today with fold open, 4355 → L&T → Back = 4355, fold still open); deployed and checked live 28 Oct ~14:05 IST
- Promise marks (tick, cross, ring) draw when they scroll into view, not all at once on load, so cards lower on Today and Book get their pencil stroke when the reader reaches them (one shared IntersectionObserver; reduced motion unchanged). Tested at 390x844 (Today far card, Book scroll, company → Back); deployed and checked live 28 Oct ~14:15 IST
- Company numbers: negative figures (cash conversion cycle, return on capital, debt to equity, ₹ crore) use a true minus (−151 days, was -151), matching the % figures elsewhere. Tested at 390x844 on L&T; deployed and checked live 28 Oct ~14:30 IST
- Company numbers: Profit after tax and Net interest income show the change on a year ago (from the same quarter a year back in the file), like Revenue already did; Home First was ₹170 cr with nothing under it, now +29%, matching its Today card. Tested at 390x844 on Home First and L&T; deployed and checked live 28 Oct ~14:02 IST

## Design upgrade (28 Oct)
- Studied the reference at 390x844 (shots/ref-bdc-390*.png, not committed) and its source: Inter + PT Serif, 30/26/21/16/14 mobile scale with tight tracking, hairlines, pill controls, stagger fade on expo-decelerate. Rules in design/inspiration.md
- ENAM palette sampled from enam.com: white, black, grey #6A6970, ENAM blue #005DA3, #D2D2D2 rules. DESIGN.md now has the palette with roles and contrast, and the new type
- Restyle (CSS + fonts, no feature changes): white ground, ENAM blue only on the primary button, active tab and newest volume bar; Today cards are hairline sections, not tinted boxes; 72px headline count; window choice is pills; Look up input is a single underline with a blue pill button; PT Serif for the sentences FINN says (story lines, the read, verdicts, notes); one reveal (fade and rise 12px, 900 ms, first three staggered) via one observer in main.tsx; reduced motion shows everything in place. Icon is a white tick on ENAM blue
- Tested at 390x844 (Today, Book, Company, Look up, Your lines); deployed and checked live 28 Oct ~16:22 IST; README screenshots retaken from the live link; DECISIONS design paragraph updated
