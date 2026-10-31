# Needs from you

## Done
- GitHub repo published (public): https://github.com/vedant-22/finn. Pushing new commits to `origin main` is fine.

## Optional
- **Old finn-ledger-next deployments (31 Oct).** The spec keeps only the 2 newest deployments on `finn-ledger-next`. After the round 7 fixes it has 4; deleting the older two was blocked by the session's permission check, so please remove them in the Vercel dashboard (project finn-ledger-next only; never the v2 to v5 projects).
- **Commit messages naming the design reference (29 Oct).** Two commits from early on 29 Oct name the reference in their messages: `2a3cba9` and `574d304`. The spec says not to rewrite history from here, so they are left for you to clean.
- **Stray Vercel project 'web' (optional cleanup).** A deploy run from the wrong folder on 28 Oct created an empty-ish project named `web` next to `finn-ledger`. It is behind Vercel login and harmless; delete it in the Vercel dashboard if you like. The live app is `finn-ledger`.
- **Gemini paid tier (optional).** The key in `.env` is on the free tier. `gemini-3.1-pro-preview` and `gemini-4-argon` return 429 (zero quota), so the "smart" step uses `gemini-3.5-flash`. If you enable billing, set `FINN_SMART_MODEL=gemini-3.1-pro-preview` in Vercel to try the stronger model on grading only. Free-tier daily limits are shared by everyone who opens the live link, so heavy use of live research on new tickers may hit 429s; cached companies are unaffected.
- **Email submission.** Send the covering note (docs/COVERING_NOTE.md) to assessment@enam.com with subject "ENAM - IIT screening - 2027", plus the AI build history export of this session.
- **Covering note signed** (Vedant Tiwari, IIT Kanpur, vedant22@iitk.ac.in).
