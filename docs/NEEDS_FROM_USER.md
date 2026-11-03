# Needs from you

## Before you submit (3 Nov)
- **The GitHub repo is still private.** `gh repo view vedant-22/finn` reports PRIVATE on 3 Nov. The brief asks for the repository, so make it public (Settings, General, Danger zone, Change visibility) or add ENAM's reviewers before you send the email. I haven't touched it. You may have made it private on purpose.
- **Send the email.** The covering note in docs/COVERING_NOTE.md goes to assessment@enam.com with the subject "ENAM - IIT screening - 2027". It's signed and ready.
- **Attach the AI build history.** Export the Claude Code sessions. The note says they're attached.
- **Record the walkthrough if you want one.** docs/WALKTHROUGH_SCRIPT.md is up to date for the live screens.

## Done
- The final build is live at https://finn-ledger.vercel.app (3 Nov, tag `finn-v8-final`, local only). flows.py passed 40/40 on live. If it ever needs rolling back, the v7 copy is https://finn-ledger-v7.vercel.app.

## Optional
- **Old finn-ledger-next deployments.** The spec keeps only the 2 newest deployments on `finn-ledger-next`, and it has about 40. Deleting from here was blocked by the session's permission check, so remove the older ones in the Vercel dashboard (project finn-ledger-next only; never the v2 to v7 projects).
- **Commit messages naming the design reference (29 Oct).** Two early commits name the reference in their messages: `2a3cba9` and `574d304`. The spec says not to rewrite history from here, so they are yours to clean, and it matters more once the repo is public.
- **Stray Vercel project 'web'.** A deploy from the wrong folder on 28 Oct created a project named `web` next to `finn-ledger`. It's harmless. Delete it if you like.
- **Gemini paid tier.** The key in `.env` is on the free tier, so grading uses `gemini-3.5-flash`. If you enable billing, set `FINN_SMART_MODEL=gemini-3.1-pro-preview` in Vercel to try the stronger model on grading only. Free-tier daily limits are shared by everyone who opens the live link, so heavy live research on new tickers may hit 429s. Cached companies are fine.
