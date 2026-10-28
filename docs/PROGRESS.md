# Progress

Next: regrade job started 10:06 IST via `nohup zsh pipeline/regrade.sh > data/regrade.log` (sleeps to 12:40 IST). If data/regrade.log is empty and no process (`pgrep -f regrade.sh`), restart it. After regrade: run evals/sample_grades.py, write evals/grades_review.md.

- [x] Brief analysis, company notes, ideation (docs/)
- [x] Engine: finn/ (sources, classify, triage, results, people, ledger, research)
- [x] Push snapshot: web/public/data/push.json (built 28 Oct 06:12 IST)
- [x] Ledgers for 18 holdings + DIXON, TITAN, PIDILITIND, POLYCAB
- [x] Frontend (Today, Book, Company, Look up, Your lines), DESIGN.md
- [x] Vercel API for live lookups; tested on ASTRAL in production
- [x] Evals: triage, results numbers, quote check (evals/)
- [x] Critic round 1 (evaluator+engineer, designer+user) and fixes
- [x] README, covering note, walkthrough script; slop_scan passes (walkthrough's long-sentence gate fails on purpose: it's spoken)
- [ ] Regrade ledgers with gemini-3.5-flash after the free quota resets (pipeline/regrade.sh, runs 12:40 IST, log in data/regrade.log)
- [ ] After regrade: refresh README screenshots, redeploy, critic round 2, final checklist x2
- [x] Publish GitHub repo: https://github.com/vedant-22/finn

## Polish log (28 Oct)
- Plain-English errors with Try again on live lookup (quota, network, timeout) and on boot; tested at 390x844 with a mocked 429
- Today says so when nothing crossed the lines
- Standard web-app-capable meta (console warning gone)
