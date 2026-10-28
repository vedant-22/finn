# Progress

Next: regrade job (pid from `pgrep -f regrade.sh`) sleeps to 12:40 IST then rebuilds ledgers; log in data/regrade.log. When done: `git diff --stat web/public/data`, sanity-check a few ledgers, run evals/sample_grades.py, write evals/grades_review.md, redeploy (`npx vercel deploy --prod --yes`), refresh README screenshots, critic round 2, final checklist pass 2. If the log is empty and no process is running, restart: `nohup zsh pipeline/regrade.sh > data/regrade.log &`.

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
- "Your lines" sheet: grab handle, drag down to close (short drags snap back)
- Book: on equal kept share, more misses rank weaker
- Deployed and checked live 28 Oct ~12:20 IST
