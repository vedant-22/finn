# Final checklist

Against the brief's "What to submit", line by line. Pass 1 on 28 Oct, 10:15 IST; pass 2 on 28 Oct, 13:20 IST, after the regrade and redeploy.

| Brief asks for | Where | Pass 1 | Pass 2 |
|---|---|---|---|
| Mobile-first prototype, easy to try on a phone | https://finn-ledger.vercel.app (responsive web; `/`, push.json and company files return 200) | ok || ok: redeployed 28 Oct ~13:20 IST; Today, Book, Company, Look up checked live at 390x844 |
| The GitHub repository | https://github.com/vedant-22/finn (public) | ok || ok: public, pushed |
| AI build history | export this Claude Code session and attach it to the email (NEEDS_FROM_USER.md) | yours to do || yours to do |
| Short writeup in the covering email: what was built, decisions and tradeoffs, what was left out, where next | docs/COVERING_NOTE.md | ok, signed || ok: grade eval result added (17/20 after a second look on 31 Oct) |
| Email to assessment@enam.com, subject "ENAM - IIT screening - 2027" | NEEDS_FROM_USER.md | yours to do || yours to do |

From the build guidelines (section 10):

| Item | Where | Pass 1 | Pass 2 |
|---|---|---|---|
| README: two-line summary, screenshots, architecture, model routing and cost, run locally, evals, what was left out | README.md | ok; screenshots to refresh after regrade || ok: screenshots retaken from live; grade eval row added |
| Walkthrough script, about 2 minutes | docs/WALKTHROUGH_SCRIPT.md | ok || ok: beats still match the data (12 today, Cyient has a miss) |
| `.env`, `brief/`, secrets ignored | .gitignore | ok || ok: only .env.example tracked |

## Stage 4 passes (31 Oct, after promoting)

| Brief asks for | Pass 3 | Pass 4 |
|---|---|---|
| Mobile-first prototype, easy to try on a phone | ok: live serves stage 4; `/`, push.json, company files, manifest, service worker and icon return 200 | ok: flows.py 32/32 on the live link; sweep.py clean on all 22 company pages at 320 and 390 |
| The GitHub repository | **blocked: the repo is private** (`gh repo view` says PRIVATE; the link 404s logged out). Flagged at the top of NEEDS_FROM_USER | same: 404 logged out. Code is pushed and main matches origin |
| AI build history | yours to do | yours to do |
| Short writeup in the covering email | ok: leads with the point of view, then what the investor does, decisions, left out, next; grade eval 17/20; slop scan passes | ok: its app link returns 200; the repo link waits on the visibility change |
| Email to assessment@enam.com, subject "ENAM - IIT screening - 2027" | yours to do | yours to do |
| README (summary, shots, architecture, routing and cost, run locally, evals, left out) | ok: all sections; shots retaken from live on 31 Oct | ok: the three images it links are tracked |
| Walkthrough, about 2 minutes | ok: rewritten for the brief, about 2:15 | ok: taps match the live app (ASTRAL under Outside your book, FY27 guidance line) |
| Secrets and private folders out of git | ok: no .env, brief/, design-reference/, design/references/ or shots/ tracked | ok: no tracked file names the base design |
