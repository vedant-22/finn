# Needs from you

## Done
- GitHub repo published (public): https://github.com/vedant-22/finn. Pushing new commits to `origin main` is fine.

## Optional
- **Stray Vercel project 'web' (optional cleanup).** A deploy run from the wrong folder on 28 Oct created an empty-ish project named `web` next to `finn-ledger`. It is behind Vercel login and harmless; delete it in the Vercel dashboard if you like. The live app is `finn-ledger`.
- **Gemini paid tier (optional).** The key in `.env` is on the free tier. `gemini-3.1-pro-preview` and `gemini-4-argon` return 429 (zero quota), so the "smart" step uses `gemini-3.5-flash`. If you enable billing, set `FINN_SMART_MODEL=gemini-3.1-pro-preview` in Vercel to try the stronger model on grading only. Free-tier daily limits are shared by everyone who opens the live link, so heavy use of live research on new tickers may hit 429s; cached companies are unaffected.
- **Email submission.** Send the covering note (docs/COVERING_NOTE.md) to assessment@enam.com with subject "ENAM - IIT screening - 2027", plus the AI build history export of this session.
- **Covering note signed** (Vedant Tiwari, IIT Kanpur, vedant22@iitk.ac.in).
