# Plan: `architecture-x`

A world-class architecture for the Founding AI Engineer role (`NETWORK_SPEC4.md`, "PRIORITY NOW"). The JD names agentic workflows and orchestration, data ingestion architecture, LLM reliability and evaluation, security, Python, a major cloud, and ML on large datasets, plus mentoring and setting direction. Today's `docs/ARCHITECTURE.md` answers the brief's four headings well but has no agent, a batch pipeline run by hand, no production cloud, no ML beyond model calls, and nothing written for a team.

## v1 (12 Nov)

### Facts this plan rests on (checked 12 Nov)
- **No model key here.** `.env` is absent; `GEMINI_API_KEY` is unset; `data/cache/llm/` is empty. Anything that needs Gemini can be built and tested offline but not measured live. `NEEDS_FROM_USER.md` already asks for the key.
- **NSE is reachable market-wide.** One day of announcements for every company: 694 rows, 376 companies, 2.5 s (27 Oct). One bhavcopy: every listed security, 0.3 s. A year of both is about 20 minutes of polite fetching.
- **scikit-learn 1.5, pandas, numpy and matplotlib are installed.** No terraform, gcloud or docker.
- **13 of 109 calls in the built companies failed to read** (ERIS and MARUTI hosts serve non-PDFs to scripts, SRF unreachable, two cover letters). These are access failures, not navigation problems, so a "transcript-finding agent" would not earn its place.
- `classify.by_rule` settles a filing from NSE's subject for free (211 of 286 in the snapshot); `pdf.verify_quote` is the quote check; the Pull steps are already separate functions (`research.py`).

### The idea the architecture opens with
**FINN is a line of small, checked steps over public events, with a private overlay that no model touches.** Every filing and every trading day is an event with a stable id. Steps turn events into facts: rules first, then a learned score, then a model only where text must be read, and code checks every model output. Facts are projected into the files the phone reads. Your book and your network are joined to those facts in code, on your side. One agent exists, where the path can't be written down in advance: answering a question about a company from its calls. It can only read public pages and propose an answer, and code checks the answer.

Four sentences a CTO can push on, each with a test behind it.

### What is built and what is designed

| Area | Built here, with an eval | Designed only (and why) |
|---|---|---|
| Ingestion | Event log and step ledger in SQLite; poller with checkpoint; idempotent steps; retries, dead letters, "parked" when the model is unavailable; replay of the 28 Oct window | Pub/Sub and Cloud SQL adapters (no GCP account; can't be run) |
| ML | A year of every NSE filing and price; event study; a logistic model; time-split evaluation against FINN's own tier policy | Monthly retraining job |
| Agent | Runtime, five public tools, the answer verifier, offline evals (guardrails, verifier, retrieval) and a scripted end-to-end run | Live success rate (needs the key; script ready); its place in the Pull screen (task `ask`) |
| Reliability | `evals/gate.py`: every eval against a floor, skips shown as skips | CI on push (I don't push) |
| Cloud | | GCP `asia-south1` target, IAM per plane, a key per investor, cost |
| Security | Agent and ingestion boundary checks added to `run_security.py` | VPC Service Controls, Cloud Armor, firm sign-in |

No app change in this task: the snapshot stays at 28 Oct (decided in ROADMAP), so there is nothing to deploy.

### A. Raw archive (one fetch feeds both B and C)
`pipeline/archive.py` (≤ 80 lines): NSE announcements for every company, 1 Nov 2025 to 28 Oct 2026, one gzip per day; bhavcopy 1 Aug 2025 to 30 Oct 2026 (60 sessions of history before the first filing, one after the last), only EQ/BE rows and the columns used. Under `data/raw/` (git-ignored). Resumable, one request a second, a manifest with counts per day. Sanity: no day's count sits at a round cap; weekends near zero; results season (late Jul, late Oct) peaks. Runs in the background while A's consumers are written.

### B. Event-driven ingestion, built (`finn/ingest/`, ≤ 250 lines)
- `store.py`: SQLite with three tables. `events(id PK, kind, at, symbol, payload)`: the NSE `seq_id` or the session date is the id, so a filing seen twice (NSE windows overlap) is stored once. `runs(event_id, step, version, status, attempts, output, error)`, keyed by event, step and step version: a step's output is stored once and reused by every replay and every investor. `checkpoints(source, high_water)`, moved only after the events are committed (at-least-once in, once in effect).
- `steps.py`: the chain for a filing: `rules` (`classify.by_rule`) → `score` (C's model, no network) → `read` (model, vague filings only, in batches of 20 as today) → `people` (model, management changes) → `results` (XBRL first cut) → `size` (code, against a year's revenue) → `tier` (code). Each step wraps the existing function; none is rewritten. A step declares its version; bumping it re-runs that step and those after it, nothing else.
- `worker.py`: drains step by step (so model steps keep their batches), 3 attempts then `dead` with the error kept; `LLMError` `no_key` or `quota` sets `parked`, not failed, and the filing projects as today's "couldn't read; shown, doesn't interrupt".
- `pipeline/ingest.py`: `poll`, `drain`, `project` (writes the `filings` part of push.json's shape), `replay --asof 2026-10-28T…` (the snapshot window from the archive), `import-readings web/public/data/push.json` (the 28 Oct model readings, imported as `runs` rows marked as imported, so a replay without a key reproduces the snapshot).
- Private overlay stays where it is (`finn/network/`, joined in code). Ingestion is public plane only.
- **`evals/run_ingest.py`** (no key, no network after the archive): (1) the replayed window's filing ids equal push.json's 286, or the difference is listed and explained; (2) category and tier match push.json for 286/286; (3) a second replay makes 0 new events and 0 step runs; (4) a step failing twice then succeeding ends `done`; failing three times ends `dead` and no other filing is affected; (5) duplicate and out-of-order delivery leave one fact each; (6) with no key and no imported readings, model steps end `parked`, none `failed`; (7) bumping `size`'s version re-runs `size` and `tier` only.
- `build_push.py` stays: it built the snapshot. The ADR says it is retired once the event path has produced a live day.

### C. ML: which filings move the market (built, measured)
`finn/materiality.py` (features and scoring, ≤ 120 lines), `pipeline/build_materiality.py` (dataset and training, ≤ 150), `evals/run_materiality.py`, `docs/MATERIALITY.md` (≤ 600 words, one chart).
- **Unit:** a company-day. A filing's day is the first session whose close follows it (after 15:30 IST, the next session). Universe: EQ/BE stocks with 60 sessions of history and a median traded value of at least ₹1 crore a day over the prior 20 sessions.
- **Label:** the market reacted. Abnormal return = the stock's return minus the universe median that day, summed over the day and the next, divided by the stock's own prior 60-session abnormal volatility times √2. Reacted if |z| ≥ 3. Second label: volume at least 3× its prior 20-session median. Days over ±40% are dropped as corporate-action artefacts.
- **Traps handled:** exchange-prompted filings ("Spurt in Volume", "Price movement", "News Verification", "Clarification") follow a move rather than cause one; they are reported apart and kept out of training. Several filings on one day: features are multi-hot, and category rates are also shown for single-category days. Features use only the past.
- **Insight:** for each category (from `by_rule`, plus "vague" for those a model would read), the share of company-days that reacted, its lift over company-days with no filing, a 95% Wilson interval, n; under 200 marked too few. The same for FINN's three tiers. **Stop rule:** if results days don't show a lift of at least 2, the alignment is wrong; fix before modelling.
- **Model:** logistic regression on NSE's subject (one-hot, top 80), category, filing time (before open, in session, after close), filing count, size (log traded value), prior volatility, and TF-IDF of the attachment text (words and pairs, min_df 20). Interpretable: its heaviest words are part of the insight. Weights saved as JSON (never a pickle) in `data/ml/materiality.json`.
- **Split by time:** train Nov 2025 to Jun 2026, choose C on Jul 2026, test Aug to 28 Oct 2026. On filing company-days in the test months: PR-AUC, ROC-AUC, and recall at the top 10% (if Today showed one filing in ten, how many of the days the market reacted to would be in it), against three baselines: FINN's tiers, category base rates from training, random. Calibration in five bins.
- **In the system:** the `score` step attaches `p_react` to every filing fact. It orders the model's read queue in a burst (results season) so likely-material filings are read first; it gates nothing, so it can't hide a filing. Whether it orders Today is a product decision left to the user, with the numbers (ADR).
- **Not a trading signal:** directionless, says whether the market noticed, not which way; FINN gives no advice. Said in the doc and the ADR.
- Commit the company-day table (`data/ml/company_days.csv.gz`) if ≤ 5 MB; otherwise the aggregates and the script.

### D. One agent, built (`finn/agent/`, ≤ 300 lines)
- **Why this one.** A question about a company ("what did they say about margins, and did it happen?") needs a path that depends on what's found: which call, which page, whether numbers are needed, when to stop. That is the case an agent earns. Everything else in FINN has a fixed path and stays a workflow.
- `runtime.py`: a loop over a model that can call tools. Limits: 6 steps, 10 tool calls, 60k input tokens; then it stops and says so. Tools are registered with a JSON schema and a plane; the runtime refuses a tool whose plane isn't public. Arguments are validated before a tool runs (symbol pattern, period from the company's own list, page in range); **no tool takes a URL**, so the model can't make the server fetch anything it didn't list. Tool output goes back marked as quoted filing text, never as instructions, and is cut to 4,000 characters. A JSONL trace per run: step, tool, arguments, sizes, tokens, cost.
- `tools.py`: `calls(symbol)`, `search(symbol, query)` (BM25 over the pages of the last four calls, in code), `read(symbol, period, page)`, `numbers(symbol, metric)` (quarterly rows and their QoQ and YoY, computed in code), `finish(answer, citations)`.
- `verify.py`: every citation's quote must be on its page (`pdf.verify_quote`); every number in the answer must appear in a `numbers` result or a verified quote; anything unsupported is dropped; if nothing survives, the answer is "Not in the calls I read." If flash-lite's answer loses all its citations, one retry on flash.
- `llm.py` gains `chat(messages, tools)` (Gemini function calling, same header key, same fixed error codes).
- `python3 -m finn.agent SYMBOL "question"` prints the answer, citations and cost.
- **`evals/run_agent.py`**, offline by default: (a) guardrails with scripted models: an unknown tool, a URL argument, a period not in the list, a private tool, a seventh step, an oversized result; each refused or stopped. (b) Verifier on doctored answers built from real ledger quotes: real kept, number changed, quote from another page, a number in no tool result, all caught. (c) Retrieval: 30 questions in plain investor words over five built companies with every call readable, each labelled with the page that answers it (taken from the ledger's verified quotes, the question written without the quote's words), plus 6 the calls can't answer; BM25 recall at 5. (d) A scripted model runs the whole loop end to end on one question: search, read, finish, verified. `--live` (with a key): answered with a verified citation on the labelled page, correct "not in the calls" on the 6, unsupported numbers after the verifier (must be 0), mean steps and cost, escalations. Results and traces saved.
- `run_security.py` gains: `finn/agent` imports nothing from `finn/network`; no tool schema has a URL field; the registry rejects a private tool; `finn/ingest` imports nothing from `finn/network`.

### E. The eval gate (`evals/gate.py`, ≤ 80 lines; `evals/gate.json`)
Runs every eval, compares each with a floor (security all, network 225/225, quotes ≥ 74/80, ingest all, agent offline all, materiality: model PR-AUC above the tier policy's, results lift ≥ 2), prints one table, exits 1 on a regression. An eval that needs the key or the network prints SKIP with the reason; a skip is never a pass. This is the rule the team works to: nothing merges below the floor.

### F. Documents
- **`docs/ARCHITECTURE.md`, upgraded** (≤ 1,400 words outside folds): the idea above, then the brief's four headings unchanged in order (pipelines, security and privacy, LLMs and agents, cloud), then ML, then "built and designed". Each section: today, built in this task, production. Every number tied to an eval output through `evals/claims.py`.
- **The diagram, redrawn** (`docs/img/architecture.svg` + 2× PNG): archive → events → steps (rules, score, model, code) → facts → views; the private overlay below the line; the agent beside the facts, reading public pages only; production names in small type under each box.
- **`docs/adr/`**, each ≤ 350 words: context, options, decision, trade-offs, revisit when.
  1. Two planes: a model reads only what the market publishes.
  2. Events, steps and views, with an idempotent step ledger.
  3. Workflows by default; one agent, where the path is unknown; tools as its boundary.
  4. Code checks every model output; evals are a merge gate.
  5. Model routing: rules, a learned score, flash-lite, then flash; a reading is paid for once for everyone.
  6. The materiality model: market reaction as the label, logistic regression, time split; not a trading signal.
  7. Production on GCP `asia-south1`: Cloud Run, Pub/Sub, Cloud SQL, Cloud Storage, Vertex AI, KMS. Why not AWS or Azure, Kubernetes, or staying on Vercel.
  8. The investor's data: one key per investor (envelope encryption), erasure by destroying the key, consent, staff access logged.
  9. Retrieval: BM25 over pages, no vector store, until questions cross companies.
- **Production target (in ADR 7 and ARCHITECTURE §4):** Cloud Scheduler → Cloud Run job `poll` → Pub/Sub → Cloud Run `steps` (retries, dead-letter topic, alert) → Cloud SQL (events, runs, facts) and Cloud Storage (raw archive, readings). The private overlay is a separate Cloud Run service whose service account **has no permission to call Vertex AI**, so the two-plane rule holds in IAM as well as in tests. Vertex AI with workload identity: no API key exists to leak. Per-investor data in Cloud SQL with row-level security and a data key per investor wrapped by Cloud KMS. Identity Platform with the firm's sign-in. Cloud Armor rate limits per user (fixes the per-instance limiter). Logs hold codes and timings, never text. Monthly cost at the whole market, in ranges, dominated by the database and the model; prices marked as list prices on a date.
- **`docs/INTERVIEW_DEFENSE.md`** (≤ 3,000 words): about 30 of the hardest questions ENAM's CTO would ask, grouped: agents, orchestration, ingestion, reliability, evaluation, security and privacy, cloud, cost and scale, ML, leading a team, and "what did you get wrong". Each: the question, an honest answer in at most 90 words, and the evidence (file, eval, number). Where the honest answer is "not built" or "not measured yet", it says so.
- **`docs/ENGINEERING.md`** (≤ 600 words): how a team builds FINN. The rules (a model step ships with a schema, a code check and an eval; private code imports no model module; a tool never takes a URL; every number in a document comes from a file), how to add a source, a step or a tool, the gate, and what I'd hand to the first three engineers.
- `evals/README.md`: sections for ingest, materiality, agent, gate. `README.md`: one pointer line. `docs/ROADMAP.md`: task 0 done; `ask` becomes "the analyst agent behind Pull's question box, with its live eval"; `writeup` must describe this architecture. `docs/NEEDS_FROM_USER.md`: the key now also runs `run_agent.py --live`.

### Order (commit after each; each commit leaves the documents true)
0. Standing live check (ROADMAP rule). Start A in the background.
1. B with `run_ingest.py`, ADR 2, the ingestion questions in INTERVIEW_DEFENSE.
2. C with `run_materiality.py`, `MATERIALITY.md`, the chart, ADR 6, the `score` step, the ML questions.
3. D with `run_agent.py`, the security checks, ADRs 3 and 9, the agent and reliability questions. `--live` if a key has appeared.
4. E, ADR 4, `ENGINEERING.md`.
5. ARCHITECTURE.md, the diagram, ADRs 1, 5, 7, 8, the rest of INTERVIEW_DEFENSE, claims.
6. ROADMAP, NEEDS, the writeup plan's amendment note, `STAGE` = `plan writeup`.

### Verification (numbers that decide)
- `run_ingest.py`: 7 checks pass; 286/286 tiers equal push.json's.
- Archive: at least 100,000 filings, 1,500 companies, 240 sessions.
- `run_materiality.py`: results lift ≥ 2 (else stop); model test PR-AUC and recall at 10% reported against all three baselines. If the model doesn't beat FINN's tiers, that is reported as the finding and the ADR keeps the tiers.
- `run_agent.py`: every guardrail and verifier case passes; retrieval recall at 5 reported (target ≥ 80%).
- `run_security.py`: 74 → about 78, all ok. `run_network.py` 225/225 unchanged.
- `gate.py` exits 0 with skips listed.
- `claims.py`: ARCHITECTURE's numbers all claimed.
- Code size: new code under 900 lines outside evals.

### Files
New: `pipeline/archive.py`, `finn/ingest/{__init__,store,steps,worker}.py`, `pipeline/ingest.py`, `finn/materiality.py`, `pipeline/build_materiality.py`, `finn/agent/{__init__,__main__,runtime,tools,verify}.py`, `evals/{run_ingest,run_materiality,run_agent,gate}.py`, `evals/gate.json`, `evals/agent_questions.json`, `data/ml/materiality.json`, `docs/MATERIALITY.md`, `docs/img/materiality.png`, `docs/adr/0001…0009-*.md`, `docs/INTERVIEW_DEFENSE.md`, `docs/ENGINEERING.md`.
Changed: `finn/llm.py` (`chat`), `evals/run_security.py`, `evals/claims.py`, `evals/README.md`, `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`, `README.md`, `docs/ROADMAP.md`, `docs/NEEDS_FROM_USER.md`, `docs/plans/writeup.md`, `docs/STAGE`.

### Not in this task
The agent in the app (task `ask`); policy changes the ML suggests (task `network-loop`, with the numbers); deleting `build_push.py`; any app or deploy change.

## Round 1 critiques of v1 (12 Nov): 6, 6, 6, 6
- **ENAM grader (6).** Too big for the time left (line budgets don't add up; 9 ADRs, about 8,000 words). Nothing new runs where a grader can see it: poll a live NSE day. The 286/286 replay fails as written: screener revenue and the latest XBRL quarter have moved since 28 Oct, and results attach once per company, so out-of-order delivery breaks it. The agent has no baseline: compare it with BM25 plus one call. A file called INTERVIEW_DEFENSE in a public repo reads as rehearsed: put the hardest questions in a "where this is weak" section. Denying Vertex in IAM doesn't stop the private service calling the public API. Draw built solid and designed dashed. Dated prices. A 200-word paragraph for the covering note.
- **Investor and designer (6).** Sprawl, and the investor sees no change. `p_react` orders a hidden queue, and "whether it orders Today is left to the user" dodges the call. Reframe the ML as an audit of FINN's own interrupt policy and name the folded filings that moved. The agent has no user and no live run, and it reverses today's "a loop would add nothing checkable" without saying why. ARCHITECTURE is written last; write its skeleton first. Keep the privacy promise as the first sentence. About 15 questions, weakest first. Cut ENGINEERING.md, the routing ADR, the BM25 ADR and the flash escalation.
- **Staff engineer and security architect (6).** The replay is circular: rules re-run on the same input, and the model rows come back through `import-readings`. Wrapping `classify.classify` and `triage` swallows `LLMError` into `fallback`, which breaks parked and retry. Results are cross-event state. Versions don't cascade: bumping `size` leaves `tier` done. Key runs on hash(code, prompt, model, inputs), record the model actually used, give events a payload hash, use a lookback, not a high-water mark. The verifier is unsound: `verify_quote` scans every page, and "the number is in some tool result" matches any number. Use one citation per sentence, abstain rather than drop. Report the pre-verifier rate; commit the questions before writing `search`. The ML stop rule can't catch misalignment: the event-time profile must peak at day 0. Exclude ex-dates rather than days over ±40%. Treat rumour verification and SAST filings as reverse-causal. Leave event days out of σ. Fit TF-IDF on train only and strip company names. Use date-clustered bootstrap intervals. "PR-AUC > tiers" as a gate floor stays red forever. GCP: one project per plane with egress denied. Wrapped data keys in Cloud SQL survive backups, so use a KMS key per investor. Pub/Sub needs at least 5 attempts and a pull worker. Build ML before the agent.
- **ENAM CTO (6).** The agent breaks FINN's own rule that questions never reach a model, and the free tier may train on them: make questions a third class, sent only on paid terms. No evidence the agent earns its place: compare with the pipeline; make answers structured claims that code checks (direction too); ship the loop only if it wins. "Materiality" is a statutory term under SEBI LODR Reg 30: call it price reaction. Circuit locks cap |z|. The tiers rank what an investor must look at, not what moves prices. Two sources of truth in production: let the ledger be the queue (Cloud SQL, `SKIP LOCKED`). Ingestion scrapes NSE alone: decide licensed feed versus scraping, ISIN across exchanges, lookback, revisions. Evals test plumbing, not the model: fingerprint prompt and model, add a live gate. Fewer documents.

### Decisions on round 1
Taken: everything above, except two. (1) `INTERVIEW_DEFENSE.md` stays in `docs/`, because the spec asks for it by name. It is the user's interview preparation, about 15 questions, weakest first. `final` leaves it out of the public snapshot unless the user wants it in. The grader gets "Where this is weak" in ARCHITECTURE. (2) The agent stays built, as an escalation with a decision rule written down before any live number exists, because orchestration of tools is the JD's first line. A local open-weights model as a stand-in planner was considered and cut: nothing is installed, and a multi-GB download in an unattended session is the wrong risk.

## v2 (12 Nov)

### What changed from v1
Half the documents (5 ADRs, no ENGINEERING.md, INTERVIEW_DEFENSE about 15 questions). ARCHITECTURE goes first, not last. No circular replay. A ledger that cascades, records the model it used, parks rather than swallows errors, and handles revisions. A whole-market live day. The ML renamed to price reaction and turned into an audit of FINN's interrupt policy that never reorders Today. Questions treated as a third kind of data. A fixed workflow as the baseline, with the agent as its escalation and a keep-or-delete rule written down before any live number. Claims checked in code, direction included. Gate floors that can pass, plus prompt and model fingerprints. GCP with one project per plane, egress denied, a KMS key per investor, and the ledger as the queue. Time box and cut order.

### The idea (ARCHITECTURE opens with it)
FINN keeps what you hold, who you know and what you ask away from anything that could learn from it. What the market publishes is read once for everyone, in small steps over a stream of filings, and code checks every model output. Your book and your network meet those facts in code, on your side. Your questions reach a model only under paid terms that rule out training on them. When the path to an answer can't be written down in advance, a bounded agent reads public pages, and code checks every claim before you see it.

### Built and designed

| Area | Running after this task, with its check | Designed only |
|---|---|---|
| Ingestion | Ledger in SQLite: events with revisions, fingerprinted steps, parked, dead; one whole-market NSE day ingested | Licensed feed; Cloud SQL as the queue |
| ML | A year of every NSE filing and price; an event study auditing FINN's tiers; a text model on the filings a model reads | Retraining on a schedule |
| Agent | Workflow (retrieve, one call, verify) and agent escalation on one runtime; claim verifier; offline evals | Live comparison (script ready; needs the key); its place in Pull (task `ask`) |
| Reliability | `gate.py`: floors, fingerprints, `--live` mode | Nightly run |
| Privacy | Questions refused by `llm.py` unless the model's terms are paid; boundary checks | Per-investor KMS keys, erasure |
| Cloud | | GCP `asia-south1`, two projects, costs |

No app change, nothing to deploy: the snapshot stays at 28 Oct.

### Scope, time box, cut order
- About 1,000 new lines outside evals: archive 80, ingestion 230, reaction 260, answering 270, `llm.py` 40, gate 90. Documents: ARCHITECTURE ≤ 1,500 words outside folds; 5 ADRs ≤ 300 words each; PRICE_REACTION ≤ 500; INTERVIEW_DEFENSE ≤ 1,500.
- **Done by 13 Nov 12:00 IST** (writeup needs the afternoon; `final` from 14 Nov). If behind, cut in this order: (1) C2, the text model; (2) the live market day; (3) the agent loop, keeping the workflow, the verifier and the evals, with ADR 3 saying the loop is designed. Never cut: ARCHITECTURE, the ADRs, the event study, the ledger and its checks, the gate, INTERVIEW_DEFENSE.
- **What it displaces**, stated in ROADMAP: probably `annual-report` and `trust`. `network-loop` takes the audit's named misses. `ask` shrinks to the Pull screen plus the live eval.

### Step 1. ARCHITECTURE first; the design-only parts; the privacy rule in code
- `docs/ARCHITECTURE.md` rebuilt around the idea, in this order: "In 200 words" (the covering note lifts it); the idea; the brief's four headings, each "Running now" and "For real"; §5 Price reaction; "Where this is weak" (5 items); "For the team" (≤ 250 words: the rules a model step, a tool and a source must meet, and the gate). Sections for pieces not yet built say "designed, being built" until their step lands. Each later step rewrites its section.
- Diagram (`docs/img/architecture.svg` + 2× PNG): archive → events → steps (rules, model, code) → facts → views; the private overlay below the line; the answering box beside the facts with an arrow to public pages only; small production names under each box; running solid, designed dashed. A box becomes solid in the commit that builds it.
- **ADR 1, three kinds of data:** public filings (a model may read them; read once for all), what you hold and who you know (code only, never a model), and what you ask (a model only under paid terms, India region, no training). Per-investor KMS keys and erasure, in summary.
- **ADR 5, production on GCP.** Region `asia-south1`, recovery in `asia-south2`.
  - **Ingestion.** Cloud Scheduler starts Cloud Run jobs. The ledger in Cloud SQL Postgres is the queue: workers claim rows with `FOR UPDATE SKIP LOCKED`, and model steps keep their batches. Cloud Storage holds the raw archive. No Pub/Sub until there is fan-out or more than about 100 events a second.
  - **Two projects.** The private project has Vertex AI disabled, outbound traffic denied (no NAT, a deny-all egress rule, Private Service Connect to Cloud SQL and KMS only) and a VPC Service Controls perimeter. The rule holds at the network as well as in tests.
  - **Models and access.** Vertex AI through workload identity, so there is no model key to leak. Identity Platform with the firm's sign-in. Cloud Armor limits per user.
  - **Per-investor keys.** One KMS key per investor, so destroying it makes every copy unreadable, backups included. Erasure takes as long as the scheduled-destroy delay, at least 24 hours.
  - **Cost.** A monthly table at whole-market scale, with list prices dated (at most 3 lookups).
  - **Why not.** AWS or Azure, Kubernetes, Pub/Sub, staying on Vercel.
- `finn/llm.py`: `generate(..., private_intent=False)` raises `LLMError("terms")` when `private_intent` is set and `FINN_MODEL_TERMS` isn't `paid`. `run_security.py` checks it.
- Commit.

### Step 2. Ingestion: the ledger (`finn/ingest/`, about 230 lines)
- `store.py` (SQLite in `data/cache/`):
  - `events(kind, id, rev, hash, at, symbol, isin, payload)`: a filing NSE changes arrives with a new hash and becomes a new revision.
  - `runs(kind, id, rev, step, fp, status, attempts, model, output, error)`: `fp` = hash(step version, prompt, schema, model asked, the `fp`s of the steps it reads). A run whose stored `fp` differs from the current one is pending again, so a change cascades to the steps after it and to nothing else.
  - `facts(key, value, fp, event)`: cross-event facts. A results first cut is keyed (symbol, quarter), so the order filings arrive in doesn't matter.
  - No high-water mark: `poll` re-reads a 3-day lookback every time; inserts are idempotent.
- `steps.py`:
  - **rules:** `classify.by_rule`.
  - **read:** vague filings only, in batches of 20, through a new `classify.read_batch` that raises. `classify.classify` keeps its fallback by calling it inside its own `try`.
  - **people:** management changes.
  - **results:** the (symbol, quarter) fact.
  - **tier:** `triage.tier_from_people`, extracted from `enrich` (`build_push.py` uses the same one).
  - **Errors:** `LLMError` `no_key` or `quota` → `parked`. `FetchError` `not_pdf` or `too_big` → `dead` at once. Others are retried and go `dead` after 5. The model actually used is recorded: `generate(meta=True)` returns it, because the fallback can switch models silently.
- `worker.py`: drains step by step (batches survive), 4 at a time for fetches. `pipeline/ingest.py`: `poll [--days 3]`, `drain`, `status`, `view` (filings in push.json's shape, written to `data/out/`, never to `web/public/`).
- **`evals/run_ingest.py`** (no key, no network: real rows from the archive, fetches stubbed):
  1. Two polls of the same window store each filing once.
  2. A changed payload becomes revision 2 and re-runs its steps.
  3. Two transient failures and then a success end `done`. Five failures end `dead`. `not_pdf` goes `dead` at once. Other filings are untouched.
  4. With no key, read and people are `parked`, never `failed` or `fallback`, and the view shows those filings as today's "not read; shown; doesn't interrupt".
  5. Changing read's prompt re-runs read and tier only.
  6. Results in any order give one fact per (symbol, quarter).
  7. The archive holds the snapshot's 286 filing ids for the 18 holdings in its window.
  Tiers are not compared with 28 Oct: the snapshot's readings can't be recomputed without the key, and importing them would make the check circular.
- **Live:** the latest trading day, whole market, `poll` then `drain` with no key. `evals/ingest_day.txt` records filings, companies, settled by rules, parked for the model, results cuts parsed and dead (with reasons), and wall time.
- **ADR 2: the ledger is the queue.**
  - **Source.** NSE scraped politely now; for real, a licensed feed behind the same `poll`, because NSE blocks cloud IPs, BSE-only companies are invisible, and terms matter.
  - **Identity.** ISIN identifies a company across exchanges. The lookback and revisions handle late and amended filings.
  - **Old builder.** `build_push.py` is retired once a keyed live day matches it.
- Commit.

### Step 3. Price reaction: a year of NSE filings audits FINN's interrupt policy
Files: `pipeline/archive.py` (started in the background at step 0), `pipeline/build_reaction.py` (≤ 150 lines), `evals/run_reaction.py` (≤ 150 lines), `docs/PRICE_REACTION.md`, `docs/img/reaction.png`. "Material" is never used: under SEBI LODR Reg 30 it means something else.
- **Data.**
  - **Filings.** Announcements for every company, 1 Nov 2025 to 28 Oct 2026, kept raw.
  - **Prices.** Bhavcopy from 1 Aug 2025 to 30 Oct 2026, EQ and BE series, with ISIN, high, low and turnover.
  - **Size.** About 200,000 filings: probes show 1,612 and 1,630 on heavy days, with no cap.
- **C1, the event study.**
  - **Event day:** the first session whose close follows the filing.
  - **Abnormal return:** the stock's return, from NSE's adjusted previous close, minus that day's universe median. It is divided by the stock's own σ over the prior 60 sessions, leaving out days it filed anything not routine.
  - **Reacted** means |z| ≥ 3, or a close locked at the day's high or low with |r| ≥ 4.9% (a band lock caps |z|; flagged).
  - **Second label:** volume at least 3× its prior 20-session median.
  - **Adjustment days excluded:** the adjusted previous close differs from the prior close by more than 0.5%. Checked on one known split.
  - **Universe:** at least 60 sessions of history and a median turnover of ₹1 crore a day.
  - **Alignment check (the stop rule):** for results filings, mean |z| over event days −5…+5 must peak at day 0. It is plotted.
  - **Reverse-causal filings,** reported apart: Spurt in Volume, Price movement, News Verification, Reg 30(11) rumour verification, clarifications, SAST and insider disclosures.
  - **Output:** reaction rate and lift over no-filing company-days, with date-clustered bootstrap 95% intervals, for FINN's three tiers (rules only, labelled so) and for each category and NSE subject. n < 200 is marked too few.
  - **Named misses:** subjects FINN folds or notes that react more than the median act subject, and act subjects with lift under 1.5, handed to `network-loop` with their numbers.
  - **Decision, now:** the study never reorders Today. It changes rules only through a reviewed edit in `network-loop`, because the tiers rank what a long-term investor must look at, and the market's reaction is evidence for that, not the definition.
- **C2, the text model, on the population a model reads today** (vague filings).
  - **Model:** logistic regression on TF-IDF, fit on train only with company names stripped, plus subject, filing time and size; also an ablation without the text.
  - **Split by time:** train Nov to Jun, choose C on Jul, test Aug to 28 Oct.
  - **Metrics,** ranked within each day: PR-AUC, and recall at the top 10% per day against the subject's base rate. Date-clustered intervals, quantile calibration.
  - **Use:** its heaviest words become proposed rules for `network-loop`; no model runs at serving time. Weights are saved as JSON.
- **Not a trading signal:** directionless, and FINN gives no advice.
- **Committed:** aggregates and `evals/reaction_result.txt` always; the company-day table if ≤ 5 MB.
- `PRICE_REACTION.md` carries the decision and its "revisit when" (no separate ADR). Commit after C1, again after C2.

### Step 4. Answering a question: workflow first, agent as escalation (`finn/agent/`, about 270 lines)
- **Written first and committed before `search` exists:** `evals/agent_questions.json`.
  - 30 questions over five built companies whose calls all read. Half are reworded from ledger quotes; half were written from reading call pages directly. Each is labelled with the page that answers it, and authorship is stated.
  - Six questions the calls can't answer.
- `tools.py`: `calls(symbol)`; `search(symbol, query)` (BM25 over the last four calls' pages, in code); `read(symbol, period, page)`; `numbers(symbol, metric, quarter)`. **No tool takes a URL.** A period must be in the company's own list, and a page must be in range. Results are cut to 4,000 characters and marked as filing text, not instructions.
- **An answer is claims.**
  - **Quote claim** {text, period, page, quote}: the quote must be on the cited page ±1 (`verify_quote`'s returned page is compared, not just found anywhere), and every number in the text must be in the quote.
  - **Number claim** {metric, quarter, change, direction}: code looks the number up and writes the sentence, so the model never states a number of its own.
  - **One failed claim rejects the whole answer.** Nothing is dropped silently, because dropping can flip the meaning.
- `runtime.py`, one loop for both:
  - **Workflow:** a plan written in code. `search` on the question takes the top 5 pages, then one flash-lite call, then verification.
  - **Agent:** the model picks the tools, with at most 6 steps, 10 tool calls and 60k input tokens, then verification.
  - **Order:** the workflow runs first. If it's rejected or empty, the agent runs once. If that fails too, the answer is "Not in the calls I read."
  - **Tools by plane:** tools are registered with a plane, and a private one is refused.
  - **Trace:** a JSONL trace per run.
  - **Privacy:** questions go with `private_intent=True`. The eval's own published questions go with `False`, explicitly.
- `llm.py` gains `chat(messages, tools)`: Gemini function calling, the key in a header, fixed error codes.
- **`evals/run_agent.py`**, offline by default:
  - **Guardrails:** an unknown tool, a URL argument, a period not in the list, a private tool, a seventh step, an oversized result.
  - **Doctored claims:** a quote cited to another page, a number changed, a number in the text but not in the quote, right numbers in the wrong direction, an unknown metric, one bad claim among good ones.
  - **Retrieval:** recall at 5 on the 30 questions.
  - **End to end:** a scripted run of the whole loop.
- **`--live`** (with a key): the workflow alone against workflow then agent, on the same 36 questions.
  - **Measures:** grounded answers (every claim verified, at least one on the labelled page ±1); correct "not in the calls" on the 6; the rejection rate before verification; cost and steps per question. 20 answers are checked by hand.
  - **Rule, written now:** the agent stays only if it adds at least 4 grounded answers out of 30 at no more than 3× the workflow's mean cost. Otherwise it is deleted, and ADR 3 says so.
- `run_security.py` adds:
  - `finn/agent` and `finn/ingest` import nothing from `finn/network`;
  - no tool schema has a URL field;
  - the registry refuses a private tool;
  - a question is refused on free terms.
- **ADR 3, workflow first and the agent on escalation.**
  - Why the November "no agents" changed: a question's path depends on what's found, and claims can now be checked.
  - BM25, not a vector store, until questions cross companies.
  - The keep-or-delete rule above.
- Commit.

### Step 5. The gate (`evals/gate.py`, `evals/gate.json`)
- **Floors:** every offline eval runs against a floor set at its committed value minus a tolerance (security and network all; quotes ≥ 74/80; ingest all; agent offline all; reaction alignment passes and its lifts within their intervals).
- **Fingerprints:** every model step's prompt, schema and model id is hashed. A changed hash is red until `--live` passes and records the new hashes. That is what goes red when flash-lite is upgraded.
- **`--live`** (key): the classify sample run twice, with agreement reported; the quotes eval; the agent eval.
- **Skips:** a skip prints its reason and never counts as a pass.
- **ADR 4: code checks every model output, and evals are the merge gate.**
- Commit.

### Step 6. Close
- **`docs/INTERVIEW_DEFENSE.md`** (≤ 1,500 words, about 15 questions, the weakest first). "What did you get wrong" leads, with this plan's own corrections: circular checks, "materiality", IAM-only planes, questions sent to a model. Each answer is at most 90 words, with its evidence, and says "not measured" where that is the truth.
- **ARCHITECTURE:** "Where this is weak" and "For the team" finished; its numbers claimed in `evals/claims.py`.
- **Other files:** `evals/README.md` sections. ROADMAP: task 0 done, displacement noted, `ask` narrowed, the `final` note on INTERVIEW_DEFENSE. NEEDS: the key also runs `gate.py --live` and `run_agent.py --live`. An amendment note at the top of `docs/plans/writeup.md`.
- `STAGE` = `plan writeup`. Commit.

### Verification (numbers that decide)
- **Ingestion:**
  - `run_ingest.py`: 7/7.
  - `ingest_day.txt`: a whole-market day with no `failed` status; parked plus dead plus done equals runs.
- **Archive:** at least 150,000 filings, 1,500 companies, 240 sessions; no day at a round cap.
- **Price reaction:** `run_reaction.py`'s alignment peaks at day 0 (else stop and fix); intervals on every rate; misses named; C2 metrics against the subject base rate, with and without text.
- **Answering:**
  - `run_agent.py` offline: every guardrail and doctored case caught; retrieval recall at 5 reported.
  - `--live` only if a key appears.
- **Existing evals:** `run_security.py` gains 5 checks, all ok; `run_network.py` 225/225.
- **Gate:** `gate.py` exits 0 and lists its skips.
- **Claims:** `claims.py` clean for ARCHITECTURE.

### Files
- **New:**
  - `pipeline/{archive,ingest,build_reaction}.py`
  - `finn/ingest/{__init__,store,steps,worker}.py`
  - `finn/agent/{__init__,__main__,runtime,tools,verify}.py`
  - `evals/{run_ingest,run_reaction,run_agent,gate}.py`, `evals/{gate.json,agent_questions.json,ingest_day.txt,reaction_result.txt}`
  - `docs/PRICE_REACTION.md`, `docs/img/reaction.png`
  - `docs/adr/000{1..5}-*.md`, `docs/INTERVIEW_DEFENSE.md`
- **Changed:**
  - `finn/llm.py` (`private_intent`, `meta`, `chat`); `finn/classify.py` (`read_batch`); `finn/triage.py` (`tier_from_people`)
  - `evals/run_security.py`, `evals/claims.py`, `evals/README.md`
  - `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`
  - `docs/ROADMAP.md`, `docs/NEEDS_FROM_USER.md`, `docs/plans/writeup.md`, `docs/STAGE`

### Not in this task
- The agent in the app (`ask`).
- Tier changes from the audit (`network-loop`).
- Deleting `build_push.py`.
- Any app change or deploy.

## Round 2 critiques of v2 (12 Nov): 8, 8, 8, 8
- **Investor and designer (8).** The handoffs go to tasks the calendar won't run: say plainly which fall, write the audit's misses as specific proposed rule edits, and pick now the one task that runs after writeup. It should be `trust`, the sheet that puts the three kinds of data on the phone. The opening contradicts itself ("keeps what you ask away", then "your questions reach a model"). "What I got wrong" should be mistakes the app shipped with, not reviewer catches. Keys and erasure only in ADR 5. "Designed", never "being built". 20 labelled questions, not 30.
- **ENAM grader (8).** Never cut the live day, which is the grader's only proof that ingestion runs; INTERVIEW_DEFENSE goes before it. Stop at noon and relabel anything unfinished as designed. The ledger drops the explain and size downgrade, so it doesn't run FINN's policy and can never "match" `build_push`. Audit only subjects the rules settle, report model-dependent ones as unaudited, and cross-check on the 286 real tiers. Lead with the checked workflow and call the agent "built, unmeasured, kept only if it wins". The terms flag is a guard against accidents; enforcement is Vertex in production. Keep a one-sheet `trust`.
- **ENAM CTO (8).** Questions have no home in the two projects: an answering service in the public project, stateless, given the question without an investor id. The region must be checked: is flash-lite served from `asia-south1`? How do facts reach a project whose egress is denied: a read-only export, the one arrow across. The named misses need multiple-testing control. The keep rule must count correct answers judged by hand, over two live runs. C2's text is NSE's subject text. Hash canonical payload fields. Write the live floors down.
- **Staff engineer and security architect (8).** Questions fail open (`private_intent` defaults to False): make private the default and public explicit. Traces keep a hash, never the text. `people` depends on `read`, so check 5 as written would lock in a bug, and `first_cut` needs the filing's quarter. Leases for crashed workers; never hold a lock through a model call; partial batches stay pending. v1's two-day window was right: results filed at 15:00–15:29 react on day +1. A band lock means the close is at a real band limit. Name a miss only if the interval's bound clears the bar. The gate can't pass without a key: a first-seen fingerprint is "unvalidated", not red. Keep `read_batch`'s prompt byte-identical. Quote claims: show the quote verbatim, with the model's own text cut to a label. A smaller live day: check the key before fetching PDFs, and cap the results cuts.

### Decisions on round 2
All taken. `INTERVIEW_DEFENSE.md` stays (the spec names it) but is the last thing written and the first cut short (to 10 questions). The live day is never cut.

## v3 (12 Nov)

### The idea (ARCHITECTURE opens with it, and claims only what runs)
No model ever sees what you hold or who you know. What you ask reaches a model only under terms that forbid training on it, and never with your holdings or your name. What the market publishes is read once for everyone, in small steps over a stream of filings, and code checks every model output. A question about a company is answered by a fixed, checked workflow: find the pages, one model call, every quote checked on its page. An agent that chooses its own reading is built behind it but not yet measured, and it stays only if it beats the workflow.

### Built and designed

| Area | Running after this task, with its check | Designed only |
|---|---|---|
| Ingestion | SQLite ledger running FINN's full filing policy: events with revisions, fingerprinted steps, leases, parked, dead; one whole-market NSE day ingested | Licensed feed; Cloud SQL as the queue |
| ML | A year of every NSE filing and price; an event study auditing the tiers the rules set; a text model on the filings a model reads | Scheduled retraining |
| Answering | Workflow and agent on one runtime; quotes shown verbatim, numbers written by code; offline evals | Live comparison (script ready; needs the key); the Pull screen (task `ask`) |
| Reliability | `gate.py`: floors, fingerprints, `--live` with written floors | Nightly run |
| Privacy | Model calls private by default; public text marked explicitly; traces keep hashes | Two GCP projects, per-investor KMS keys |
| Cloud | | GCP `asia-south1`, dated costs |

No app change, nothing to deploy: the snapshot stays at 28 Oct.

### Scope, time box, cut order, what falls
- **Size.** About 1,050 new lines outside evals. ARCHITECTURE ≤ 1,500 words outside folds; 5 ADRs ≤ 300 words each; PRICE_REACTION ≤ 500; INTERVIEW_DEFENSE ≤ 1,500.
- **Stop at 13 Nov 12:00 IST wherever things stand.** Anything unfinished is relabelled "designed" in ARCHITECTURE, the ADRs and the diagram, and the close (step 6) runs anyway.
- **Cut order:** (1) C2, the text model; (2) the agent loop, keeping the workflow, the verifier and the evals, with ADR 3 saying the loop is designed; (3) INTERVIEW_DEFENSE down to 10 questions. **Never cut:** the live market day, ARCHITECTURE, the ADRs, the ledger and its checks, the event study, the gate.
- **What falls, written in ROADMAP plainly.** With `final` from 14 Nov and `writeup` on 13 Nov afternoon, `network-loop`, `annual-report` and `ask` won't run. If time remains after `writeup`, the one task is `trust`, cut to one sheet written from ADR 1: what FINN holds about you, who reads what, what a question costs you in privacy. That puts this work on the phone. The audit's misses go into PRICE_REACTION.md as specific proposed rule edits with their numbers, and into the writeup's "next".

### Step 0. Standing live check (ROADMAP rule); start the archive fetch in the background
`pipeline/archive.py` (≤ 80 lines, resumable, one request a second, a manifest of counts per day):
- **Filings:** NSE announcements for every company, 1 Nov 2025 to 28 Oct 2026, one gzip per day under `data/raw/` (git-ignored).
- **Prices:** bhavcopy from 1 Aug 2025 to 30 Oct 2026, EQ and BE rows, with ISIN, open, high, low, close, adjusted previous close, volume and turnover.

### Step 1. ARCHITECTURE first; the design-only parts; privacy in code
- **`docs/ARCHITECTURE.md` rebuilt, in this order:**
  - "In 200 words", for the covering note;
  - the idea;
  - the brief's four headings, each with "Running now" and "For real";
  - §5 Price reaction;
  - "Where this is weak" (5 items);
  - "For the team" (≤ 250 words): the rules a model step, a tool and a source must meet, and the gate.
  
  A piece not built yet says "designed". Each step rewrites its own section when it lands.
- **The diagram** (`docs/img/architecture.svg` + 2× PNG):
  - archive → events → steps (rules, model, code) → facts → views;
  - the private overlay below the line, with one arrow down: a read-only facts export;
  - the answering box beside the facts, reading public pages only;
  - small production names under each box.
  
  Running solid, designed dashed; a box turns solid in the commit that builds it.
- **ADR 1, three kinds of data, who may read each and where each lives:**
  - **Public filings:** a model may read them, once for everyone.
  - **What you hold and who you know:** code only, never a model. Stored in the private project, which is described in ADR 5.
  - **What you ask:** sent to a model only on paid terms with no training. In production it goes to a stateless answering service in the public project. That service gets the question without an investor id (the edge checks the sign-in and passes only the question and the symbol), logs codes and timings, and keeps nothing. Traces keep a hash of the question, never its text. Vertex request logging is off.
  - **Region:** state whether flash-lite is served from `asia-south1`, checked in one lookup. If it is only available on a global endpoint, ADR 1 says so and names the regional model that would replace it.
- **ADR 5, production on GCP,** region `asia-south1`, recovery in `asia-south2`.
  - **Ingestion:** Cloud Scheduler starts Cloud Run jobs. The ledger in Cloud SQL is the queue: a claim is a short transaction that sets `lease_until` with `SKIP LOCKED`, no lock is held through a model call, and expired leases are reclaimed. Cloud Storage holds the raw archive.
  - **Public project:** ingestion and the answering service, which reaches Vertex AI through workload identity, so there is no model key.
  - **Private project:** the overlay. Vertex is disabled, egress is denied (no NAT, a deny-all egress rule, Private Service Connect to Cloud SQL and KMS), and a VPC Service Controls perimeter surrounds it. It reads a read-only facts export (a Cloud Storage bucket shared into the perimeter), which is the one crossing.
  - **Per-investor keys:** one KMS key per investor, so destroying it makes every copy unreadable, backups included. Erasure takes the scheduled-destroy delay (at least 24 hours).
  - **Access and limits:** Identity Platform with the firm's sign-in; Cloud Armor limits per user.
  - **Cost:** a monthly table at whole-market scale, list prices dated (at most 3 lookups, shared with the region check).
  - **Why not:** AWS or Azure, Kubernetes, Pub/Sub (revisit at fan-out or about 100 events a second), staying on Vercel.
- **`finn/llm.py`:**
  - `generate` and `chat` treat text as private by default. Public text needs `public=True`, which the existing callers in `classify`, `people`, `explain` and `ledger` now pass.
  - Private text raises `LLMError("terms")` unless `FINN_MODEL_TERMS=paid`. That flag is a guard against accidents; ADR 1 says the real control is Vertex in the production project.
  - The cache key and the prompts are unchanged.
  - `run_security.py` checks both directions.
- Commit.

### Step 2. Ingestion: the ledger runs FINN's filing policy (`finn/ingest/`, about 260 lines)
- **`store.py` (SQLite, under `data/cache/`), four tables:**
  - **`events(kind, id, rev, hash, at, symbol, isin, payload)`:** the hash covers fixed fields only (symbol, subject, attachment text, attachment URL, time, ISIN), so a cosmetic change in NSE's JSON doesn't re-bill the model. A real change becomes a new revision.
  - **`runs(kind, id, rev, step, fp, status, attempts, lease_until, model, output, error)`:** `fp` = hash(step version, prompt, schema, model asked, the `fp` of every step it reads). A stored `fp` that differs from the current one makes the run pending again.
  - **`facts(key, value, fp, event)`:** results first cut keyed (symbol, quarter); revenue keyed (symbol, quarter).
  - No high-water mark. `poll` re-reads a 3-day lookback; inserts are idempotent.
- **`steps.py`, in triage's order.** Every decision `build_push` makes is a step, and each calls the existing function:
  1. **rules:** `classify.by_rule`.
  2. **read:** vague filings, batches of 20, through `classify.read_batch`. Its prompt is byte-identical to today's, so classify's fingerprint and cache survive. It raises instead of falling back; `classify.classify` keeps its fallback by calling it inside its own `try`. A partial batch (18 of 20 returned) leaves the missing 2 pending, never `fallback`.
  3. **people:** management changes, decided on the category from rules or read.
  4. **explain:** `enrich_line`'s selection, reading the line, the amount and "routine".
  5. **results:** `first_cut(symbol, quarter_end)`, with the quarter taken from the filing's date.
  6. **size:** code. The amount over the (symbol, quarter) revenue, fetched only when explain found an amount.
  7. **tier:** code. `triage.tier_from_people` and `triage.downgrade`, extracted from `enrich` and used by `build_push` too.
- **Errors.**
  - **Before fetching:** `has_key()` is checked before any model step fetches a PDF. With no key it parks without fetching.
  - **Parked:** `LLMError` `no_key`, `quota` or `terms`.
  - **Dead at once:** `FetchError` `not_pdf` or `too_big`.
  - **Retried:** everything else, `dead` after 5 tries.
  - **Recorded:** the model actually used (`generate(meta=True)`), because the fallback can switch silently.
- **`worker.py`:** claims with a lease, works outside the claim, drains step by step (so batches survive), and fetches 4 at a time.
- **`pipeline/ingest.py`:** `poll [--days 3]`, `drain [--cap-results 50]`, `status`, and `view` (filings in push.json's shape, written to `data/out/`, never to `web/public/`).
- **`evals/run_ingest.py`:** no key, no network. It uses real rows from the archive with fetches stubbed.
  1. Two polls of a window store each filing once.
  2. A cosmetic payload change makes no revision; a real change makes revision 2, which re-runs its steps.
  3. Transient failure handling:
     - two failures and then a success end `done`;
     - five failures end `dead`;
     - `not_pdf` is `dead` at once;
     - other filings are untouched.
  4. A worker killed mid-step leaves a lease, which expires; the run is reclaimed and done once.
  5. A partial batch leaves the missing filings pending.
  6. With no key, every model step is `parked` and none is `failed` or `fallback`. Nothing is fetched for them. The view shows those filings as today's "not read; shown; doesn't interrupt".
  7. Changing read's prompt re-runs exactly read and the steps that read it (people, explain, size, tier), and not rules or results.
  8. Results arriving in any order give one fact per (symbol, quarter).
  9. The archive holds the snapshot's 286 filing ids for the 18 holdings in its window.
  
  Tiers are not compared with 28 Oct: those readings can't be recomputed without the key, and importing them would make the check circular.
- **Live (never cut):** the latest trading day, whole market, `poll` then `drain --cap-results 50` with no key. `evals/ingest_day.txt` records:
  - filings and companies;
  - how many were settled by rules;
  - how many were parked for the model, with nothing fetched for them;
  - results cuts parsed and dead, with reasons, and how many were skipped by the cap;
  - wall time.
  
  ARCHITECTURE quotes these numbers.
- **ADR 2: the ledger is the queue.**
  - **Source:** NSE scraped politely now; for real, a licensed feed behind the same `poll`, because NSE blocks cloud IPs, BSE-only companies are invisible, and terms matter.
  - **Identity and corrections:** ISIN across exchanges; lookback and revisions for late and amended filings; leases.
  - **Retiring `build_push.py`:** once a keyed live day shows the same tiers on the same readings.
- Commit.

### Step 3. Price reaction: a year of NSE filings audits FINN's interrupt policy
Files: `pipeline/build_reaction.py` (≤ 150 lines), `evals/run_reaction.py` (≤ 170 lines), `docs/PRICE_REACTION.md`, `docs/img/reaction.png`. The word "material" is never used: under SEBI LODR Reg 30 it means something else.
- **C1, the event study.**
  - **Event day:** the first session whose close follows the filing.
  - **Abnormal return:** the stock's return over the event day and the next, from NSE's adjusted previous close, minus the universe median on each day. It is divided by the stock's own σ times √2. σ comes from the prior 60 sessions, leaving out days the company filed anything not routine.
  - **Reacted:** |z| ≥ 3, or a close at a band limit. A band limit means close equal to high or low with |r| within 0.1 point of 2, 5, 10 or 20%; it is flagged, because a lock caps |z|.
  - **Second label:** volume at least 3× its prior 20-session median.
  - **Adjustment days are excluded:** the adjusted previous close differs from the prior close by more than 0.5%. Checked on one known split.
  - **Universe:** at least 60 sessions of history and a median turnover of ₹1 crore a day.
  - **Alignment, the stop rule:** for results filings, mean |z| over event days −5…+5 must peak at day 0 or +1, above every other day. It is plotted by filing time (before open, in session, after close).
  - **Reverse-causal filings,** reported apart and never named as misses: Spurt in Volume, Price movement, News Verification, Reg 30(11) rumour verification, clarifications, SAST and insider disclosures.
  - **Audit population:** subjects the rules settle. Categories whose tier depends on a model reading are reported as "not audited: needs the reading": vague filings, people for management changes, size for deals. Their reaction rates are shown, with no verdict on the tier.
  - **Rates:** reaction rate and lift over no-filing company-days, with date-clustered bootstrap 95% intervals, for the rule tiers, each category and each NSE subject. n < 200 is marked too few.
  - **Named misses:**
    - a fold or note subject whose interval's lower bound clears the median act subject's lift;
    - an act subject whose upper bound is under 1.5.
    
    Benjamini-Hochberg is applied across subjects, and the expected false finds are stated. Each miss is written as a proposed rule edit with its numbers.
  - **Cross-check:** reaction rates by the tiers FINN shipped on the 286 snapshot filings, with the small n stated.
  - **Decision, now:** the study never reorders Today. A rule changes only through a reviewed edit, because the tiers rank what a long-term investor must look at, and the market's reaction is evidence for that, not its definition.
- **C2, the text model,** on vague filings, the population a model reads today.
  - **Model:** logistic regression on TF-IDF of NSE's subject text (`attchmntText`, not the PDFs), fit on train only with company names stripped, plus subject, filing time and size; and an ablation without the text.
  - **Split by time:** train Nov to Jun, choose C on Jul, test Aug to 28 Oct.
  - **Metrics,** ranked within each day: PR-AUC, and recall at the top 10% per day against the subject's base rate. Date-clustered intervals, quantile calibration.
  - **Use:** its heaviest words become proposed rules. No model runs at serving time. Weights are saved as JSON.
- **Not a trading signal:** directionless, and FINN gives no advice.
- **Committed:** aggregates and `evals/reaction_result.txt`; the company-day table if ≤ 5 MB.
- `PRICE_REACTION.md` holds the decision, the proposed edits and "revisit when". Commit after C1, and again after C2.

### Step 4. Answering a question: workflow first, agent on escalation (`finn/agent/`, about 270 lines)
- **Questions file, committed before `search` exists:** `evals/agent_questions.json`.
  - 20 questions over five built companies whose calls all read. Half are reworded from ledger quotes; half were written from reading call pages. Each is labelled with the page that answers it, and authorship is stated.
  - 6 questions the calls can't answer.
- **`tools.py`:** `calls(symbol)`; `search(symbol, query)` (BM25 over the last four calls' pages, in code); `read(symbol, period, page)`; `numbers(symbol, metric, quarter)`.
  - **No tool takes a URL.** A period must be in the company's own list, and a page must be in range.
  - **Results** are cut to 4,000 characters and marked as filing text, not instructions.
- **An answer is evidence, not prose.**
  - **Quote item:** {label ≤ 8 words, period, page, quote}. The quote must be on the cited page ±1: the page `verify_quote` returns is compared with the cited one. The screen shows the quote verbatim under its label, so a model sentence can't misstate it.
  - **Number item:** {metric, quarter, change}. Code looks the numbers up and writes the sentence, with the direction included.
  - **One failed item rejects the answer.**
- **`runtime.py`, one loop for both paths.**
  - **Workflow:** a plan written in code. `search` on the question takes the top 5 pages, then one flash-lite call, then verification.
  - **Agent:** the model picks the tools, with at most 6 steps, 10 tool calls and 60k input tokens, then verification.
  - **Order:** the workflow runs first. If it's rejected or empty, the agent runs once. If that fails too, the answer is "Not in the calls I read."
  - **Tools by plane:** tools are registered with a plane, and a private one is refused.
  - **Trace:** JSONL, holding a hash of the question, never its text.
  - **Privacy:** questions are private by default. Only the eval's own published questions pass `public=True`.
- `llm.py` gains `chat(messages, tools)`: Gemini function calling, the key in a header, fixed codes.
- **`evals/run_agent.py`**, offline by default:
  - **Guardrails:** an unknown tool, a URL argument, a period not in the list, a private tool, a seventh step, an oversized result.
  - **Doctored items:** a quote cited to another page, a quote with a number changed, a number item with the wrong direction, an unknown metric, one bad item among good ones.
  - **Retrieval:** recall at 5 on the 20.
  - **End to end:** a scripted run of the whole loop.
  
  **`--live`** (with a key), run twice on the 26 questions:
  - **Paths compared:** the workflow alone against the workflow followed by the agent.
  - **Measures:** grounded answers; correct "not in the calls" on the 6; the rejection rate before verification; cost and steps per question.
  - **Hand judgment:** every answer the agent adds is judged correct or not by hand.
  - **Rule, written now:** the agent stays only if, in both runs, it adds at least 4 correct answers out of 20 at no more than 3× the workflow's mean cost. Otherwise it is deleted, and ADR 3 says so.
- **`run_security.py` adds:**
  - `finn/agent` and `finn/ingest` import nothing from `finn/network`;
  - no tool schema has a URL field;
  - a private tool is refused;
  - private text is refused on free terms;
  - a trace holds no question text.
- **ADR 3: workflow first, the agent on escalation.**
  - Why November's "no agents" changed: a question's path depends on what's found, and every item can now be checked.
  - BM25, not a vector store, until questions cross companies.
  - The keep-or-delete rule.
- Commit.

### Step 5. The gate (`evals/gate.py`, `evals/gate.json`)
- **Offline floors,** at the committed values minus a tolerance:
  - security and network: all;
  - quotes: ≥ 74/80 (skipped if its PDFs aren't cached and there's no network);
  - ingest and agent offline: all;
  - reaction: alignment passes, and every headline rate sits inside the committed interval.
- **Fingerprints:** every model step's prompt, schema and model id is hashed.
  - **Unchanged:** passes.
  - **First seen:** "unvalidated", shown as a skip.
  - **Changed from a validated value:** red until `--live` passes and re-records it. This is what goes red when flash-lite is upgraded.
- **`--live` floors, written in `gate.json`:**
  - classify category ≥ 21/24 and tier ≥ 20/24, with agreement between two runs ≥ 22/24;
  - the agent's grounded answers at no less than the first live run's count minus 2, recorded when that run happens.
- **Skips:** a skip prints its reason and never counts as a pass.
- **ADR 4: code checks every model output, and evals are the merge gate.**
- Commit.

### Step 6. Close (runs even after a noon stop)
- **`docs/INTERVIEW_DEFENSE.md`** (≤ 1,500 words, about 15 questions, the weakest first; written last).
  - **"What did you get wrong" leads,** with mistakes the app shipped with, each checked against the repo before it's written: the grade endpoint trusted the phone; the model key travelled in a URL; 17 of 20 hand-checked grades held; invented profile years sat beside real executives' filings; grading falls back to flash-lite when the free quota runs out.
  - **The plan's own near-misses,** in one line: questions to a model, a circular replay check, "materiality".
  - **Each answer:** at most 90 words, with its evidence, saying "not measured" where that is the truth.
- **ARCHITECTURE:** "Where this is weak" and "For the team" finished; every number claimed in `evals/claims.py`.
- **`evals/README.md`:** a section for each new eval.
- **ROADMAP:**
  - task 0 done;
  - what falls (above), with `trust`-as-one-sheet as the task after `writeup`;
  - `final` leaves INTERVIEW_DEFENSE out of the public snapshot unless the user says otherwise.
- **NEEDS:** the key also runs `gate.py --live` and `run_agent.py --live`.
- **Writeup plan:** an amendment note at the top of `docs/plans/writeup.md`: the covering note's architecture paragraph is ARCHITECTURE's "In 200 words", the brief trace's architecture rows change, and "next" carries the proposed rule edits.
- **`STAGE` = `plan writeup`.** Commit.

### Verification (numbers that decide)
- **Archive:** ≥ 150,000 filings, 1,500 companies, 240 sessions; no day at a round cap.
- **Ingestion:**
  - `run_ingest.py`: 9/9.
  - `ingest_day.txt`: no `failed` status; done, parked, dead and skipped add up to runs.
- **Price reaction:** alignment peaks at day 0 or +1 (else stop and fix); every rate has an interval; misses pass BH and their bounds; C2 metrics against the subject base rate, with and without text.
- **Answering:**
  - `run_agent.py` offline: every guardrail and doctored case caught; retrieval recall at 5 reported.
  - `--live` only if a key appears.
- **Existing evals:** `run_security.py` +6 checks, all ok; `run_network.py` 225/225; `run_classify` untouched (its prompt is byte-identical).
- **Gate:** `gate.py` exits 0 and lists its skips and unvalidated fingerprints.
- **Claims:** `claims.py` clean for ARCHITECTURE.

### Files
- **New:**
  - `pipeline/{archive,ingest,build_reaction}.py`
  - `finn/ingest/{__init__,store,steps,worker}.py`
  - `finn/agent/{__init__,__main__,runtime,tools,verify}.py`
  - `evals/{run_ingest,run_reaction,run_agent,gate}.py`, `evals/{gate.json,agent_questions.json,ingest_day.txt,reaction_result.txt}`
  - `docs/PRICE_REACTION.md`, `docs/img/reaction.png`
  - `docs/adr/000{1..5}-*.md`, `docs/INTERVIEW_DEFENSE.md`
- **Changed:**
  - `finn/llm.py`; `finn/classify.py` (`read_batch`); `finn/triage.py` (`tier_from_people`, `downgrade`)
  - `finn/people.py`, `finn/explain.py`, `finn/ledger.py` (pass `public=True`)
  - `evals/run_security.py`, `evals/claims.py`, `evals/README.md`
  - `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`
  - `docs/ROADMAP.md`, `docs/NEEDS_FROM_USER.md`, `docs/plans/writeup.md`, `docs/STAGE`

### Not in this task
- The agent in the app.
- Rule edits from the audit (proposed only).
- Deleting `build_push.py`.
- Any app change or deploy.

## Round 3 critiques of v3 (12 Nov): 8.5, 8.5, 8, 8
- **Investor and designer (8.5).** `trust` won't run on "if time remains": write ADR 1's "who reads what" as app copy so the sheet is an hour's paste, schedule it for 13 Nov evening, and let `final` absorb it. The agent is 270 unmeasurable lines that its own rule will likely delete; cut it before C2. Lead with one number: act days react N× as often as no-filing days, with its interval and the chart. Put a time on every step and set an archive floor. Draw the diagram in the app's colours and type, ≤ 9 boxes, legible at 390 px. Keep leases and fingerprints off the first screen.
- **ENAM grader (8.5).** A cut-off can lose never-cut items: the gate runs after the cuttable agent, there are no clock deadlines, and nothing covers NSE throttling the archive. The 1,500-word cap endangers the brief's own named examples (name linking, retention, consent), so carry them over. Price the whole-market day from measured cost, and state the model routing. Enforce the ADR template (≥ 2 rejected options, a numeric revisit trigger) in `claims.py`. Ask for a free key now, for public-text live runs. Decide now whether INTERVIEW_DEFENSE ships.
- **ENAM CTO (8).** A per-investor KMS key can't cover one Cloud SQL instance. Envelope-encrypt overlay rows, caches and exports in the app with per-investor data keys wrapped by KMS; destroying the wrapping key is the erasure (DPDP). A bucket can't be shared "into" a perimeter: put it inside the private perimeter, with an ingress rule for the exporter's service account. BH needs p-values. The keep rule ignores wrong answers: hand-judge both paths, count net gain, cap false answers to unanswerable questions. Same-day filings need an attribution rule. Left unanswered: interrupts a week for a 20-stock book; cost from measured counts; why build an agent you can't measure.
- **Staff engineer and security architect (8).** `run_security.py:161` calls `generate("ping")` without `public=True`, so three key checks would fail. Size divides by TTM revenue, four quarters summed (`triage.py:38-40`, `build_push.py:38-39`). A failed explain keeps the rule tier (`triage.py:34-35`); only a failed people reading becomes "note". Results selection uses read's category for vague board outcomes, so check 7 is wrong as written. `first_cut` returns None while XBRL lags, behind a 6-hour cache. A bare hash of a short question can be reversed. Private answers would hit the disk cache. "Verbatim" shows the model's string, which fuzzy matching forgives. The gate passes vacuously without a key: seed validated fingerprints from committed live runs, hash the fallback chain, flag a degraded model. Also missing: lease fencing, σ from abnormal returns, an unpark rule.

### Decisions on round 3
All taken. Four calls:
1. **The agent loop becomes designed.** It is built in `ask` only once a key exists, and ADR 3's keep rule is written now. Orchestration runs in the ledger, tool use runs in the checked workflow, and nothing unmeasurable is built.
2. **The order puts the JD's core first:** ledger, event study, gate, answering workflow, then C2 (the ML model) last. ML is the JD's "highly desirable"; the rest is its "adept at".
3. **INTERVIEW_DEFENSE is the user's preparation and stays out of the public snapshot** unless the user says otherwise. The grader gets its hardest five as "Where this is weak". This is decided now and goes in ROADMAP.
4. **`trust` is scheduled,** not left to "if time remains".

## v4 (12 Nov)

### The idea (ARCHITECTURE opens with it, and claims only what runs)
No model ever sees what you hold or who you know. What you ask reaches a model only under terms that forbid training on it, never with your holdings or your name, and it isn't stored. What the market publishes is read once for everyone, in small checked steps over a stream of filings. A year of the whole market's filings and prices measures how well FINN's rules pick what interrupts you. A question about a company is answered by a fixed workflow whose every quote is checked on its page. An agent that chooses its own reading is designed, and will be built only when it can be measured against that workflow.

### Built and designed
| Area | Running after this task, with its check | Designed only |
|---|---|---|
| Ingestion | SQLite ledger running FINN's filing policy as fingerprinted steps; one whole-market NSE day ingested and priced | Licensed feed; Cloud SQL as the queue |
| ML | A year of every NSE filing and price; an event study auditing the rule tiers; interrupts a week for a 20-stock book; a text model on the filings a model reads | Scheduled retraining |
| Answering | Checked workflow on a tool registry with planes; quotes shown as the page's own text; numbers written by code; offline evals | The agent escalation and its keep rule; the Pull screen (task `ask`) |
| Reliability | `gate.py`: floors, fingerprints seeded from committed live runs, `--live` with written floors | Nightly run |
| Privacy | Model calls private by default; private calls never cached; traces carry nothing derived from the question | Two GCP projects; envelope encryption with per-investor keys |
| Cloud | | GCP `asia-south1`, costs from measured counts |

No app change, nothing to deploy.

### Schedule, cuts, what falls
- **Deadlines (IST),** assuming a start by 12 Nov 05:00. A later start shifts steps 0–5 by the delay, and C2 and INTERVIEW_DEFENSE's length absorb it; step 7 stays at 12:00.
  - Step 0: 06:00. Step 1: 10:00. Step 2: 18:00.
  - Step 3: 13 Nov 00:00. Step 4: 02:00. Step 5: 07:00. Step 6 (C2): 09:30. Step 7 (close): 12:00.
  - At a deadline the step lands in its smallest working form, or its unfinished part is relabelled "designed" in ARCHITECTURE, the ADRs and the diagram. Every commit leaves the documents true.
- **Cut order:**
  1. C2.
  2. Step 5 down to the tools, the verifier and their offline evals.
  3. INTERVIEW_DEFENSE down to 10 questions.
- **Never cut:** the live market day, ARCHITECTURE, the five ADRs, the ledger and its checks, C1 and its two headline numbers, the gate. Step 7 runs whatever happened before it.
- **Archive floor:** if under 6 months of filings or prices have arrived when step 3 starts, step 3 runs on what's there and every number states its coverage.
- **Size:** about 900 new lines outside evals. ARCHITECTURE ≤ 2,200 words outside folds; ADRs ≤ 300 words each; PRICE_REACTION ≤ 600; INTERVIEW_DEFENSE ≤ 1,500.
- **What falls, written plainly in ROADMAP:**
  - `writeup` runs on the afternoon of 13 Nov.
  - `trust`, as one sheet, runs that evening. It is pasted from ADR 1's "What the app says", about an hour's work, and `final` (from 14 Nov) absorbs it if it slips.
  - `network-loop`, `annual-report` and `ask` don't run before the deadline.

### Step 0. Live check; archive in the background; ask for a key (by 06:00)
- The ROADMAP live check.
- **`pipeline/archive.py`** (≤ 80 lines): resumable, one request a second, and a manifest of counts per day. A day that returns a round number of filings is refetched in halves.
  - **Filings:** NSE announcements for every company, 1 Nov 2025 to 28 Oct 2026, one gzip per day under `data/raw/` (git-ignored).
  - **Prices:** bhavcopy from 1 Aug 2025 to 30 Oct 2026, EQ and BE rows: ISIN, open, high, low, close, previous close, volume and turnover.
- **NEEDS, now, not at close:**
  - a free AI Studio key unlocks the public-text live runs (classify floors, `gate.py --live`);
  - a paid-terms key unlocks the question path.
  - If a key appears during this task, run `gate.py --live` and record the result.

### Step 1. ARCHITECTURE first; ADRs 1 and 5; privacy in code (by 10:00)
- **`docs/ARCHITECTURE.md`, rebuilt in this order:**
  1. "In 200 words" (for the covering note; its lead number arrives with step 3);
  2. the idea;
  3. the brief's four headings, each with "Running now" and "For real";
  4. §5 Price reaction;
  5. "Where this is weak" (5 items: the hardest interview questions, in public form);
  6. "For the team" (≤ 250 words: what a model step, a tool and a source must meet before merge, and the gate).
  - **Carried over unchanged:** name-to-contact linking (same, different, possible), the retention table and consent.
  - **The first screen stays plain:** leases, fingerprints and queue mechanics live in folds and ADRs.
  - Parts not built yet say "designed". Each step rewrites its own section when it lands.
- **Diagram** (`docs/img/architecture.svg` + 2× PNG), in DESIGN.md's colours and type, ≤ 9 boxes, legible at 390 px wide:
  - archive → events → steps (rules, model, code) → facts → views;
  - the private overlay below the line, with one arrow down: a read-only facts export;
  - the answering box beside the facts, reading public pages only;
  - production names small under each box.
  - Running is solid, designed is dashed; a box turns solid in the commit that builds it.
- **ADR template, checked by `claims.py`:** five headings: Context; Options (at least two rejected, each with why); Decision; Trade-offs; Revisit when (with a number).
- **ADR 1, three kinds of data:**
  - **Public filings:** a model may read them, once for everyone; free terms are allowed.
  - **What you hold and who you know:** code only, never a model; this lives in the private project (ADR 5).
  - **What you ask:** a model reads it only on paid terms with no training. In production a stateless answering service in the public project gets the question and the symbol, never an investor id (the edge checks the sign-in). It logs codes and timings, keeps nothing and caches nothing. Vertex request logging is off.
  - **Region:** whether flash-lite is served from `asia-south1`, settled in one lookup. If it is served only globally, the ADR says so and names the regional model that would replace it.
  - **Revisit when:** a feature needs a model to see holdings. The answer then is on-device, or a model in the private project with no egress.
  - **"What the app says":** three plain lines per kind of data, written as app copy, ready for the `trust` sheet.
- **ADR 5, production on GCP,** region `asia-south1`, recovery in `asia-south2`:
  - **Ingestion:** Cloud Scheduler starts Cloud Run jobs. The ledger in Cloud SQL is the queue: a claim is a short transaction that sets a lease with `SKIP LOCKED`, no lock is held through a model call, expired leases are reclaimed, and completions are fenced by lease token. Cloud Storage holds the raw archive.
  - **Public project:** ingestion and the answering service, which reaches Vertex through workload identity, so there is no model key.
  - **Private project:** the overlay.
    - Vertex is disabled.
    - Egress is denied: no NAT, a deny-all egress firewall rule, and Private Service Connect for Cloud SQL and KMS.
    - A VPC Service Controls perimeter surrounds it, with no egress rules.
    - The facts export bucket sits inside the perimeter, and one ingress rule lets only the exporter's service account write to it. That is the one crossing, and it points inward.
  - **Keys and erasure:** the app envelope-encrypts each investor's overlay rows, caches and exports with a data key wrapped by that investor's KMS key. Destroying that key version erases every copy, backups included. That meets the DPDP Act's erasure duty without rewriting backups. Erasure takes the scheduled-destroy delay (at least 24 hours).
  - **Access and limits:** Identity Platform with the firm's sign-in; Cloud Armor limits per user.
  - **Cost:** a monthly table at whole-market scale built from measured counts (step 2's day, step 5's tokens per question), with list prices dated (≤ 3 lookups, shared with the region check).
  - **Options rejected:** AWS or Azure; Kubernetes; Pub/Sub (revisit at fan-out or about 100 events a second); staying on Vercel.
- **`finn/llm.py`:**
  - `generate` treats text as private by default. Public text needs `public=True`, which `classify`, `people`, `explain`, `ledger` and `evals/run_security.py:161` now pass.
  - Private text raises `LLMError("terms")` unless `FINN_MODEL_TERMS=paid`. That flag is a guard against accidents; the real control is Vertex in production.
  - Private text is never cached, whatever `cache` says.
  - Prompts and the public cache key are unchanged.
  - **`run_security.py` checks:** public text passes; private text is refused on free terms; private text on paid terms writes nothing to the disk cache.
- Commit.

### Step 2. The ledger runs FINN's filing policy (`finn/ingest/`, about 280 lines; by 18:00)
- **`store.py`** (SQLite, under `data/cache/`):
  - **`events(kind, id, rev, hash, at, symbol, isin, payload)`:** the hash covers fixed fields only (symbol, subject, attachment text, attachment URL, time, ISIN), so a cosmetic change in NSE's JSON doesn't re-bill the model. A real change becomes a new revision.
  - **`runs(kind, id, rev, step, fp, status, attempts, lease, lease_until, not_before, model, output, error)`:** `fp` = hash(step version, prompt, schema, model asked, fallback chain, and the `fp` and status of every step it reads). A stored `fp` that differs from the current one makes the run pending again.
  - **`facts(key, value, fp, event)`:** the results first cut, and TTM revenue as of the quarter (four quarters summed, as `build_push.py` does), both keyed (symbol, quarter).
  - No high-water mark: `poll` re-reads a 3-day lookback, and inserts are idempotent.
- **`steps.py`:** every decision `build_push` and `triage.enrich` make, each step calling the existing function:
  1. **rules:** `classify.by_rule`.
  2. **read:** vague filings, in batches of 20, through `classify.read_batch`. Its prompt is byte-identical to today's, so classify's fingerprint and cache survive. It raises; `classify.classify` keeps its fallback by catching around it. A partial batch leaves the missing filings pending.
  3. **results:** for results filings at act (category and tier from rules or read), `first_cut(symbol, quarter_end)`, with the quarter taken from the filing's date. While XBRL lags it returns `None`, which is `not_yet`: retried at every drain with the listing cache bypassed, and `dead: no_xbrl` 60 days after the quarter ends. One fact per (symbol, quarter).
  4. **people:** management changes not at fold.
  5. **explain:** `enrich_line`'s selection.
  6. **size:** code. The amount over TTM revenue as of the quarter, fetched only when explain found an amount.
  7. **tier:** code. `triage.tier_from_people` and `triage.downgrade`, extracted from `enrich`, which uses them too.
     - A parked input counts as an input. Tier proceeds the way today's code does when that step fails: people parked → note, "not read"; explain parked → rule tier kept, marked unsized; read parked → note, "not read".
     - Tier re-runs when the input lands, because the input's status is in its `fp`.
- **Statuses:**
  - **done** and **pending**;
  - **parked:** `no_key`, `quota` (with `not_before`), `terms`;
  - **blocked:** a step that can't tell whether it applies while an input is parked, e.g. people when read is parked;
  - **not_yet;**
  - **degraded:** the model recorded differs from the one asked; re-run when a key allows;
  - **dead:** `not_pdf` and `too_big` at once; anything else after 5 tries.
  - `has_key()` is checked before a model step fetches a PDF. With no key the step parks without fetching.
  - **Unparking:** `drain` starts by moving `no_key` runs to pending when a key exists, and `quota` runs once `not_before` has passed.
- **`worker.py`:** claims with a lease token, works outside the claim, and a completion writes only if its token still holds. Drains step by step, so batches survive, and fetches 4 at a time.
- **`pipeline/ingest.py`:** `poll [--days 3]`, `drain [--cap-results 50]`, `status`, and `view` (filings in push.json's shape, written to `data/out/`, never to `web/public/`).
- **`evals/run_ingest.py`** (no key, no network; real archive rows, fetches stubbed):
  1. Two polls of a window store each filing once.
  2. A cosmetic payload change makes no revision; a real change makes revision 2, which re-runs its steps.
  3. Two failures then a success end done; five failures end dead; `not_pdf` is dead at once; other filings are untouched.
  4. A worker killed mid-step leaves a lease that expires; the run is reclaimed and done once. When the slow original finishes late, it writes nothing.
  5. A partial batch leaves the missing filings pending.
  6. With no key, every model step is parked or blocked, none failed or fallback, and nothing is fetched for them. The view shows each filing the way today's code does when that step fails. With a key stubbed in, `drain` unparks them.
  7. Changing read's prompt re-runs read and its dependants (people, explain, size, tier, and results only for filings that read categorised), never rules or the other results.
  8. Results arriving in any order, and a `not_yet` followed by a cut, give one fact per (symbol, quarter).
  9. The archive holds the snapshot's 286 filing ids for the 18 holdings in its window.
  10. A filing whose explain step parks keeps its rule tier, marked unsized, matching `triage.enrich` on the same stubbed failure.
  
  Tiers are not compared with 28 Oct: without the key that comparison is circular.
- **Live (never cut):** the latest trading day, whole market, `poll` then `drain --cap-results 50` with no key. `evals/ingest_day.txt` records:
  - filings and companies;
  - how many were settled by rules;
  - how many were parked for a model, with nothing fetched;
  - results cuts done, not_yet and dead (with reasons), and how many the cap skipped;
  - wall time;
  - the statuses, which must sum to runs;
  - **₹ for the day had the key been there:** the parked count × the snapshot's measured cost per filing read, with the price date.
- **ADR 2: the ledger is the queue.**
  - **Options rejected:** Pub/Sub with a separate state store; a cron batch (today's `build_push`).
  - **Source:** NSE scraped politely now; for real, a licensed feed behind the same `poll`, because NSE blocks cloud IPs, BSE-only companies are invisible, and terms matter.
  - **Identity and corrections:** ISIN across exchanges; lookback and revisions; leases and fencing.
  - **Retiring `build_push.py`:** once a keyed live day shows the same tiers on the same readings.
  - **Revisit when:** about 100 events a second, or a second consumer of events.
- Commit.

### Step 3. Price reaction: a year audits FINN's interrupt rules (by 13 Nov 00:00)
Files: `pipeline/build_reaction.py` (≤ 170 lines), `evals/run_reaction.py` (≤ 170), `docs/PRICE_REACTION.md`, `docs/img/reaction.png` (in DESIGN.md's colours). The word "material" is never used: under SEBI LODR Reg 30 it means something else.
- **Unit: the company-day.**
  - **Event day:** the first session whose close follows the filing. The window covers that day and the next, because results filed at 15:00–15:29 react on day +1.
  - **Attribution:** a company-day is credited to its highest-tier filing. Per-subject rates use days with that subject alone; mixed days are counted and reported apart.
- **Abnormal return:** the stock's return over the event day and the next, from NSE's previous close, minus the universe median on each day. z = that ÷ (σ√2), where σ comes from the prior 60 sessions' abnormal returns, leaving out days with a filing that isn't routine.
- **Reacted:** |z| ≥ 3, or a close at a band limit: close equal to high or low, with |r| within 0.1 point of 2, 5, 10 or 20%. Band closes are flagged, because a lock caps |z|.
  - **Second label:** volume at least 3× its prior 20-session median.
- **Excluded:** adjustment days, where the previous close differs from the prior close by more than 0.5%. Checked on one known split.
- **Universe:** at least 60 sessions of history and a median turnover of ₹1 crore a day.
- **Alignment, the stop rule:** for results filings, mean |z| over days −5…+5 must peak at day 0 or +1, above every other day. It is plotted by filing time (before open, in session, after close).
- **Reverse-causal filings,** reported apart and never named as misses: Spurt in Volume, Price movement, News Verification, Reg 30(11) rumour verification, clarifications, SAST and insider disclosures.
- **Audit population:** subjects the rules settle. Model-dependent ones (vague filings, people for management changes, size for deals) are "not audited: needs the reading", shown with their reaction rates and no verdict.
- **Rates:** reaction rate and lift over no-filing company-days, with date-clustered bootstrap 95% intervals, for the rule tiers, each category and each subject. n < 200 is marked too few.
- **Named misses:**
  - **Method:** for each subject, the date-clustered bootstrap distribution of its lift minus the bar; one-sided p-values; Benjamini–Hochberg at q = 0.10 across subjects; FCR-adjusted intervals for those kept, with the expected false finds stated.
  - **Bars:** a fold or note subject whose lift exceeds the median act subject's; an act subject whose lift is under 1.5.
  - Each miss is written as a proposed rule edit with its numbers.
- **Two headline numbers,** carried into "In 200 words", the covering note and the chart:
  - "On days FINN's rules say act, the stock reacted N× as often as on days with no filing (95% CI a–b)."
  - **Interrupts a week for a 20-stock book:** over random 20-stock books drawn from the 500 most traded, the median and 90th percentile of act days a week. Given as a range: from rule-settled filings only, up to every model-dependent filing at act. Also the share of them that moved the price.
- **Cross-check:** reaction rates by the tiers FINN shipped on the 286 snapshot filings, with the small n stated.
- **Decision:** the study never reorders Today. A rule changes only through a reviewed edit, because the tiers rank what a long-term investor must look at, and the market's reaction is evidence for that, not its definition.
- `PRICE_REACTION.md` holds the method, the results, the proposed edits and "revisit when". Commit.

### Step 4. The gate (`evals/gate.py`, `evals/gate.json`; by 02:00)
- **Offline floors,** at the committed values minus a tolerance:
  - security and network: all;
  - quotes: ≥ 74/80 (skipped if its PDFs aren't cached and there's no network);
  - ingest: all;
  - reaction: alignment passes, and every headline rate sits inside its committed interval.
- **Fingerprints:** every model step's prompt, schema, model and fallback chain is hashed.
  - **Seeds:** classify and quotes start validated where an AST comparison shows those constants, and the models in config, identical to the commit that recorded `classify_result.txt` and `quotes_result.txt`. Anything else starts first seen.
  - **Validated and unchanged:** passes.
  - **First seen:** "unvalidated", shown as a skip.
  - **Changed from a validated value:** red until `--live` passes and re-records it. This is what goes red when flash-lite is upgraded.
- **`--live` floors, written in `gate.json`:**
  - classify category ≥ 21/24 and tier ≥ 20/24, with agreement between two runs ≥ 22/24;
  - the workflow's grounded answers at no less than its first live run minus 2, recorded when that run happens.
- **Skips:** a skip prints its reason and never counts as a pass.
- **ADR 4: code checks every model output, and evals are the merge gate.**
  - **Options rejected:** an LLM as judge; human spot checks alone.
  - **Revisit when:** a step's output can't be checked by code. Then it needs a held-out set of at least 50 labelled by hand.
- Commit.

### Step 5. Answering a question: the checked workflow (`finn/answer/`, about 220 lines; by 07:00)
- **Questions file, committed before `search` exists:** `evals/answer_questions.json`.
  - 20 questions over five built companies whose calls all read. Half are reworded from ledger quotes; half were written from reading call pages. Each is labelled with the page that answers it, and authorship is stated.
  - 6 questions the calls can't answer.
- **`tools.py`:** a registry in which each tool carries a plane, and a private one is refused.
  - **Tools:** `calls(symbol)`; `search(symbol, query)` (BM25 over the last four calls' pages, in code); `read(symbol, period, page)`; `numbers(symbol, metric, quarter)`.
  - **Arguments:** no tool takes a URL. A period must be in the company's own list, and a page must be in range.
  - **Results:** cut to 4,000 characters and marked as filing text, not instructions.
- **An answer is evidence, not prose.**
  - **Quote item:** {label ≤ 8 words, period, page, quote}. `verify_quote` must find the quote on the cited page ±1. The screen shows the page's matched span, not the model's string, under the model's label.
  - **Number item:** {metric, quarter, change}. Code looks the numbers up and writes the sentence, direction included.
  - **One failed item rejects the answer,** and a rejected answer becomes "Not in the calls I read."
- **`workflow.py`:** `search`, then the top 5 pages, then one flash-lite call with structured output, then verification.
  - **Privacy:** questions are private by default. Only the eval's own published questions pass `public=True`.
  - **Trace:** JSONL with a random id, codes, timings and token counts, and nothing derived from the question.
- **`evals/run_answer.py`,** offline, with the model call stubbed by recorded or doctored outputs:
  - **Guardrails:** an unknown tool, a URL argument, a period not in the list, a private tool, an oversized result.
  - **Doctored items:** a quote cited to another page, a number changed inside a quote, swapped words, the wrong direction, an unknown metric, one bad item among good ones.
  - **Retrieval:** recall at 5 on the 20, the real offline measure.
  - **End to end:** one run through a stub.
  - **Tokens per question,** counted from the 5 pages; this feeds ADR 5's cost table.
  - **`--live`** (with a key): the 26 run twice, recording grounded answers, correct "not in the calls" on the 6, the rejection rate before verification, and cost.
- **`run_security.py` adds:**
  - `finn/answer` and `finn/ingest` import nothing from `finn/network`;
  - no tool schema has a URL field;
  - a private tool is refused;
  - a trace holds neither the question's text nor a hash of it.
- **ADR 3: a checked workflow, with the agent designed.**
  - **Why:** November's "no agents" still holds for building. What would change it is a question whose path depends on what's found.
  - **Options rejected:** an agent loop now (it can't be measured without a key, and its own keep rule would likely delete it); a vector store (BM25 is enough until questions cross companies).
  - **Designed escalation:** a rejected answer retries once on flash, then the agent runs over the tools above (≤ 6 steps, 10 tool calls, 60k input tokens).
  - **Keep rule, written before any number exists:** both paths are hand-judged on the 26, over two runs. The agent stays only if it adds at least 4 net correct answers (or recovers half the workflow's misses when there are fewer than 8), gives at most 1 false answer on the 6 unanswerable questions, and costs no more than 3× the workflow's mean.
  - **Revisit when:** a key exists (task `ask`).
- Commit.

### Step 6. C2, the text model (by 09:30; first to be cut)
- **Population:** vague filings, the ones a model reads today.
- **Model:** logistic regression on TF-IDF of NSE's subject text (`attchmntText`), fit on train only with company names stripped, plus subject, filing time and size. An ablation without the text.
- **Split by time:** train Nov to Jun, choose C on Jul, test Aug to 28 Oct.
- **Metrics,** ranked within each day: PR-AUC, and recall at the top 10% per day against the subject's base rate. Date-clustered intervals; calibration by quantile.
- **Use:** its heaviest words become proposed rules. No model runs at serving time; the weights are saved as JSON. Not a trading signal.
- **Committed:** aggregates and `evals/reaction_result.txt`; the company-day table if ≤ 5 MB. Commit.

### Step 7. Close (by 12:00; runs whatever happened before)
- **`docs/INTERVIEW_DEFENSE.md`** (≤ 1,500 words, about 15 questions, weakest first):
  - **"What did you get wrong" leads,** with mistakes the app shipped with, each checked against the repo before it's written: the grade endpoint trusted the phone; the model key travelled in a URL; 17 of 20 hand-checked grades held; invented profile years sat beside real executives' filings; grading falls back to flash-lite when the free quota runs out.
  - **The plan's near-misses,** in one line: questions to a model, a circular replay check, "materiality", an agent it couldn't measure.
  - **Each answer:** at most 90 words, with its evidence, saying "not measured" where that is the truth.
  - **The CTO's three are included:** interrupts a week, cost per day and per question from counts, and why the agent isn't built.
- **ARCHITECTURE:** "Where this is weak" and "For the team" finished. Every number is claimed in `evals/claims.py`, which also checks the five ADR headings.
- **`evals/README.md`:** a section for each new eval.
- **ROADMAP:**
  - task 0 done;
  - what falls, and `trust` scheduled for 13 Nov evening;
  - INTERVIEW_DEFENSE out of the public snapshot (decided; the user may override).
- **NEEDS:** the keys (free for public text, paid for questions) and what each unlocks: `gate.py --live`, `run_answer.py --live`, and building the agent.
- **Writeup plan:** an amendment at the top of `docs/plans/writeup.md`:
  - the covering note's architecture paragraph is "In 200 words", with the headline number;
  - the brief trace's architecture rows change;
  - "next" carries the proposed rule edits.
- **`STAGE` = `plan writeup`.** Commit.

### Verification (numbers that decide)
- **Archive:** ≥ 150,000 filings, 1,500 companies, 240 sessions; no day at a round number, or the archive floor rule applied and stated.
- **Ingestion:** `run_ingest.py` 10/10. In `ingest_day.txt` the statuses sum to runs, nothing is `failed`, and the ₹ figure carries its date.
- **Price reaction:** alignment peaks at day 0 or +1 (else stop and fix); every rate has an interval; misses survive BH; both headline numbers carry intervals or ranges.
- **Answering:** `run_answer.py` offline catches every guardrail and doctored case, and reports recall at 5.
- **Existing evals:** `run_security.py` all ok, including the new checks and the fixed ping; `run_network.py` 225/225; `run_classify` untouched.
- **Gate:** `gate.py` exits 0, with classify and quotes validated, and lists its skips.
- **Claims:** `claims.py` clean, ADR headings included.
- **C2:** test metrics against the base rate, with and without the text.

### Files
- **New:**
  - `pipeline/{archive,ingest,build_reaction}.py`
  - `finn/ingest/{__init__,store,steps,worker}.py`
  - `finn/answer/{__init__,tools,verify,workflow}.py`
  - `evals/{run_ingest,run_reaction,run_answer,gate}.py`, `evals/{gate.json,answer_questions.json,ingest_day.txt,reaction_result.txt}`
  - `docs/PRICE_REACTION.md`, `docs/img/reaction.png`
  - `docs/adr/000{1..5}-*.md`, `docs/INTERVIEW_DEFENSE.md`
- **Changed:**
  - `finn/llm.py`; `finn/classify.py` (`read_batch`); `finn/triage.py` (`tier_from_people`, `downgrade`)
  - `finn/people.py`, `finn/explain.py`, `finn/ledger.py` (pass `public=True`)
  - `evals/run_security.py` (line 161 among them), `evals/claims.py`, `evals/README.md`
  - `docs/ARCHITECTURE.md`, `docs/img/architecture.{svg,png}`
  - `docs/ROADMAP.md`, `docs/NEEDS_FROM_USER.md`, `docs/plans/writeup.md`, `docs/STAGE`

### Not in this task
- The agent loop.
- Any app change or deploy.
- Rule edits from the audit (proposed only).
- Deleting `build_push.py`.

## Round 4 critiques of v4 (12 Nov): 9, 9, 9, 8.5
- **Investor and designer (9).** There should be one lead number, not two, and the plan should say now what leads if it's weak. The archive floor isn't a floor: below some coverage, keep the headline out. Named misses have no place in the cut order. Nothing verifies what the grader sees first: the diagram at 390 px, and the lead number against its result file.
- **ENAM grader (9).** An ordering bug: `reaction_result.txt` is committed in step 6 (C2, cut first), but the step 4 gate needs it. The ADR template is half enforced: headings only, and ADR 1, 3 and 4 have no number under "Revisit when". The answering checks never enter the gate. The day's ₹ leaves out people and explain behind read.
- **ENAM CTO (9).** The 26 eval questions are public, so a *free* key measures the workflow and the agent; paid terms gate only real users' questions. "Act days vs no-filing days" flatters, since any results day moves; lead with act vs fold among filing days, and act without results. Encrypted holdings can't be indexed: say how a filing finds its holders. Erasure destroys every key version. Bootstrap B ≥ 20,000, and fix the BH family before looking. Still hard in interview: "what do your rules add beyond 'it's a results filing'?"
- **Staff engineer and security architect (8.5).**
  - **Degraded can't be detected.** The cache key uses the model asked (`llm.py:36`), while the entry stores the model that answered (`:60`). A hit logs the asked model (`:40`), and `generate` returns only the result. So a fallback answer replays forever as the asked model, and a `--live` run that fell back would validate a fingerprint.
  - **`--live` can pass from cache.** `run_classify` goes through the cache (`classify.py:126`), so "two runs agree" is 24/24 by construction.
  - **`verify_quote` is too forgiving.** It accepts a quote on any page (`pdf.py:120-122`), returns no span, and its fuzzy match can forgive swapped words.
  - **Two smaller gaps.** `results.py:63` hard-codes the 6-hour cache. The ₹ figure undercounts.

### Decisions on round 4
All taken, as the amendments below.

## v5 (12 Nov): v4 with these amendments
**The FINAL plan is v4 as amended here; where they differ, v5 wins.**

1. **The lead number** (step 3, "In 200 words", the covering note, the chart title):
   - **The one lead sentence:** "On filing days, the ones FINN's rules mark act reacted N× as often as the ones they fold (95% CI a–b); N′× leaving results out."
   - **Line two:** interrupts a week for a 20-stock book.
   - **Context only, in PRICE_REACTION:** act days against no-filing days.
   - **If it's weak** (the CI's lower bound ≤ 1, or N′ < 1.5): "In 200 words" leads with the live market day and interrupts a week, and PRICE_REACTION says plainly that, outside results, the rules can't be told apart from fold by the market's reaction. That answers "what do your rules add beyond results?" either way.
2. **Archive floor, hard:** if there's less than 3 months, or fewer than 200 act company-days, the study still runs and states its coverage. The headline stays out of "In 200 words" and the email, which lead with the live market day.
3. **Cut order,** now:
   1. C2;
   2. named misses down to the BH list, without FCR intervals;
   3. step 5 down to the tools, the verifier and their offline evals;
   4. INTERVIEW_DEFENSE down to 10 questions.
4. **Ordering:** step 3 commits `evals/reaction_result.txt` and the company-day table (if ≤ 5 MB). C2 writes its own `evals/c2_result.txt`.
5. **ADR template, fully checked:** `claims.py` asserts the five headings, at least two rejected options, and a number under "Revisit when". The triggers:
   - **ADR 1:** an on-device or private-project model reaches flash-lite's classify floor (≥ 21/24). Then features that need holdings move there. Rejected options: holdings redacted inside prompts; one project split by IAM alone.
   - **ADR 2:** about 100 events a second, or a second consumer.
   - **ADR 3:** a key exists and the agent clears the keep rule (net +4 correct, ≤ 1 false on the 6).
   - **ADR 4:** model steps whose output code can't check pass 10% of calls. Then a hand-labelled set of ≥ 50.
   - **ADR 5:** about 100k investors (a blind index), or a second region.
6. **The answering checks join the gate:** step 5 adds `run_answer.py`'s offline guardrail, doctored-item and recall-at-5 floors to `gate.json`, and Verification requires them.
7. **The day's ₹:** for each model step, parked plus blocked runs × that step's measured cost per call. People and explain behind a parked read are estimated from the snapshot's share of read filings that went on to them. It is labelled an estimate, with the price date.
8. **Keys:** a free key is enough for the public-text runs, which are classify floors, `gate.py --live`, `run_answer.py --live` on the 26 published questions, and the agent's keep-rule measurement. Paid terms gate only real users' questions. NEEDS (step 0) and ADR 3 say so. Even if a key arrives, the agent's build stays in `ask`.
9. **ADR 5, how a filing finds its holders:** at each drain, the private matcher decrypts each investor's holdings in memory. Data keys are cached for the run and never written. At the firm's scale (thousands of investors, tens of holdings each) that takes milliseconds. Revisit at about 100k investors, with a blind index (an HMAC of the symbol under a per-investor key). Erasure destroys every version of the investor's key.
10. **Statistics:** the bootstrap uses B ≥ 20,000, as date-clustered multinomial weights over per-date aggregates. The BH family (subjects with n ≥ 200 in the archive's counts) is written into `run_reaction.py` and committed before any reaction rate is computed.
11. **The model that answered, and fresh runs** (`finn/llm.py`, step 1):
    - `generate(meta=True)` returns {result, model, cached}, with the model that answered taken from the cache entry on a hit. METER logs that model too.
    - `FINN_FRESH=1` (or `fresh=True`) skips cache reads but still writes.
    - **The ledger:** model ≠ asked → `degraded`. With a key, `drain` re-runs degraded runs fresh.
    - **`gate.py --live`:** runs classify twice with `FINN_FRESH=1` (so `run_classify.py` needs no change), and fails if any call fell back.
    - **`run_security.py` adds:** a fallback answer served from cache is reported with its real model, and so becomes degraded.
12. **`finn/answer/verify.py` is its own check:**
    - the cited page ±1 only;
    - exact match after normalising;
    - no fuzzy match, and no any-page fallback;
    - it returns the raw page span through a map of offsets from the normalised text to the raw text.
    
    `pdf.verify_quote` is unchanged, so `run_quotes` stays as it is.
13. **`finn/results.py`:** `first_cut(..., ttl_hours=6)` becomes a parameter, and the `not_yet` retries pass 0. Added to Changed.
14. **Seen by the grader, verified:** the diagram is rendered at 390 px and looked at once. `claims.py` matches the "In 200 words" number to `reaction_result.txt`. ARCHITECTURE's existing model routing (cheap model for bulk, flash where it reasons) carries over.

## Round 5 critiques of v5 (12 Nov): 9.5, 9.5, 9.5, 9
- **Investor and designer (9.5).**
  - The lead sentence is too dense: give it one ratio.
  - `claims.py` must check whatever leads, live-day figures included.
- **ENAM grader (9.5).**
  - Amendments 10–13 add code without revisiting size or deadlines.
  - ADR 1's trigger is a weak proxy for handling holdings.
- **ENAM CTO (9.5).**
  - "Milliseconds" is wrong: each data key needs a KMS unwrap.
  - Reverse-causal days must leave the fold count.
  - Print n beside N′.
  - The soft spot in interview stays "show me an agent you built"; the answer is the ledger, the workflow and the keep rule.
- **Staff engineer and security architect (9).**
  - `people.from_filing` (`people.py:47-53`) and `explain.explain` (`explain.py:22`) return only the result, and a global METER mixes runs across 4 threads.
  - The ₹ figure overstates read about 20× (one call per 20 filings), and double-counts blocked runs.

### Decisions on round 5
All taken, as amendments 15–21. Every reviewer is at 9 or above with nothing substantial left, so the plan is final.

## v5, final amendments (round 5)
15. **Lead, in three lines:**
    - "On filing days FINN marks act, the stock moved N× as often as on days it folds (95% CI a–b)."
    - Then N′ (results left out) with its n.
    - Then interrupts a week.
    - Reverse-causal days are left out of both the act and the fold counts.
    - `claims.py` checks whatever leads: reaction figures against `reaction_result.txt`, and live-day figures against `ingest_day.txt`.
16. **Size and deadlines:** about 1,000 new lines outside evals, budgeted per step:
    - step 1: about 60 (privacy, `meta`, fresh);
    - step 2: about 280;
    - step 3: about 190;
    - step 5: about 250 (with `verify.py`);
    - step 6: about 90;
    - archive: about 80.
    
    The deadlines stand; the cut order absorbs any overrun.
17. **ADR 1's trigger:** a 20-item holdings-shaped eval, built when needed (questions over a synthetic book, scored on the answer and on nothing of the book leaking into logs or output). A candidate model in the private project or on the device must pass at ≥ 18/20.
18. **ADR 5, the matcher:** a long-running worker in the private project that keeps unwrapped data keys in memory for at most an hour. That makes KMS unwraps about one per investor per hour, not per drain, and their cost is priced in the table. A cold start unwraps in parallel and takes seconds, not milliseconds.
19. **Which model answered, per run:** `llm.py` records the answering model in a `contextvars` scope. The worker opens one scope per run and reads it after the step, so `people` and `explain` need no signature change and 4 threads don't mix. `run_ingest` check 11: a stubbed fallback inside explain marks that run `degraded`.
20. **₹ per day, corrected:**
    - read's cost per call is divided by its batch of 20;
    - people and explain behind a parked read are counted only through the snapshot's share, never in full as well;
    - people and explain runs already blocked on their own are counted once.
21. **Verification gains:** `run_ingest.py` 11/11.

## FINAL (12 Nov)
**The FINAL plan is v4 with v5's amendments 1–21. Where they differ, the higher-numbered amendment wins.** Execution starts at step 0 of v4.

## Execution (13 Nov)
Started 00:43 IST, about 20 hours after the plan assumed. Steps ran faster than budgeted, so nothing on the cut list was cut. C2 was built.

**Standing live check.** `index-BqOq4beW.js`, the old hash, so no app change and no e2e needed.

**What ran, step by step, with commits:**
0. **Archive.** 181,790 filings over 362 days, with no day at a round count, and 307 price sessions (`pipeline/archive.py`). NEEDS now says which key unlocks what.
1. **Privacy in `llm.py`.** Private by default, `terms`, never cached, `meta`, fresh, and `scope` for the model that answered. ARCHITECTURE rebuilt, ADRs 1 and 5, diagram, and the ADR template checked in `claims.py`.
2. **Ledger** (`finn/ingest/`). `run_ingest` 11/11. Live day 12 Nov: 987 filings, 574 companies, 759 settled by rules, 340 parked, 0 PDFs fetched, statuses summing to runs, 30 s, about ₹33. ADR 2.
3. **Price reaction.**
   - Alignment passes, peaking on day 0.
   - Act/fold 5.3× (4.7–5.9). Without results 1.1× (0.3–2.0, n 159), which is **weak under amendment 1**, so "In 200 words" leads with the live day and interrupts a week.
   - 0 of 13 misses survive BH. The BH family was committed (`ba7c30e`) before any rate.
4. **Gate.** Classify was seeded validated by AST. **Found: `run_quotes` sampled the live ledgers and had drifted (68/81 against 74/80).** The sample is pinned and reproduces 74/80. ADR 4.
5. **Answering** (`finn/answer/`). The questions were committed (`8882443`) before search existed. `run_answer` 20/20, recall at 5 17/20. Security 88/88. ADR 3.
6. **C2.** PR-AUC 0.084 (0.067–0.105), against 0.078 without the text and 0.078 for the subject's base rate. A negative result, stated as one.
7. **Close.** INTERVIEW_DEFENSE (1,292 words); ARCHITECTURE's "Where this is weak" and "For the team"; evals README; the writeup amendment; ROADMAP.

**Deviations, each written where it applies:**
- **Adjustment days.** The bhavcopy's previous close isn't adjusted for bonuses (Nestlé and HDFC Bank, Aug 2025), so a return beyond ±30% also counts. Both bonuses are verified as flagged.
- **`no_xbrl`** counts 60 days from the filing, not the quarter: a late filer at 66 days would otherwise die on first sight.
- **Quotes has no prompt.** `run_quotes` tests the verifier, so it is a floor, not a fingerprint. The seed covers classify, and the answer step was added to the fingerprints.
- **₹ a day** uses the snapshot's mean cost per call ($0.1311 for 85 calls). No per-step usage was recorded locally.
- **The region is unsettled.** The locations page renders its marks client-side. ADR 1 states the rule either way.
- **No sklearn.** Its build here fails against numpy 2, so C2 uses about 50 lines of numpy and scipy.
- **Size.**
  - About 925 new lines outside evals, against about 1,000 planned.
  - ADRs run 345–525 words by `wc` (≤ 300 planned; ADR 5 carries the cost table).
  - ARCHITECTURE is 2,255 words outside folds (≤ 2,200 planned).
  - PRICE_REACTION is 724 words (≤ 600 planned).

## Result review, round 1 (13 Nov): 7, 8, 7, 7.5
Live check first: `index-BqOq4beW.js`, the old hash. Offline gate 8 pass, 0 fail, 5 skip; `claims.py` holds; `flows.py` 40/40 on a local preview of a fresh build (same bundle hash as live).
- **Investor and designer (7).** The diagram's legend promises dashed boxes and draws none; every box names a GCP service that doesn't exist; labels too small at 390. The lead bullet says the model did nothing. act/note/fold and "planes" undefined. "The idea" repeats the opening; the old market estimate sits beside the measured one; 20/20 against 17/20. Leases look over-built on single-writer SQLite.
- **ENAM grader (8).** No live model number. The agent, the JD's first item, is paper: its limits can be tested offline with a scripted planner. The diagram blurs built and designed; the market day omits `--cap-results 50`. Nothing enforces the gate (no CI, no nightly live run). No IaC.
- **ENAM CTO (7).** No live number. The gate skips edits to unvalidated steps, never reads the answer live floors, and `run_answer --live` run 2 is run 1 from cache. Answering hides quota/terms errors as "Not in the calls I read", flags no fallback, and shows a model-written label. Replays: facts are first-writer-wins with no version, `ttm` ignores the quarter (look-ahead) and caches None, `plan` rescans all history every drain. Holdings have no inventory row; a private project with no egress can't notify the phone; database and compute unpriced.
- **Staff engineer and security (7.5).** `verify` matches mid-word: "17%" shows as "7%". Degraded runs re-asked forever, and a changed read output doesn't reach tier (fingerprints hash status, not output). The gate misses 5 of 6 model steps. A claim of 80 rows can outlast its 600 s lease, so two drains pay twice; a crash never counts an attempt. "No subject misfiled" can't come out otherwise: the bar is the act median (6.0×), so "Bagging of orders" (note, 2.9×) can't be flagged. The ₹/day overstates explain about 1.5×.

### Decisions on round 1
All taken except what needs a key or a tool not installed here (Terraform, Postgres): those are stated as such. Each code fix gets the check that would have caught it. The agent is built, bounded, tested offline with scripted planners, and off until a keyed run clears ADR 3's keep rule. A CI workflow runs the gate and claims on every PR and a nightly `--live`; it is checked here on a clean export of HEAD.

### Round 1 fixes, as done (13 Nov)
Each code fix has a check that fails when the fix is undone (mutation-tested).
- **Ledger** (`4bee7eb`).
  - A try is counted at claim, so a crash counts; one batch a claim and a 30-minute lease against a 10-minute worst case.
  - A racing planner can't reset a leased run.
  - Outputs are in fingerprints, re-asks are bounded at two, an hour apart, and planning reads only what changed: a quiet 12 Nov drain reads 0 events, 0.02 s against 0.8 s.
  - Facts carry their version; ttm uses the four quarters before the filing's.
  - `run_ingest` 16/16, check 9 skipped without the archive.
- **Gate and CI.** Every model step names its validator, and any change is red (`gate.py`). `.github/workflows/gate.yml` runs the gate and claims on every PR and `--live` nightly. Clean export of HEAD in a fresh venv: 9 pass, 0 fail. The ledger eval's day is checked in (38 KB).
- **Agent** (`finn/answer/agent.py`). Built on the workflow's registry and verifier: 6 steps, 10 calls, 60,000 tokens, no repeats, quotes only from pages read, leads into other companies headed by company. Off unless `FINN_AGENT=1`. `run_agent.py` 16/16 with scripted planners; `run_answer.py --live --agent` computes the keep rule. The planned retry on flash was cut, because the planner already runs on flash.
- **Price reaction.** The misses bar was a family of one (6.0×), so a post hoc 2× test, labelled as such, sits beside it: none survive, orders closest at p = 0.046.
- **Cost.** Explain's share is a range: 157–246 calls, $0.24–0.38 a day. Databases, compute and storage are priced as assumed list prices, about $1,000 a month in all.
- **Privacy.** Holdings are in the inventory, and a push that carries nothing lets the private project stay without egress.
- **Docs.** Diagram redrawn: boxes name running code, dashes mark only the designed parts, 12 px minimum. Words defined, the old market estimate gone, "In 200 words" at 200. ADR 3 renamed to `0003-checked-workflow-bounded-agent.md`.
- **Not done, and stated:** a live model number and the keep rule need a key; there is no IaC, since Terraform isn't installed here; Postgres isn't run. No app change, so no deploy: the live bundle stays `index-BqOq4beW.js`.

## Result review, round 2 (13 Nov): 8, 8.5, 8, 7.5
Investor and designer 8, ENAM grader 8.5, ENAM CTO 8, staff engineer and security 7.5.
- **Investor and designer.** The export arrow is drawn solid, but no export exists. CI is said to run, yet it never has on GitHub. The lead gives only 1.1 interrupts, not 1.1–8.9, and omits the cap of 50. There is lab-notebook voice ("Terraform isn't installed here", "by me", "didn't load"), and seven one-word bullets.
- **ENAM grader.** In CI, with NSE blocked, quotes, answer and agent all skip, so a pull request exercises none of them. `--live` marks explain validated, though enrich runs without revenue, and people rests on 2 filings. The answer floor is set by its own first run. The keep rule needs more flash calls than the free tier's 20 a day. There is no access control between investors, costs are sized only for 5,000 investors, Gemini isn't weighed against another family, and the demo book is 18, not 20.
- **ENAM CTO.** `--accept` silences a validated step, and the nightly job sets its own floor every night. The agent's budget and the keep rule's cost are chars ÷ 4, mixing flash with flash-lite prices. `MAX(seq)+1` races on Postgres, and planning still scans every event. Facts don't record when they were known, and `ttm` reads restated figures.
- **Staff engineer and security.**
  1. A failed re-ask erases a degraded answer, so an act becomes a note.
  2. `verify` treats `.`, `,` and `-` as word edges, so "15.6%" shows as "6%" and "14,859" as "859".
  3. `--accept` bypasses the gate.
  4. Check 16 is flaky: 2 in 30 runs.
  5. Status in the fingerprint re-runs people after an identical re-ask.
  6. A question naming a domain crashes answering.
  7. The keep rule's cost is in tokens, and the budget is checked after the call is paid.
  8. `quarter_end` is suspect.
  9. No checks for one batch a claim, the lease length or a fresh re-ask.

### Decisions on round 2
All taken, each code fix with a check that fails when it is undone. A live run, a GitHub run and Terraform stay stated as not done.

### Round 2 fixes, as done (13 Nov)
Each code fix has a check that fails when the fix is undone (mutation-tested).
- **Ledger.**
  - A failed re-ask keeps its degraded answer, and its try counts (check 17).
  - Fingerprints see done and degraded as one settled state, so an identical re-ask re-runs nothing (18).
  - One batch a claim and a 30-minute lease are checked (19), and so is a fresh re-ask (13).
  - `quarter_end` no longer skips back a quarter on its first day, and results moved to version 2 (20).
  - Check 16 counts rows read, not calls: 10 runs in a row clean. `run_ingest` 20/20.
- **Answering.**
  - A quote can't start or end inside a number or drop a sign.
  - A search query may name a website, since it's never fetched, and an unknown company is refused before any model call. `run_answer` 33/33.
- **Agent.** A page that isn't a number is rejected, not a crash. A step whose prompt would pass the budget isn't sent. Tokens come from the API's reported usage, thinking included. Cost is in dollars at each model's list price, and so is the keep rule. `run_agent` 18/18.
- **Gate.**
  - Page text is checked in (`evals/fixtures/pages.json.gz`, 0.5 MB). On a clean export with the network blocked: 9 pass, 0 fail, only the archive check skipped.
  - `--accept` is refused for a validated step. `--live` validates classify only: people and explain need labelled sets.
  - The answer floors are fixed before any live run: 14 of 20 grounded, 5 of 6 said so.
- **Docs.**
  - The lead gives 1.1–8.9 and the cap of 50. CI is called written, not run. The export is drawn dashed. The firm's voice throughout.
  - ADR 2 covers the Postgres sequence, what planning still scans, and facts by quarter, not vintage.
  - ADR 5 covers access between investors, a 50-investor pilot at about $250 a month, and other model families.
  - The keep rule needs billing, at most about $5.

## Result review, round 3 (13 Nov): 8.5, 9, 7.5, 8
Investor and designer 8.5, ENAM grader 9, ENAM CTO 7.5, staff engineer and security 8. Live check first: `index-BqOq4beW.js`. Gate 9 pass, 0 fail, 6 skip; claims hold. All round 2 fixes verified in code; two mutated on a copy and their checks failed.
- **Found by three of four: the keep rule's cost leg can't fail.** `workflow.py` appends the verdict to `codes` before pricing, so every workflow trace is $0, and `run_answer.py` floors the base at $1: a 25× agent passes. No check covered it.
- **Staff engineer and CTO.** Paid retries are uncounted: a cut-off reply doubles its room up to 32,768 and only the last try's usage is kept, so the 60,000-token budget isn't a ceiling. Two price functions disagree on an unknown model. The verifier still lets a quote flip meaning: a dropped "not", a Unicode minus, an apostrophe as a word edge ("don’t" → "t see"), "lakh crore" cut to "lakh", "bps" dropped, "(45.2)" opened. The workflow crashes on a page fetch failure; the agent's "unavailable" becomes "Not in the calls I read". Classify's batch pastes 20 filings unmarked, so one can relabel another. `not_yet` re-reads NSE every drain with no backoff. The agent's page check is ±1 twice over.
- **CTO.** A hand edit of `gate.json` passes as validated. ADR 2's Postgres sequence fix is wrong (sequences are taken at write, not commit). `ttm` reads screener's restated figures. INTERVIEW_DEFENSE isn't checked by `claims.py` and has drifted (nine doctored cases, check 5).
- **Grader.** A fixture miss turns a whole eval into a skip, so CI can go green without answering. `--accept` records no one. People and explain have no labelled set, though no key is needed to label one.
- **Investor and designer.** evals/README is stale (16/16, 74/74), in first person, says "interrupt". One step has three names (read, classify, "Classify vague filings"); two different sevens. "In 200 words" is 207 and says "with no key" unexplained. Docs say any changed step can be accepted by name; ADR 3 still says characters ÷ 4; ADR 2 has bare "blocked;" and "dead.". INTERVIEW_DEFENSE §1 is a changelog. The Answering box has no input arrow.

### Decisions on round 3
All code findings fixed, each with a check that fails when the fix is undone. Quotes are shown as whole sentences: the model's excerpt must sit inside one sentence, and the investor sees that sentence. Usage is summed over every try, in the error too, and the agent caps each reply at the budget left. A validated entry of `gate.json` can't change in a pull request (`gate.py --base`). Point-in-time results: `ttm` reads the as-filed XBRL facts where the ledger holds them. The people and explain labelled sets stay undone, and are stated: labels a model writes for its own eval aren't ground truth, so a person labels them.

### Round 3 fixes, as done (13 Nov)
Each code fix has a check that fails when the fix is undone (mutation-tested: the old file swapped back, the check fails or the eval crashes).
- **The meter.**
  - The workflow prices every call a model answered, and a failed call keeps what it paid.
  - `llm.generate` sums usage and dollars over every try, in its error too, and with a budget refuses a retry that might not fit.
  - One price function: an unpriced model is an error, and config checks every model it can call at import.
  - The keep rule is a function that divides by the real workflow cost; it fails at 3.1× and on a $0 baseline.
  - The agent caps each reply at what is left, and a refused retry stops at the token limit.
  - Checks: answer cost and keep (8), agent 19–22.
- **Quotes.** The screen shows the whole sentences a quote sits in (abbreviation-aware, at most 1,000 characters), so a dropped "not", "crore" or "bps" comes back. A Unicode minus, an apostrophe inside a word and an accounting bracket are word parts. Eight doctored cases with controls; the old verifier fails all eight.
- **Answering.** A page that can't be fetched is "unavailable", never a crash. An agent that can't reach its model is shown as unavailable, not "Not in the calls I read". The agent's quote must be found on a page it read, not within a page of one (agent 17, 18).
- **Ledger.** `not_yet` waits a quarter of the filing's age, 15 minutes to 6 hours (check 21). Sizing reads the four earlier quarters as their own filings gave them, public by the filing's day, and falls back to screener's restated table, saying so (check 22). `run_ingest` 22/22, ten runs in a row.
- **Classify.** An index read twice is unread (security, inject). The input-side fix, each filing as data with its own id, changes a validated step's input, so it waits on a keyed re-validation; ADR 4 says so.
- **Gate.**
  - `--base REF` takes what is validated, and the floors, from the base branch: a hand-edited `gate.json` passes nothing, a step marked validated by hand fails, and floors may only rise.
  - A changed validated step passes only by a live run in the job, and CI gives the job the key only under a maintainer's `live-eval` label.
  - With the page fixture present, a fetch is a fail, not a skip.
  - `--accept` needs `--why` and records who and the day.
  - Checks: security, gate (4). `run_security` 93/93.
- **Claims.** Every eval count stated in README, ARCHITECTURE, evals/README, INTERVIEW_DEFENSE and the ADRs is checked against its result file. PRICE_REACTION's 15,551 and the lead's 5.3× are claimed. On a clean export with the network blocked by a dead proxy: claims hold, and the gate gives 9 pass, 0 fail, with only the archive check skipped.
- **Docs.**
  - evals/README is in the firm's voice, with current counts and act/note/fold.
  - "In 200 words" is 199, with the 5.3× and "no model key".
  - Steps carry the gate's names, and the ledger's seven steps are kept apart from the gate's seven model steps.
  - ADR 2: Postgres planning by dirty marks with compare-and-set and a nightly full re-plan (a sequence doesn't fix it), and statuses defined.
  - ADR 3: the budget counts reported tokens.
  - ADR 4: `--base`, and the fingerprint's scope.
  - The threat rows name row-level security and the inject check. The diagram shows answering's input.
  - INTERVIEW_DEFENSE §1 is three lessons and a pointer.
- **Not done, and stated:** labelled sets for people and explain (a person labels them); a live model number; a GitHub run; Terraform; Postgres.

## Result review, round 4 (13 Nov): 8.5, 8.5, 8, 8.5
Live check first: `index-BqOq4beW.js`. Gate 9 pass, 0 fail, 6 skip; claims hold (the shipped-tiers line in PRICE_REACTION now claimed, `e639e7f`). Four reviewers started on the built result.

Investor and designer 8.5, ENAM grader 8.5, ENAM CTO 8, staff engineer and security 8.5. Round 3's fixes hold under mutation, except four that had no check (below).
- **Found by three: a deleted `gate.json` entry passed.** With classify's prompt edited and its entry, or whole evals, removed, `gate.py --base HEAD` exited 0.
- **Found by three: "its letter does" is untested.** The text model read NSE's summary, and no letter is read in the study.
- **Grader.**
  1. The covering note and brief trace contradict the architecture ("No agent acts alone"; data "stays on the phone"). README has no ledger, gate, ADRs or price study. The writeup hand-off is stale.
  2. Consent is one line, and the contact, who isn't a user, has none.
  3. A clone gets 21/21 where the docs say 22/22, the gate then rewrites the result and `claims.py` fails; the gate prints 7 skips where the docs say one.
  4. The diagram omits what feeds the app (the snapshot build, `/api`, Vercel).
  5. The region is asserted in ADR 5 and unsettled in ADR 1. A per-question cost is estimated but filed under measured.
  6. Nothing backs the `live-eval` label: no code owners, no required reviewers.
- **CTO.**
  1. Whole sentences break at "U.S." (20 cuts in 549 pages).
  2. The keep rule's "+4" never binds: at 18 of 20, +1 keeps the agent.
  3. `FINN_FAST_MODEL` changes a model past the gate.
  4. The CI key outlives the maintainer's read: a later push still gets it.
  5. A run parked for `terms` never resumes.
  6. "This quote passed your verifier. Who said it?" An analyst's question is shown as evidence.
  7. The gate's power is unstated: on one run a classifier truly 85% accurate clears 21 of 24 half the time.
- **Staff engineer and security** (each reproduced).
  1. `verify.py`: a page break splits a sentence and the tail is shown as whole (82 shown sentences start mid-sentence in 549 pages).
  2. `worker.py`: a claimed run is worked without checking that its inputs are settled, so a tier computed during a re-ask stays "not read".
  3. `worker.py`: one filing whose reply is always unreadable kills its batch of 20.
  4. `llm.py`: a 200 with no candidates, or one that isn't JSON, isn't an `LLMError`, so answering crashes and the paid tokens are lost.
  5. Four round 3 fixes have no check: the agent's reply cap, usage on the final error, the import-time price check, `--accept` needing `--why`.
  6. `steps.py`: the sizing fact's key omits `by`, so an earlier filing can be sized with a result first public later.
  7. `store.py`: a filing revised while its read is parked sends both revisions to the model.
  8. `workflow.py`: a percentage off a loss ("up from -531.0 crore (126.9%)").
- **Investor and designer.** The private boundary told three ways. README's architecture section describes the old diagram. The lead isn't readable cold ("capped at 50"; 8.9 without its 90th percentile). An 87-word table cell. "Ledger" means two things; "lines" undefined. The diagram's top box says archive where `poll` reads NSE. Three lab-notebook lines.

### Decisions on round 4
All taken, each code fix with a check that fails when it is undone. The writeup's own work (the covering note, README and trace rewritten) stays with `writeup`; here the contradictions are removed and the hand-off corrected. A live number, a GitHub run and hand-labelled sets stay stated as not done.

### Round 4 fixes, as done (13 Nov)
- **Gate** (`d06849f`). A dropped eval, floor, pattern or step is red in a pull request, and so is an eval that can't run; a step with no entry fails; a clone's ingest run keeps the full record.
- **Answering and the rest** (`4b9f088`). Dotted initials and a lower-case word don't end a sentence. A quote from a turn the moderator introduced as a question is refused. The keep rule never asks for fewer than 2. The two models are named in code only. A run parked for `terms` resumes on paid terms. The CI key goes only to the run the labelling starts.
- **Docs** (this commit). The letter claim is "untested", with the 5.1% against 3.6%. The boundary is told one way. Consent, the contact and the DPDP question are in §2 and ADR 1. The lead says 50 of 176 and where 1.1 and 8.9 come from. The region is "unconfirmed". The gate's skips are named, with what it can't guard and its power on 24 filings. "A quote carries no speaker" is in "Where this is weak".
- **The staff engineer's eight** (`c9636a1`, `c91e453`), each with a check that fails when undone. A sentence cut by a page break or blank line isn't shown. A run is worked only on the inputs it was planned for (check 24). An unreadable batch is halved down to the one filing that breaks it (25). A replaced revision is never read. The sizing fact is keyed by day. A 200 with no candidates, or one that isn't JSON, is a coded `LLMError` carrying what was paid. There is no percentage worked off a loss. The four round 3 fixes that had no check now have one: the agent's reply cap, usage on the final error, the import-time price check and `--accept`'s reason.
- **The rest** (`d34fec2`).
  - The diagram's top box is NSE, polled or archived. The app's snapshot and `/api` feed its views, and the export still starts at Facts.
  - README's architecture section matches it and links the ADRs and the price study.
  - The note and the trace no longer say "no agent acts alone" or that data "stays on the phone".
  - "Ledger" is defined against the app's promise ledger.
  - `.github/CODEOWNERS` covers `evals/`, `.github/`, the model client and config, and the settings it needs are in NEEDS.
  - INTERVIEW_DEFENSE carries round 4's lessons. The writeup hand-off takes counts only from result files.
- **Check after the fixes.** Live bundle `index-BqOq4beW.js`, unchanged, so no app change and no deploy. Offline gate: 9 pass, 0 fail, 6 skip. Claims hold.

## Result review, round 5 (13 Nov)

Investor and designer 8.5, ENAM grader 8.5, ENAM CTO 8, staff engineer and security 8. Round 4's fixes held under 21 mutations on a copy.
- **CTO: the price study dropped a fifth of the year.** Prices were keyed by ISIN, and NSE's filings keep the old ISIN after a split, so 34,740 filings (HDFC Bank's and SBI's results among them) never matched and their days counted as "no filing". The live grade counted an answer near the labelled page as right. INTERVIEW_DEFENSE said the questions were "written by me" (the coding agent wrote them), that C2 "is why FINN reads the letter" (it already did), and that the ledger "ran a whole market day" (every model step parked). C2 kept reverse-causal filings whose text said "clarification", and its two intervals weren't paired. In CI the key could reach every pull request if stored as a repository secret.
- **Staff engineer** (each reproduced). The gate fingerprinted its own model table, not the call: classify switched to the dearer model passed. Halving turned a model that garbles every reply into 39 calls a batch (780 paid requests), past the lease. Read's reply items weren't checked: a missing `line` crashed the drain, and a tier of "URGENT" reached tier. Enrich's threads dropped the context, so the live gate couldn't see a people or explain fallback. Sizing depended on drain order: with results capped, the screener fallback was stored as the day's fact.
- **Grader.** No live number. The architecture runs beside the app, not inside it. A hand-set fingerprint for an unvalidated step passed `--base` with no record. The push design needs silent pushes a web app can't take. The diagram lacked fundamentals, the people's source and the snapshot's input. `FINN_SMART_MODEL` was still named in two docs. No IaC.
- **Investor and designer.** The lead was 212 words and implied the ledger feeds the app. The diagram drew Gemini running in the ledger. "Where this is weak" didn't open with the replay. §5 used undefined statistics. "Keyed by ISIN" contradicted README. evals/README listed checks 1–22 of 27, and "ledger" meant two things there. There was lab-notebook voice, and the first table's cells were long.

### Decisions on round 5
All taken except three that stay stated as not done: a keyed run (no key here); a GitHub run (the repo is never pushed from here); IaC (Terraform isn't installed, and installing it changes the machine). The app reading the ledger stays out, as ROADMAP decided: the snapshot stays at 28 Oct, and "Where this is weak" now opens with it.

### Round 5 fixes, as done (13 Nov)
Each code fix has a check that fails when the fix is undone. The old file was run against the new check on a copy, and the check failed.
- **Price study** (`c944510`).
  - Prices are keyed by symbol and joined across every ISIN and rename. 98.6% of filings match; the rest are 88 suspended, insolvent or SME companies.
  - A stop rule requires at least 97% matched, a top-500 stock filing results about four times a year (median 4.1) and no duplicate symbols. The gate reads it.
  - Reverse-causal subjects are matched as whole words, so "PIT" no longer matches inside "Capital".
  - New numbers: 5.2× (4.7–5.7), 1.0× without results, 1.4–12.0 interrupts a week.
  - C2 leaves out filings whose text answers a move, and pairs its interval: +0.000 (−0.016 to +0.018), no gain.
  - The docs and claims carry the new numbers. INTERVIEW_DEFENSE §1 adds the lesson: a join needs a coverage check.
- **Answering.** A live answer is grounded only if the shown text holds the labelled answer; being on the labelled page is reported apart (`run_answer` 66/66). The questions are said to be the coding agent's, and a person checks them before a keyed run counts.
- **Gate** (`6f954af`, `ac939d6`).
  - An unvalidated step that changed needs `--accept`'s new record.
  - Fingerprints come from each call: its model, and every argument that changes what the model is asked. A model call no step owns is red. Each ledger step has one `MODEL`.
  - Enrich runs each thread in the caller's context. `run_security` 101/101.
- **Ledger** (`ac939d6`, `934a7f1`).
  - Halving follows only a failing half and stops when both fail: 3 calls for a garbling model, at most 11 for one bad filing. No call starts that might outlast the lease.
  - Read's items are checked against the schema's lists.
  - Sizing waits for an earlier quarter's results the ledger holds, and a fallback is never stored.
  - Checks 28–31. `run_ingest` 31/31.
- **CI** (`739d037`). The key is `LIVE_EVALS_GEMINI_KEY`, an environment secret only. The first step fails if it reaches an unlabelled pull request. `.github/CODEOWNERS` covers the gate, the workflow, the model client and config.
- **Docs** (`f367a55`, `aa1f037`).
  - The lead is 200 words and says the ledger runs beside the app, not feeding it.
  - The weaknesses open with the replay.
  - §5 is in plain words, and the first table is short. "Drain" and "fingerprint" are defined.
  - The diagram says "Gemini once keyed", shows the snapshot's sources and the demo's invented people, and keeps the export clear of the labels.
  - Push needs a native app: ADR 5 and ARCHITECTURE.
  - The stale model variable is gone. ADR 1's region line is in the firm's voice.
- **Check after the fixes.** Live bundle `index-BqOq4beW.js`, unchanged. Offline gate: 9 pass, 0 fail, 6 skip. Claims hold.

## Result review, round 6 (13 Nov)
Investor and designer 9, ENAM grader 8.5, ENAM CTO 8.5, staff engineer and security 8. Round 5's fixes held under mutation, and the price study rebuilt from raw data reproduces the table.
- **Staff engineer.**
  1. Classify's fingerprint covers the call's text, not how `items` is built: cutting `[:400]` to `[:40]` passed.
  2. An analyst's unpunctuated question can be widened into a company answer: 14 cases on the checked-in pages.
  3. People's reply items aren't checked: a missing `seniority` kills tier, and `"CEO"` folds silently.
  4. The gate ignores exit codes: run_reaction crashes on a fresh checkout and still passes.
  5. Halving can start a call after the lease (check 30 counted calls, not start times).
  6. Two overlapping polls crash one (`store.put` selects, then inserts).
  7. `workflow_dispatch` can bring the key to any branch.
- **CTO.**
  1. The live grade still passes wrong answers ("Page 3 of 25" for "almost Rs 3 trillion"), and it would validate on labels no person checked.
  2. The lease bound, as above, and backoff counted from the claim.
  3. INTERVIEW_DEFENSE says the subject line predicts nothing; it is NSE's summary text that adds nothing.
  4. The nightly run needs a reviewer every night.
  5. The top 500 hold 27 securities that never file (ETFs, MCX). σ before 28 Jan reaches back before the filings archive. BM25 recall rests on questions written from the pages.
- **Grader.**
  1. Aliasing `llm.generate` bypassed the gate (fixed in `a6c59ac`).
  2. ADR 5's per-investor unwrap has no mechanism, since the service account can unwrap every key.
  3. Which filings are read reveals the book and the research.
  4. Delhi recovery conflicts with erasure by key, and needs a second key per investor.
  5. The model routing is asserted, not measured.
  6. Push and caching contradictions remain in the note, README and trace, and the diagram has no path for questions.
  7. The private project isn't written as code.
- **Investor and designer** (fixed in `e2917cc`, `a5aafc5`). "Key" was undefined, and the lead's counts didn't add up. The phone sat inside "public". §5 mixed baselines. README had two ledgers and a stale push line. The paragraphs were long.

### Round 6 fixes, as done (13 Nov)

### Diagram rebuild (15 Nov)
Two iterations ran (`docs/img/arch_iterations/v1.png`, `v2.png`), each read as a rendered image by two reviewers: taste and accuracy, and plain language. v1 scored 7.5 and 6.5 (the line's "no model" claim covered the phone, the caption said nothing leaves the private side while an arrow left it, and "Today", "/api", "rows" and "no-training terms" needed the docs). v2 fixed those and scored 8.5 and 8.5, both SHIP, so v2 was chosen and copied to `docs/img/architecture.svg` and `.png`.

### Diagram text, words only (15 Nov)
The layout stayed v2's; only the words changed. With the text stripped, every later SVG is byte-identical to `v2.svg`, and no line runs past its box. Three iterations ran (`docs/img/arch_iterations/v3.png`, `v4.png`, `v5.png`), each read as a rendered image by two reviewers: does every line read as a person wrote it, and is the picture unchanged and still true to `ARCHITECTURE.md`.
- v3 scored 7 and 8.5: "a model", "API key", "locked project" and "call out" were unexplained, the answering box had lost "only", and the footer read as if deployed.
- v4 fixed those and scored 9 and 9, both ship.
- v5 took three honesty fixes the accuracy reviewer offered (answering "searches" and no longer promises an answer; "FINN doesn't keep it"; "your phone reads it only when signed in", since staff access is in the design) and scored 9 and 9.5, both ship. v5 was chosen and copied to `docs/img/architecture.svg` and `.png`.
- Not taken: dropping the first-person solid/dashed caption for a line on what FINN is. The caption was asked for by name.
- The scanner (`slop_scan.py --lexical`) and both humaniser checks found nothing in the final text. The SVG title and description and the alt-texts in ARCHITECTURE, the covering note and the README carry the new words.
