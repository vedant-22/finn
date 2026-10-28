# Needs from you

## Blocking: publish the GitHub repo
Creating a public repo was refused by the permission system in this unattended session, so the code is committed locally only. To publish, from the repo root:

```
gh repo create vedant-22/finn --public --source . --push --description "FINN: an investor agent that keeps management to its word"
```

`.env`, `brief/`, caches and `.vercel` are already in `.gitignore`; I checked the history for keys before committing. The README links to `https://github.com/vedant-22/finn`, so use that name or update the link.

## Optional
- **Gemini paid tier (optional).** The key in `.env` is on the free tier. `gemini-3.1-pro-preview` and `gemini-4-argon` return 429 (zero quota), so the "smart" step uses `gemini-3.5-flash`. If you enable billing, set `FINN_SMART_MODEL=gemini-3.1-pro-preview` in Vercel to try the stronger model on grading only. Free-tier daily limits are shared by everyone who opens the live link, so heavy use of live research on new tickers may hit 429s; cached companies are unaffected.
- **Email submission.** Send the covering note (docs/COVERING_NOTE.md) to assessment@enam.com with subject "ENAM - IIT screening - 2027", plus the AI build history export of this session.
- **Sign the covering note.** I left `[Your name]` at the bottom of docs/COVERING_NOTE.md rather than guess.
