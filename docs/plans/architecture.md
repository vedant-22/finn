# Plan: `architecture`

The brief's "Architecture, data security & privacy" section, one diagram, and the fixes that make it true.

## v1 (11 Nov)

### Why this raises the result
Architecture is one of the four things the brief grades and the only one with nothing written. The brief says "how you design FINN matters as much as what it shows" and asks for foundational decisions on pipelines, security and privacy, LLMs and agents, and cloud. A section that only describes boxes would score average. This one states one organising decision, proves the claims about today's system in code, and marks plainly what is not built.

### What I found (11 Nov, from the code and the live link)
1. `/api/grade` takes `src` and `calls` from the phone. `calls[-1].url` is fetched by the server (`ledger.grade` → `pdf.pages`) and the client's text goes into the strong model's prompt on the server's key. So `DECISIONS.md`'s "the API never fetches a URL the client sends" is false for this endpoint.
2. `finn/llm.py` sends the Gemini key as `?key=` in the URL. A connection error's text contains that URL, and `research.promises_for` and `webapi` pass error text to the client (`str(e)[:200]`).
3. No security headers on the live link beyond HSTS. Functions run in `iad1` while the edge answers from `bom1` (`x-vercel-id: bom1::iad1::`); `/api/network` takes 1.3 s.
4. finn-network has no `GEMINI_API_KEY`, so live reading fails there with a raw message. (User's to fix; listed in `NEEDS_FROM_USER.md`.)
5. True today and worth saying: `finn/network/*` imports only `re, json, math, datetime, pathlib, dataclasses` (no model, no HTTP); only `classify, explain, people, ledger, triage, research` call the model, and none of them imports `finn.network`; contacts carry no phone, email or notes; identity answers travel with the request and are never stored; no key-shaped string in git history; API responses are `no-store`.

### The organising decision: two planes
- **Public plane.** What companies publish: prices, filings, results, calls. The same for every investor. Fetched after the close, read by cheap models, checked by code, served as static files.
- **Private plane.** What belongs to one investor: who they know, when they last spoke, their lines, their answers. Matched and ranked by rules that can be tested. No model reads it.
- **One crossing, one way.** People named in filings flow into the private plane, where FINN decides whether the new CFO is the person you know. Nothing flows back.

Every section of the document hangs off this.

### A. `docs/ARCHITECTURE.md` (about 1,400 words plus tables; first person, plain sentences)
0. **In short** (under 170 words, written so the covering note can lift it) and the diagram.
1. **Data pipelines.** One table, a row a source (prices: NSE bhavcopy; filings: NSE announcements; results: NSE XBRL; fundamentals: screener tables and transcripts, NSE copy first; annual reports: links held, not read; profiles: synthetic): fetched from, refreshed when, stored as, keyed by. Then **how things are linked**: the symbol joins prices, filings and the ledger; the registry turns an employer's name into an organisation (group companies stay separate); identity joins a name in a filing to a contact (compatible name, independent evidence weighed by employer size, no contradiction → same / different / possible; "possible" is asked, never assumed). One worked example each of same, different and possible, taken from `network.json` and checked. Then refresh and failure: what is cached and for how long, what happens when NSE, a PDF or the model fails, how staleness is shown. Then what a real deployment changes (a scheduler; announcements every few minutes in market hours; a database in place of JSON files).
2. **Data security and privacy.** A data inventory table: each kind of personal data (the investor's career; contacts' names, how known, meeting dates; contacts' careers; people in filings; identity answers; lines and read state; question text), where it comes from, where it lives today, where it would live and for how long, whether a model sees it. Then the decisions: no model reads the network; one investor's network is theirs, even inside the firm; never in a shared cache; logs hold no names or questions; the demo file is public only because everyone in it is invented. Consent and profile sources: synthetic here; for real the investor's own export plus a licensed provider or the contact's consent, never scraping; India's DPDP Act as the frame (what a person or the law has made public sits outside it, the fact that you know someone does not); requests to see, correct or erase honoured through the firm. Minimisation: FINN stores the relationship, not the conversation. Access control for real: firm sign-in, row-level rules per investor, a key per investor, admin can't read networks. Inside information: the caution built today; for real the firm's restricted list and a log that the caution was shown.
3. **LLMs and agents.** The step table (step, model, calls, why, what code checks after). What a model never does: read a contact, produce a results number, show a quote that isn't on its page, pick who to call, answer a network question. Routing, caching, fallback, cost (measured figures from the README). The free tier's terms and why only public filings go to it. Agents: none plan or act on their own today, and why (same answer twice, errors traceable to a step, 20 strong calls a day). Where one would earn its place next (finding a transcript on a company's own site; open questions over a company's documents), with its limits (tools restricted to primary sources, bounded steps, quotes still page-checked, never the private plane).
4. **Cloud.** Today: static app and JSON at Vercel's edge, four stateless Python functions in Mumbai, Gemini's API, the batch build on a laptop after the close, settings on the phone. Why: free, one deploy, browsing never waits on a model. For real, a table: component, where, why (one India region; private plane in its own database with no route to a model provider; scheduler and queue; push; paid model terms; firm sign-in; cost meter).
5. **Threats considered.** A table: threat, what stops it, built or not (forged grade request; key leak; a filing that tries to instruct the model; wrong person matched; someone else reading a network; strangers spending the quota; inside information; stale data read as fresh; script injection).
6. **Not built.** One list.

### B. The diagram (`docs/img/architecture.svg`, and a PNG of it)
Hand-written SVG in FINN's own look, drawn tall for a phone (about 400 wide, text 11 px or more at 390). Three bands: public plane (sources → rules, cheap model, code checks, one strong call → static files), the boundary line ("nothing below this line goes to a model"), private plane (contacts, profiles → network engine → the investor's view), then the phone. One arrow crosses the line, downward: people named in filings.

### C. Fixes that make it true
- **H1 Model key and errors.** Key in the `x-goog-api-key` header. `LLMError` text comes from a fixed list (quota, no key, unavailable, bad response); upstream text goes to the server log only. API errors become `{error: code}`; `plainError` in `web/src/lib.ts` maps codes, including "live reading is off on this link" when there is no key.
- **H2 Sealed steps.** `finn/seal.py`: `seal(obj)` returns compressed JSON plus an HMAC; `unseal` verifies. `/api/sources` and `/api/call` return a seal beside the readable result; `/api/grade` reads only seals and ignores anything else. The key is `FINN_SEAL_KEY` or derived from the model key. The phone passes strings through untouched, so no canonical-JSON problem.
- **H3 Fetch guard** in `pdf.fetch`: http(s) only, no credentials, default ports, host must resolve to public addresses, redirects followed by hand (3 at most) and each hop checked.
- **H4 Request limits** in `webapi`: body size cap per endpoint (413), bad JSON and unknown op are 400, question capped at 300 characters.
- **H5 Headers** in `vercel.json`: CSP (`default-src 'self'`; inline styles allowed; `frame-ancestors 'none'`; `object-src 'none'`), nosniff, referrer policy, permissions policy (microphone for self only). The same headers on `vite preview` so the e2e run is under them.
- **H6 Functions in Mumbai** (`"regions": ["bom1"]`). Revert if `/api/sources` gets worse answers from NSE there.
- **H7 `evals/run_security.py`** (no model, no network): the network core imports nothing that can reach a model or the internet; no module that calls the model imports the network; a forged or altered seal is refused and its URL is never fetched; the fetch guard refuses loopback, link-local, private, `file:` and credentialed URLs and a redirect to one; no part of a key appears in any error; oversized and malformed bodies are refused.

### Verification
- `python3 evals/run_security.py` all pass; `evals/run_network.py` 225/225; `npm test` 27/27.
- `web/test/e2e/flows.py` on the local preview under the new headers: 40/40 and no console message naming Content Security Policy (new check). After deploy, the same on the live link.
- Live: `curl -I` shows the headers; `x-vercel-id` shows the function in `bom1`; a forged `/api/grade` body gets 400; `/api/network` still answers the four starter questions; time per call before and after.
- The live research path with a stub model in place of Gemini (sources → call → grade through the seals). With a real key only if the user has set one; otherwise it is listed as the one thing not checked end to end.
- The document: every claim about today cites a file or a test, and I re-read each against the code. The three worked identity examples match `network.json`. The diagram is rendered to PNG at 390 wide and read. The writing check (`~/ENAM-FINN/for_claude/slop_scan.py`) passes.
- 390×844 screenshots of Today and a company page before and after the headers: identical. https://finn-ledger.vercel.app serves the same asset as before.

### Files
New: `docs/ARCHITECTURE.md`, `docs/img/architecture.svg`, `docs/img/architecture.png`, `finn/seal.py`, `evals/run_security.py`, `evals/security_result.txt`.
Changed: `finn/llm.py`, `finn/webapi.py`, `finn/research.py`, `finn/sources/pdf.py`, `api/sources.py`, `api/call.py`, `api/grade.py`, `web/src/lib.ts`, `vercel.json`, `web/vite.config.ts`, `web/test/e2e/flows.py`, `evals/README.md`, `README.md` (the architecture section only: the diagram, five lines, a link), `docs/DECISIONS.md` (the two planes; sealed steps), `docs/NEEDS_FROM_USER.md`.

### Order (commit after each)
1. The document, sections 0 to 4, and the diagram. The required section exists even if the session stops here.
2. H1 and H4 with their checks. 3. H2 and H3 with their checks and the client change. 4. H5 and H6, e2e under headers. 5. Deploy, live checks. 6. Sections 5 and 6 from what was actually built; README, DECISIONS, evals README. 7. Roadmap and STAGE.

### Not in this task
The covering note's short version (task `writeup` lifts section 0). Anything in the app about privacy (task `trust`). Sign-in, a database, a scheduler: described, not built.

## Round 1 critiques of v1 (11 Nov), each 7/10
- **Grader.** (1) A false claim: `network.json` names real executives from NSE filings, ties them to invented contacts, and 5 of the 7 profiles add invented years to real people; the label says "the people ... are not [real]". (2) The doc would be false at its first commit (Mumbai before H6). (3) H3 is overbuilt; use a host allow-list. (4) The threats, "for real" and "not built" sections overlap; aim for about 1,000 words. (5) The profiles row is thin: how they were made; what a LinkedIn export does and doesn't hold; refresh; retention in months. Also wanted: exact model IDs, measured cost per step, the free tier's data terms, and an "In short" with one sentence per bullet.
- **Investor and designer.** (1) It reads like a compliance pack. Keep what only FINN could write: worked identity examples, what a model never does, why no agents. Fold the rest. (2) The holdings leak: the model is asked about the book's filings only, so the free tier can infer the book. (3) The CSP blocks the inlined `data:` rupee font. (4) Under-verified: no number decides the region move, seal size vs body caps, `FINN_SEAL_KEY`, phones running the old client. (5) Diagram: system fonts, a solid background, 10 labels at most; plain names, "What the market publishes" and "What only you know".
- **Staff engineer and security.** (1) Critical: the seal key "derived from the model key" is a public constant when there's no key, and `ledger.grade` fetches before any key check. (2) A partial set of seals silently changes which call is "latest"; bind seals to kind, symbol, period, asof and iat; MAC over the compressed bytes, `compare_digest` before decompressing. (3) Quota abuse: seals can be replayed and `/api/call` takes any symbol; say "capped", not "prevented"; the key's project must have no billing. (4) H3: an allow-list would drop about 20% of real transcript URLs, which are on company sites; `requests` resolves again at connect time (rebinding); stream with a byte cap, cap zip members, a total deadline, `FetchError` text from a fixed list. (5) CSP: `font-src 'self' data:`, `base-uri`, `form-action`; try `style-src 'self'`. (6) The region move can fail silently (`research.sources` swallows NSE errors); decide it by counting NSE transcripts. (7) The threat table over-claims: the read, questions, bull and bear are unchecked model text; log scrubbing is untested; `/api/network` doesn't cap `decisions`.
- **Conflict resolved.** Allow-list or public addresses: public addresses, enforced at connect time. That covers redirects and rebinding without dropping company-site transcripts.

## v2 (11 Nov)

### The organising decision, named plainly
Two sides. **What the market publishes:** prices, filings, results, calls, and people named in filings. The same for every investor, and models may read it. For real, it's computed for the whole market, never for one book, so what a model reads says nothing about what anyone holds. **What only you know:** your holdings, your network, your answers, your questions, your lines. No model reads it. **One crossing, downward:** people named in filings meet your contacts on your side, never the reverse. Today's build reads only the demo book's filings. That's harmless because the book is invented, and the doc says so plainly.

### A. `docs/ARCHITECTURE.md`: at most 1,000 words outside `<details>` folds; first person, plain
Rule: every sentence about today is true at the commit that adds it. A claim about a fix lands in the same commit as the fix and names its test.
0. **In short** (170 words at most): one sentence on the two sides, then one per brief bullet, so the covering note can lift it whole. Then the diagram.
1. **Data pipelines.** Four sentences, then one table: source, fetched from, refreshed, stored as, keyed by, and for real. Prices come from the NSE bhavcopy; filings from NSE announcements; results from NSE XBRL; fundamentals and transcripts from NSE first, then screener; annual reports are links held, not read. Profiles row: 43 invented contacts; 7 invented profiles, 2 of them decoys sharing a filing person's name and correctly left unattached. For real: a LinkedIn export gives name, company, position and connection date, with no history or education. So careers come from the contact's consent or a licensed provider under its terms, never scraping. Profiles refresh monthly, and matching re-runs when a filing or profile changes someone's employer. **Linking:** the symbol joins prices, filings and ledger; the registry turns an employer name into an organisation, keeping group companies apart; identity calls a name same, different or possible, and "possible" is asked, never assumed. A fold holds one worked example of each, checked against `network.json`, plus how staleness and failures are shown.
2. **Security and privacy.** Lead with a two-column table, **"A model sees" and "No model ever sees"**, each with a today line and a for-real line, holdings included. The next paragraph says what's real and what's invented. Real: the people named in filings, as their company filed them under a legal duty, which falls outside the DPDP Act under s.3(c)(ii). Invented: the investor, contacts, ties, and the years in the 7 profiles. Then consent and access for real, in 5 lines. Folds:
   - **Data inventory:** item, source, where today, where for real, retention in months, model sees y/n.
   - **Threats:** at most 7 rows, each stopped, capped or unchecked, with its test. Forged grade; server made to fetch an internal address; key leak; strangers spending the quota (capped); a filing that instructs the model (bounded: schema, page-checked quotes, code-made numbers; the read, questions, bull and bear are unchecked model text); wrong person matched (0 false matches in 84 adversarial namesakes); someone else reading a network.
3. **LLMs and agents.** A step table: step, exact model ID, calls, measured cost, what code checks after. What a model never does. The free tier's terms (unpaid prompts may be used by the provider), which is why only public filings go there; for real, paid terms. Agents: none today, and why; where one would earn its place; its limits.
4. **Cloud.** A today table (what, where, why), then for real in 5 lines. There's no separate "not built" section: it's folded into the for-real columns.

Function log retention on the Hobby plan is verified from Vercel's docs before it's stated.

### B. Diagram (`docs/img/architecture.svg` + 2× PNG)
- 400 wide, solid background, a system font stack, at most 10 labels.
- Two tinted fields with one hairline between them, labelled "No model below this line". The model mark appears only above it.
- One arrow down, "people named in filings"; the phone at the bottom.
- Rendered to PNG with Playwright and read at 390.

### C. Fixes
- **P0 Provenance.** Correct the label in `data/network/investor.json`, then rebuild `network.json`. Then:
  - In `web/src/Network.tsx` (`Synthetic`, `NetSyntheticNote`), one short line: "Demo network: you, your contacts and how you know people are invented; people named in filings are real."
  - `X-Robots-Tag: noindex` on `/data/*`.
  - 390 check.
- **H1 Key and error text.**
  - The key goes in the `x-goog-api-key` header.
  - `LLMError` and `FetchError` carry fixed codes: `no_key`, `quota`, `unavailable`, `bad_response`, `unreachable`, `not_pdf`, `too_large`. Upstream detail goes to the server log only.
  - `webapi` returns `{error: code}`, and `plainError` maps each code, including `live_off`: "Live reading is off on this link."
  - `/api/network` logs the exception type and frames, never its message.
- **H2 Sealed steps.**
  - **Key:** HMAC-SHA256(`FINN_SEAL_KEY` or `GEMINI_API_KEY`, "finn-seal-v1"). If neither is set, nothing is sealed and grade answers `live_off` before any fetch.
  - **Format:** `b64(zlib(json)).b64(mac)`, with the MAC over the compressed bytes, checked with `compare_digest` before decompressing. Decompressed size is capped at 2 MB. The header carries kind, symbol, period, asof and iat.
  - **Who seals:** `/api/sources` returns `src_seal`, which includes the transcript list. `/api/call` returns `call_seal`. `/api/grade` takes only `{src_seal, call_seals}`.
  - **Grade:** the latest period and its URL come from the sealed src; call seals only supply older promises. It refuses mixed symbols, duplicate periods, more than 6 seals, or an iat older than 6 h. A missing call shows as "not read".
  - **Old clients:** a grade request with no seals gets 409 `update`, and the client reloads once. The service worker already uses `skipWaiting` and `clients.claim`.
- **H3 Fetch guard at connect time.** New `finn/netguard.py`, installed by `webapi` (server only; the batch build is untouched):
  - It replaces urllib3's `create_connection`: resolve, refuse any address that isn't global (loopback, private, link-local, CGNAT, multicast, reserved, IPv4-mapped IPv6), and connect to the vetted address. Every hop and any rebinding is covered.
  - In `pdf.fetch`: http(s) only, default ports, no userinfo, 3 redirects at most, streamed with a 40 MB cap, a cap on zip member size, and a 45 s total deadline.
- **H4 Limits.**
  - Body caps: sources and call 2 KB, network 64 KB, grade set to twice the largest measured five-call run.
  - Bad JSON or an unknown op gets 400.
  - Questions are capped at 300 characters, `decisions` at 200 entries.
  - A per-IP, per-instance limiter on call and grade returns 429 `busy`. It slows abuse but doesn't stop it, and the doc says so.
- **H5 Headers** in `vercel.json`, and the same on `vite preview`:
  - CSP: `default-src 'self'; script-src 'self'; style-src 'self'` (`'unsafe-inline'` only if e2e shows a block), `img-src 'self' data:; font-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
  - Also: `nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: microphone=(self), camera=(), geolocation=()`.
- **H6 Region `bom1`, decided by numbers.** For 3 symbols, before and after: transcripts sourced from NSE, and the median `/api/sources` time over 3 runs. Keep it only if the counts are equal and time is no more than 20% worse. Otherwise revert, and the doc says why.
- **H7 `evals/run_security.py`.** No model and no network: the resolver and transport are injected. Cases:
  - The network core's imports, and model modules not importing the network.
  - Seals: forged, altered, expired, partial, mixed-symbol, too many, no key. In each, the URL is never fetched (`create_connection` raises).
  - The guard: loopback, private, link-local, IPv4-mapped, `file:`, credentialed URLs, a redirect to 127.0.0.1, rebinding (public, then private).
  - A zip bomb and an oversized body.
  - No part of a key appears in any error.
  - Oversized and malformed bodies are refused; `decisions` is capped.
  - A question's text never appears in captured logs.

### Verification (numbers that decide)
- `run_security.py` all pass; `run_network.py` 225/225; `npm test` 27/27.
- `flows.py` on the local preview under the headers:
  - 40/40, and zero console messages mentioning Content Security Policy.
  - The rupee font face reports `loaded`.
  - `compare.py` shows no pixel change on Today and a company page before and after.
- The research path end to end locally with a stubbed model, through the seals. The largest seal sizes are recorded there and set the grade cap.
- Live:
  - `curl -I` shows the headers; `x-vercel-id` shows the region.
  - A forged grade gets 400 and a grade with no seals gets 409.
  - `/api/network` gives the four starter questions the same answers as before.
  - With no key, a non-prebuilt company shows the `live_off` sentence.
  - https://finn-ledger.vercel.app is unchanged.
- The document:
  - Every "today" claim cites a file or a test.
  - At most 1,000 words outside folds (counted).
  - `slop_scan.py` passes.
  - The PNG is read at 390.

### Order (each commit leaves the doc true)
1. P0, H1 and H4, with their checks.
2. The document and diagram, true to that commit; seals, guard, headers and region appear as "not yet" lines.
3. H2, H3 and the client change; doc lines updated.
4. H5 and H6, measured; e2e.
5. Deploy and live checks. Then:
   - final doc lines and the README architecture section;
   - DECISIONS (the two sides, sealed steps);
   - the evals README;
   - NEEDS_FROM_USER: the key's Cloud project must have no billing; an optional firewall rate rule; the model key.
6. ROADMAP and STAGE.

Cut line: once step 2 is committed, the required section exists. H6 is the first thing to drop.

### Files
- **New:** `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`, `finn/seal.py`, `finn/netguard.py`, `evals/run_security.py`, `evals/security_result.txt`.
- **Changed:**
  - `data/network/investor.json`, `web/public/data/network.json`, `web/src/Network.tsx`
  - `finn/llm.py`, `finn/webapi.py`, `finn/research.py`, `finn/ledger.py`, `finn/sources/pdf.py`
  - `api/*.py`
  - `web/src/lib.ts`
  - `vercel.json`, `web/vite.config.ts`
  - `web/test/e2e/flows.py`
  - `evals/README.md`, `README.md`, `docs/DECISIONS.md`, `docs/NEEDS_FROM_USER.md`

## Round 2 critiques of v2 (11 Nov)
- **Grader, 8/10.** (1) The live link lags the doc: deploy after step 1 and after every step that changes a "today" claim. (2) Seals are now the overbuild. The server can list the URLs itself, and abuse is capped elsewhere, so seals cost a module, a client change and a 409 path for little. (3) The efficiency bonus slipped: name routing, caching and chunking, plus one whole-market cost line. A 10 needs real executives to carry only filed facts.
- **Investor and designer, 8.5/10.** (1) Pull still reveals interest: for real, read every company with a call on a schedule and cache for everyone. (2) The P0 line reads as "you are invented" and overclaims; suggested: "your contacts and their ties are invented; names from filings are real". (3) "In short" mirrors the brief's list; open with one idea. (4) Seal expiry must never surface to the user. (5) Hedge the DPDP reading. Also: real executives should get only filed facts.
- **Staff engineer and security, 8.5/10.** (1) A regression: taking the latest URL from the sealed src grades the NSE cover letter where today the screener alternate is used, and it drops the rule that the newest good call is the latest. (2) The 409 path can't reload old clients: they show `error` as text. (3) H3's exact hook is `urllib3.util.connection.create_connection` (urllib3 2.x calls it through the module; patching `urllib3.connection` does nothing). Resolve IPv4 only, since `::127.0.0.1` reports `is_global` in 3.12; pass the IP literal to the original; pin urllib3; `trust_env=False`; redirects by hand. (4) `/api/call` downloads PDFs before finding there's no key; answer `live_off` first, and have `/api/sources` say `live:false`. (5) Measure the grade cap on a six-call run.

### Decisions on round 2
- **Seals are cut.** The grader is right on judgment. A grade request's answer goes only back to whoever sent it. So the server needs to control what it fetches and what it spends, not whether the phone is telling the truth about itself. With the URL listed by the server, the guard at connect time, a key check first, caps and a key with no billing, seals add a key to manage, expiry, an old-client path and size limits, and protect no one. This also clears security's issues 1, 2 and 5, and the designer's issue 4: the request contract doesn't change, so old clients keep working. The doc states the reasoning: it's the kind of call the brief grades.
- **Real executives carrying only filed facts is deferred to `network-loop`.** The 5 attached profiles give real executives full careers with invented years, and they feed the identity and path checks (225). Changing them means rebuilding and re-verifying the network, and that task already does both. Here, the label, the app line and the doc say it exactly. A roadmap line records the follow-up.

## v3 (11 Nov)

### The idea the document opens with
Two sides. **What the market publishes:** prices, filings, results, calls, people named in filings. The same for everyone; models may read it. For real, it's computed for the whole market on a schedule and cached for everyone, so what a model reads says nothing about what any investor holds or looks at. **What only you know:** your holdings, your network, your answers, your questions, your lines. No model reads it. **One crossing, downward:** people named in filings meet your contacts on your side, never the reverse. The other decision follows from it: the server trusts only what it fetched itself.

### A. `docs/ARCHITECTURE.md`: at most 1,000 words outside `<details>` folds; first person, plain
Rule: every sentence about today is true at the commit that adds it, and the live link is redeployed whenever a "today" claim changes. A claim about a fix lands with the fix and names its test.

0. **In short** (170 words at most):
   - It opens with the two sides in 2 or 3 sentences and doesn't mirror the brief.
   - Then 4 labelled lines (pipelines, privacy, models, cloud), so the covering note can lift it whole.
   - Then the diagram.

1. **Data pipelines.** Four sentences, then one table: source, fetched from, refreshed, stored as, keyed by, for real.
   - **Sources:**
     - prices: NSE bhavcopy
     - filings: NSE announcements
     - results: NSE XBRL
     - fundamentals and transcripts: NSE first, then screener
     - annual reports: links held, not read
   - **Profiles row:**
     - Today: 43 invented contacts and 7 synthetic profiles. Five of them attach to real people named in filings: employers and roles from the filing, years invented, marked in the file. Two are decoys and correctly stay unattached.
     - For real: a LinkedIn export gives name, company, position and connection date only. Careers come from the contact's consent or a licensed provider under its terms; never scraping. Profiles refresh monthly, and matching re-runs when an employer changes.
   - **Linking:** symbol, registry, identity (same, different or possible; "possible" is asked).
   - **Fold:** one worked example of each, checked against `network.json`, plus how staleness and failures show.
   - **For real:** every company with a call is read after it files, on a schedule, and cached for everyone. On-demand reads cover misses only.

2. **Security and privacy.**
   - **Lead table: "A model sees" / "No model ever sees"**, with a today line and a for-real line, holdings included.
   - **What's real, what's invented:** people named in filings, as their company filed them under a legal duty. I read DPDP s.3(c)(ii) as placing that outside the Act. That a given investor knows them is not. Invented: the investor, contacts, ties, and the years in the 7 profiles.
   - **The server trusts only what it fetched itself:** the one design rule for the live endpoints, with the reasoning above in two sentences.
   - **Consent and access for real:** 5 lines.
   - **Folds:**
     - data inventory, with retention in months, verified;
     - threats, at most 7 rows, each stopped, capped or unchecked, with its test. The read, questions, bull and bear count as unchecked model text.

3. **LLMs and agents.**
   - **Step table:** step, exact model ID, calls, measured cost, what code checks after.
   - **Efficiency, named:** routing (flash-lite for bulk, flash once per company), caching (prompt-keyed disk cache; built files served static), chunking (first 6 pages to find a transcript, the call cut to its pages).
   - **One whole-market cost line**, computed from the measured per-call and per-filing figures: announcements a day × classify cost, plus companies × calls a year × read cost.
   - **What a model never does.**
   - **The free tier's terms** (unpaid prompts may be used by the provider), so only public filings go there; for real, paid terms.
   - **Agents:** none today, and why; where one would earn its place; its limits.

4. **Cloud.** A today table (what, where, why), then for real in 5 lines. Not-built items sit in the for-real columns.

### B. Diagram (`docs/img/architecture.svg` + 2× PNG)
- 400 wide, solid background, a system font stack, at most 10 labels.
- Two tinted fields with a hairline labelled "No model below this line"; the model mark only above it.
- One arrow down, "people named in filings"; the phone at the bottom.
- Rendered with Playwright and read at 390.

### C. Changes
- **P0 Provenance.**
  - The label in `data/network/investor.json` says exactly what is real and what is invented. Then rebuild `web/public/data/network.json` with the existing build step; the executor finds the writer and must not change anything else in the file.
  - `web/src/Network.tsx` (`Synthetic`, `NetSyntheticNote`): "Demo network: your contacts, their ties and any career years are invented. Names and roles from filings are real."
  - `X-Robots-Tag: noindex` on `/data/*`.
  - 390 check.
- **H1 Key, errors, key first.**
  - The key goes in the `x-goog-api-key` header.
  - `LLMError` and `FetchError` carry fixed codes: `no_key`, `quota`, `unavailable`, `bad_response`, `unreachable`, `not_pdf`, `too_large`. Upstream detail goes to the server log only.
  - `webapi` answers `{error: code}`. `plainError` maps each code, including `live_off`: "Live reading is off on this link. The 22 companies already read still open."
  - `/api/call` and `/api/grade` check for the key before any fetch.
  - `/api/sources` returns `live: false` without a key, and the client stops before the calls with that sentence.
  - `/api/network` logs the exception type and frames, never its message.
- **H2 Grade trusts only what the server lists.**
  - The request contract is unchanged, so old clients work.
  - The symbol comes from `src.symbol`, cleaned the same way as `/api/call`. The server runs `research.sources(sym)` itself (no model) and uses its own name, basis, asof, quarters and `numbers_text`.
  - A client call is kept only if its period is in the server's transcript list and its `url` is one of that period's `urls`.
  - Latest is the newest good call, as today. An empty server list answers `unavailable`.
  - Shape caps: 6 calls at most, 40 promises per call, 600 characters per field.
  - The promise text from the phone is shape-checked only. A forged list misleads only its sender. Evidence quotes are still checked against the page the server fetched itself, and cost is capped.
  - For real, grading runs as a server job and the phone never carries intermediate steps.
- **H3 Connect-time guard, `finn/netguard.py`, installed by `webapi`** (server only; the batch build is untouched):
  - It replaces `urllib3.util.connection.create_connection`: resolve with `AF_INET` only, refuse any address that isn't `is_global`, and call the original with the IP literal (keeping the timeout and socket options). TLS still verifies the hostname.
  - Pin `urllib3` in `requirements.txt` to the 2.x version that's installed.
  - `pdf.fetch` uses its own Session with `trust_env=False`, and follows redirects by hand (3 at most). Each hop must be http(s), on a default port, with no userinfo.
  - Streamed with a 40 MB cap, a cap on zip member size, and a 45 s total deadline.
- **H4 Limits.**
  - Body caps: sources and call 2 KB, network 64 KB, grade twice the largest measured six-call body.
  - Bad JSON or an unknown op gets 400.
  - Questions are capped at 300 characters, `decisions` at 200 entries.
  - A per-IP, per-instance limiter on call and grade returns 429 `busy`. It slows abuse but doesn't stop it, and the doc says so.
- **H5 Headers** in `vercel.json`, and the same on `vite preview`:
  - CSP: `default-src 'self'; script-src 'self'; style-src 'self'` (`'unsafe-inline'` only if e2e shows a block), `img-src 'self' data:; font-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
  - Also: `nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: microphone=(self), camera=(), geolocation=()` (Ask has voice input).
- **H6 Region `bom1`, decided by numbers.**
  - For 3 symbols, before and after: transcripts from NSE, and the median `/api/sources` time over 3 runs.
  - Keep it only if the counts are equal and time is no more than 20% worse. Otherwise revert, and the doc says why.
- **H7 `evals/run_security.py`.** No model and no network: the resolver and transport are injected, and every guard test goes through `requests.get`. Cases:
  - The network core's imports, and model modules not importing the network.
  - Grade: an unlisted URL, a foreign period, a mixed symbol and an oversized list are all dropped or refused, and never fetched (`create_connection` raises).
  - Grade and call with no key answer `live_off` before any fetch.
  - The guard: loopback, private, link-local, `::127.0.0.1`, `file:`, credentialed URLs and odd ports; a redirect hop to 127.0.0.1; rebinding (public, then private).
  - `urllib3.connection.connection is urllib3.util.connection`.
  - A zip bomb and an oversized stream.
  - No part of a key appears in any error.
  - Malformed and oversized bodies are refused; `decisions` is capped.
  - A question's text never appears in captured logs.

### Verification (numbers that decide)
- `run_security.py` all pass; `run_network.py` 225/225; `npm test` 27/27.
- `flows.py` on the local preview under the headers:
  - 40/40, and zero console messages mentioning Content Security Policy.
  - The rupee font face reports `loaded`.
  - `compare.py` shows no pixel change on Today and a company page, apart from the P0 line.
- The research path end to end locally with a stubbed model. The largest six-call body is recorded there and sets the grade cap.
- Live, after each deploy:
  - `curl -I` shows the headers; `x-vercel-id` shows the region.
  - A grade with a foreign URL fetches nothing and grades no such call.
  - `/api/network` gives the four starter questions the same answers as before.
  - With no key, a non-prebuilt company shows the `live_off` sentence within 2 s, with no PDF fetched.
  - https://finn-ledger.vercel.app is unchanged.
- The document:
  - Every "today" claim cites a file or a test.
  - At most 1,000 words outside folds (counted).
  - `slop_scan.py` passes.
  - The PNG is read at 390.
  - Vercel's Hobby log retention is checked in the docs before it's stated.

### Order (each step committed; deployed where marked)
1. P0, H1 and H4, with their checks. Deploy.
2. The document and diagram, true to that commit; the guard, grade rule, headers and region appear as "not yet" lines.
3. H2, H3 and `requirements.txt`; doc lines updated. Deploy.
4. H5 and H6, measured; e2e. Deploy.
5. Live checks, then:
   - final doc lines and the README architecture section;
   - DECISIONS (the two sides; the server trusts only what it fetched);
   - the evals README;
   - NEEDS_FROM_USER: the key's Cloud project must have no billing; an optional firewall rate rule; the model key.
6. ROADMAP (done, plus the `network-loop` line on filed facts only) and STAGE.

Cut line: once step 2 is committed, the required section exists. H6 is the first thing to drop.

### Files
- **New:** `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`, `finn/netguard.py`, `evals/run_security.py`, `evals/security_result.txt`.
- **Changed:**
  - `data/network/investor.json`, `web/public/data/network.json`, `web/src/Network.tsx`
  - `finn/llm.py`, `finn/webapi.py`, `finn/research.py`, `finn/sources/pdf.py`
  - `api/*.py`
  - `web/src/lib.ts`
  - `requirements.txt`, `vercel.json`, `web/vite.config.ts`
  - `web/test/e2e/flows.py`
  - `evals/README.md`, `README.md`, `docs/DECISIONS.md`, `docs/NEEDS_FROM_USER.md`, `docs/ROADMAP.md`

## Round 3 critiques of v3 (11 Nov): 9, 9, 9
- **Grader.** The deferral is acceptable. One part can't wait: invented profile years reach the screen. A path sentence in `network.json` gives HDFC Bank's real incoming CEO an invented 2011–2016 stint, far from any banner. Hide years that come from a synthetic profile. Restore the full privacy folds (inventory columns; the threat row "someone else reading a network"; a for-real line saying networks are stored apart and never joined, staff access logged). Otherwise none substantial.
- **Staff engineer and security.** Accepts the seal cut: no shared state is keyed by client text, and seals wouldn't stop quota or compute abuse. Remaining: (1) re-deriving sources in grade isn't deterministic; match URLs against the whole merged list, take the period from the server, report `nse_ok`, retry NSE once. (2) The per-instance limiter doesn't protect the compute allowance; the firewall rate rule should be required. (3) The guard tests go through `pdf.fetch`, and the original `create_connection` is looked up at call time.
- **Investor and designer.** (1) `noindex` alone doesn't keep real names out of search, because rendering can still use the data; add `robots.txt`. (2) The opening idea contradicts on-demand reads; say "who holds or looks at what", and read misses with no user identity into the shared cache. (3) The `live_off` sentence: drop "on this link", and take the count from `companies.json`. Checked: every employer, role and school in the 5 profiles appears in its filing.
- **Decision.** Each item is a concrete fix with no design change, so all are adopted below as written and there is no round 4. The firewall rule is set in the Vercel dashboard, outside this worktree, so it becomes a required item in NEEDS_FROM_USER. The doc states the bound until then: once the model's daily quota is gone, grade fails fast.

## FINAL (v4, 11 Nov)

The goal: the brief's "Architecture, data security & privacy" section, one diagram, and the changes that make every claim in it true on the live link.

### The idea the document opens with
- **Two sides. What the market publishes:**
  - prices, filings, results, calls, and people named in filings;
  - the same for everyone, and models may read it;
  - for real, computed for the whole market on a schedule and cached for everyone. A company nobody has read yet is read with no user identity attached and added to the shared cache, so what a model reads says nothing about who holds or looks at what.
- **What only you know:** your holdings, network, answers, questions and lines. No model reads it.
- **One crossing, downward:** people named in filings meet your contacts on your side, never the reverse.
- **What follows:** the server trusts only what it fetched itself.

### A. `docs/ARCHITECTURE.md`: at most 1,000 words outside `<details>` folds; first person, plain
Every sentence about today is true at the commit that adds it, and the live link is redeployed whenever a "today" claim changes. A claim about a change lands with the change and names its test.

0. **In short** (170 words at most):
   - The two sides in 2 or 3 sentences.
   - Four labelled lines: pipelines, privacy, models, cloud.
   - The diagram.

1. **Data pipelines.** Four sentences, then one table: source, fetched from, refreshed, stored as, keyed by, for real.
   - **Sources:**
     - prices: NSE bhavcopy
     - filings: NSE announcements
     - results: NSE XBRL
     - fundamentals and transcripts: NSE first, then screener
     - annual reports: links held, not read
   - **Profiles row:**
     - Today: 43 invented contacts and 7 synthetic profiles. Five attach to real people named in filings: employers, roles and schools as their filing states them, years invented and never shown. Two are decoys and correctly stay unattached.
     - For real: a LinkedIn export gives name, company, position and connection date only. Careers come from the contact's consent or a licensed provider under its terms, never scraping. Profiles refresh monthly, and matching re-runs when an employer changes.
   - **Linking:** the symbol joins prices, filings and ledger; the registry turns an employer name into an organisation, keeping group companies apart; identity calls a name same, different or possible, and "possible" is asked, never assumed.
   - **Fold:** one worked example of each, checked against `network.json`, plus how staleness and failures show.
   - **For real:** scheduled reads of every company that files a call.

2. **Security and privacy.**
   - **Lead table: "A model sees" / "No model ever sees"**, with a today line and a for-real line, holdings included.
   - **What's real, what's invented:** people named in filings appear as their company filed them under a legal duty. I read DPDP s.3(c)(ii) as placing that outside the Act; the fact that a given investor knows them is not. Invented: the investor, contacts, ties and the profile years.
   - **Why the demo file is public today:** `network.json` is public only because its people on your side and every tie are invented. `robots.txt` and `noindex` keep it out of search.
   - **The server trusts only what it fetched itself:** two sentences on why seals were cut.
   - **For real:**
     - each investor's network is stored separately and never joined with another's, including by the firm;
     - staff access is logged;
     - firm sign-in;
     - consent and requests to see, correct or erase.
   - **Folds:**
     - Data inventory: item, source, where today, where for real, retention in months, model sees y/n. Covers the investor's career; contacts' names, how known, meetings; contacts' careers; people in filings; identity answers; lines and read state; question text; server logs (Hobby retention checked in Vercel's docs).
     - Threats, at most 8 rows, each stopped, capped or unchecked, with its test: forged grade; server made to fetch an internal address; key leak; strangers spending quota or compute (capped by the daily quota and the limiter; the firewall rule is the user's step); a filing that instructs the model (bounded; the read, questions, bull and bear are unchecked model text); wrong person matched (0 false matches in 84 adversarial namesakes); someone else reading a network; real names in search.

3. **LLMs and agents.**
   - **Step table:** step, exact model ID, calls, measured cost, what code checks after.
   - **Efficiency, named:** routing (flash-lite for bulk, flash once per company), caching (prompt-keyed disk cache; built files served static), chunking (first 6 pages to find a transcript; the call cut to its pages).
   - **One whole-market cost line**, from measured figures: announcements a day × classify cost, plus companies × calls a year × read cost.
   - **What a model never does.**
   - **The free tier's terms** (unpaid prompts may be used by the provider), so only public filings go there; for real, paid terms.
   - **Agents:** none today, and why; where one would earn its place; its limits.

4. **Cloud.** A today table (what, where, why), then for real in 5 lines. Not-built items sit in the for-real columns.

### B. Diagram (`docs/img/architecture.svg` + 2× PNG)
- 400 wide, solid background, a system font stack, at most 10 labels.
- Two tinted fields with a hairline labelled "No model below this line"; the model mark only above it.
- One arrow down, "people named in filings"; the phone at the bottom.
- Rendered with Playwright and read at 390.

### C. Changes
- **P0 Provenance.**
  - **(a)** The label in `data/network/investor.json` says exactly what's real and what's invented.
  - **(b)** No year that comes from a synthetic profile reaches any screen or API answer. In the `finn/network` sentence renderer (paths, reach lines), drop the year span when it comes from a profile. Rebuild `web/public/data/network.json` with the existing build, on the same 28 Oct inputs. `run_network.py` stays 225/225; update only expectations that quote those years, and list each in the commit.
  - **(c)** `web/src/Network.tsx` (`Synthetic`, `NetSyntheticNote`): "Demo network: your contacts and their ties are invented. Names and roles from filings are real."
  - **(d)** `web/public/robots.txt` with `Disallow: /data/` and `Disallow: /api/`; `X-Robots-Tag: noindex` on `/data/*`.
  - **Check:** for each of the 5 profile people, none of their profile's years appears in `network.json` or in the `/api/network` answers to the starter questions (an assertion in `run_security.py`). Then 390.
- **H1 Key, errors, key first.**
  - The key goes in the `x-goog-api-key` header.
  - `LLMError` and `FetchError` carry fixed codes: `no_key`, `quota`, `unavailable`, `bad_response`, `unreachable`, `not_pdf`, `too_large`. Upstream detail goes to the server log only.
  - `webapi` answers `{error: code}`. `plainError` maps each code. `live_off` reads: "Reading new companies is off for now. The N already in FINN still open.", with N from `companies.json`.
  - `/api/call` and `/api/grade` check for the key before any fetch.
  - `/api/sources` returns `live: false` without a key, and the client stops before the calls with that sentence.
  - `/api/network` logs the exception type and frames, never its message.
- **H2 Grade trusts only what the server lists.**
  - The request contract is unchanged, so old clients work.
  - The symbol comes from `src.symbol`, cleaned as in `/api/call`. The server runs `research.sources(sym)` itself (no model) and uses its own name, basis, asof, quarters and `numbers_text`.
  - `sources` reports `nse_ok`. If NSE failed inside grade, retry it once.
  - A client call is kept only if its `url` matches some URL anywhere in the server's merged transcript list, before the 6-call cut. Its period is taken from the server's entry.
  - Latest is the newest good call, as today. An empty server list answers `unavailable`.
  - Shape caps: 6 calls at most, 40 promises per call, 600 characters per field.
  - The promise text from the phone is shape-checked only. A forged list misleads only its sender. Evidence quotes are still checked against the page the server fetched itself, and nothing shared is keyed by client text.
  - For real, grading runs as a server job and the phone never carries intermediate steps.
- **H3 Connect-time guard, `finn/netguard.py`, installed by `webapi`** (server only; the batch build is untouched):
  - It replaces `urllib3.util.connection.create_connection`: resolve with `AF_INET` only, refuse any address that isn't `is_global`, and call the original with the IP literal (keeping the timeout and socket options). The original is held as a module attribute and looked up at call time, so tests can swap it. TLS still verifies the hostname.
  - Pin `urllib3` in `requirements.txt` to the 2.x version installed.
  - `pdf.fetch` uses its own Session with `trust_env=False`, and follows redirects by hand (3 at most). Each hop must be http(s), on a default port, with no userinfo.
  - Streamed with a 40 MB cap, a cap on zip member size, and a 45 s total deadline.
- **H4 Limits.**
  - Body caps: sources and call 2 KB, network 64 KB, grade twice the largest measured six-call body.
  - Bad JSON or an unknown op gets 400.
  - Questions are capped at 300 characters, `decisions` at 200 entries.
  - A per-IP, per-instance limiter on call and grade returns 429 `busy`. It slows abuse but doesn't stop it, and the doc says so.
- **H5 Headers** in `vercel.json`, and the same on `vite preview`:
  - CSP: `default-src 'self'; script-src 'self'; style-src 'self'` (`'unsafe-inline'` only if e2e shows a block), `img-src 'self' data:; font-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
  - Also: `nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: microphone=(self), camera=(), geolocation=()` (Ask has voice input).
- **H6 Region `bom1`, decided by numbers.**
  - For 3 symbols, before and after: transcripts from NSE (`nse_ok` and the count), and the median `/api/sources` time over 3 runs.
  - Keep it only if the counts are equal and time is no more than 20% worse. Otherwise revert, and the doc says why.
- **H7 `evals/run_security.py`.** No model and no network: the resolver and transport are injected. Cases:
  - The network core's imports, and model modules not importing the network.
  - Grade: an unlisted URL, a mixed symbol and an oversized list are dropped or refused, and never fetched (the swapped `create_connection` raises).
  - Grade with NSE answering differently keeps honest calls.
  - Grade and call with no key answer `live_off` before any fetch.
  - The guard through `requests.get`: loopback, private, link-local, `::127.0.0.1`, rebinding (public, then private).
  - Through `pdf.fetch`: a redirect hop to 127.0.0.1, userinfo, an odd port, `file:`, a stream over the cap, a zip bomb.
  - `urllib3.connection.connection is urllib3.util.connection`.
  - No part of a key appears in any error.
  - Malformed and oversized bodies are refused; `decisions` is capped.
  - A question's text never appears in captured logs.
  - The P0 year check.

### Verification (numbers that decide)
- `run_security.py` all pass; `run_network.py` 225/225; `npm test` 27/27.
- `flows.py` on the local preview under the headers:
  - 40/40, and zero console messages mentioning Content Security Policy.
  - The rupee font face reports `loaded`.
  - `compare.py` shows no pixel change on Today and a company page, apart from the P0 line and the dropped years.
- The research path end to end locally with a stubbed model. The largest six-call body is recorded and sets the grade cap.
- Live, after each deploy:
  - `curl -I` shows the headers; `/robots.txt` is served; `x-vercel-id` shows the region.
  - A grade with a foreign URL fetches nothing and grades no such call.
  - `/api/network` gives the four starter questions the same answers as before, years from profiles aside.
  - With no key, a non-prebuilt company shows the `live_off` sentence within 2 s, with no PDF fetched.
  - https://finn-ledger.vercel.app is unchanged.
- The document:
  - Every "today" claim cites a file or a test.
  - At most 1,000 words outside folds (counted).
  - `~/ENAM-FINN/for_claude/slop_scan.py` passes.
  - The PNG is read at 390.

### Order (each step committed; deployed where marked)
1. P0, H1 and H4, with their checks. Deploy.
2. The document and diagram, true to that commit; the guard, grade rule, headers and region appear as "not yet" lines.
3. H2, H3 and `requirements.txt`; doc lines updated. Deploy.
4. H5 and H6, measured; e2e. Deploy.
5. Live checks, then:
   - final doc lines and the README architecture section (diagram, five lines, a link);
   - DECISIONS (the two sides; the server trusts only what it fetched; seals considered and cut);
   - the evals README;
   - NEEDS_FROM_USER (required before sharing the link: the firewall rate rule on `/api/call` and `/api/grade`; the key's Cloud project must have no billing; the model key).
6. ROADMAP: architecture done; `network-loop` already carries the filed-facts follow-up. STAGE: `plan writeup`.

Cut line: once step 2 is committed, the required section exists. H6 is the first thing to drop; next, H5's `style-src` tightening (keep `'unsafe-inline'`).

### Files
- **New:** `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`, `finn/netguard.py`, `evals/run_security.py`, `evals/security_result.txt`, `web/public/robots.txt`.
- **Changed:**
  - `data/network/investor.json`, the `finn/network` sentence renderer, `web/public/data/network.json`, `web/src/Network.tsx`
  - `finn/llm.py`, `finn/webapi.py`, `finn/research.py`, `finn/sources/pdf.py`
  - `api/*.py`
  - `web/src/lib.ts`
  - `requirements.txt`, `vercel.json`, `web/vite.config.ts`
  - `web/test/e2e/flows.py`
  - `evals/README.md`, `README.md`, `docs/DECISIONS.md`, `docs/NEEDS_FROM_USER.md`, `docs/ROADMAP.md`

### Not in this task
- The covering note's short version (`writeup` lifts section 0).
- The in-app privacy sheet (`trust`).
- Removing the invented years from the profile data (`network-loop`).
- Sign-in, a database, a scheduler: described, not built.

## Execution log
- Step 1 (P0, H1, H4) committed: 825bcda, d20334f. `run_security.py` 39/39, `run_network.py` 225/225, `npm test` 27/27, `flows.py` 40/40 on the local preview. No-key path shows the sentence in 0.05 s with no call fetched. Grade body cap set to 64 KB from built files (DIXON, 32 KB), still to be measured end to end.
- Deploy after step 1 was refused by the session's permission check; nothing deployed yet. The live link still runs the pre-P0 build.
- Step 2 (document and diagram) committed: a8c3a9c. 997 words outside folds; slop scan passes; PNG read at 390.
- Step 3 (H2, H3, urllib3 pin) committed: 19e5282. End to end with a stubbed model on ASIANPAINT (sources, 6 calls, grade, as the phone calls them): every honest call kept. The largest realistic body is 34 KB at 10 promises a call (the most any real call has; the most a real company has is 38), so the grade cap is 68 KB. The app now sends only `src.symbol` to grade. Real NSE and BSE PDFs download through the guard.
- Step 4: H5 committed (ddc08cf). On the local preview under the headers: `flows.py` 40/40, 0 CSP or console messages, the rupee face `loaded`, service worker registered. Pixel diff against the live link: Today and LT differ only in the new demo-network line (it wraps to two lines on the company page, +18 px). H6 dropped (cut line): it needs live timings, and deploys are refused in this session. The doc says "Not yet: the Mumbai region; it needs live timing."
- Step 5, without the live part: README architecture section, DECISIONS, evals README, NEEDS_FROM_USER committed (061abec and after). `run_security.py` 74/74, `run_network.py` 225/225, `npm test` 27/27; ARCHITECTURE.md 999 words outside folds, slop scan passes.

- Session 2 (11 Nov): deploy refused again by the permission check. Saved the live (old build) `/api/network` answers to the four starters and notices in `evals/live_network_before.json`. The committed code gives the same answers except where a profile's years were dropped (5 strings, same people, rows and order; deterministic), so "answers as before, years from profiles aside" holds locally. Wrote `web/test/e2e/live.py`: every live check in one run, with network answers compared to the committed code's. Against the old build it fails what the deploy should fix (headers, robots, grade answers `500 KeyError: 'quarters'` on a made-up body) and passes the rest.
- Session 3 (11 Nov): deploy refused a third time by the permission check; live still `index-B42OWfM3.js`. Nothing else in this task can move without it.
- Session 4 (11 Nov): live still `index-B42OWfM3.js` with no CSP header; deploy tried once and refused a fourth time. Stopped to ask the user to deploy or allow the script.
- Session 5 (11 Nov): live still `index-B42OWfM3.js` with no CSP header. No deploy attempt, since it has been refused four times and the user hasn't deployed or allowed it yet.
- Session 6 (11 Nov): same: live `index-B42OWfM3.js`, no CSP header, and no permission rule for the script in any settings file. No deploy attempt.
- Session 7 (11 Nov): same again: live `index-B42OWfM3.js`, no CSP header, no permission rule. No deploy attempt.

- Session 8 (11 Nov): same: live `index-B42OWfM3.js`, no CSP header, no permission rule. Three sessions had ended on this with nothing else moving, so the live part is cut from this task: the architecture is done in the repo, and the live checks became a standing step at the start of every execute session (`docs/ROADMAP.md`, rules). STAGE: `plan writeup`.

### Still owed on the live link (run when the live hash changes)
1. `python3 web/test/e2e/live.py` (all must pass) and `python3 web/test/e2e/flows.py https://finn-network.vercel.app` (40/40).
2. Optionally H6 (region `bom1`) by the plan's rule, once live timings exist.

- Session 9 (11 Nov, writeup execute): the user deployed. Live `index-BqOq4beW.js`, same as a local build of `220d293`; live `/data/network.json` matches the repo byte for byte. `live.py` 16/16 after one fix to the test itself: the no-key check opened `#/read/MARICO` (a card's full view, so it landed on Today) instead of `#/c/MARICO`; on the right route the sentence shows within 2 s. `flows.py` on the live link 40/40. Items 1 of "Still owed" done; H6 still optional.
