# ADR 2. The ledger is the queue

Status: built, 13 Nov 2026. Code: `finn/ingest/`, `pipeline/ingest.py`. Checks: `evals/run_ingest.py`. A market day: `evals/ingest_day.txt`.

## Context
The app's snapshot comes from a batch, `build_push.py`. It re-decides every filing, falls back silently and records nothing. The market files about 1,000 times a day, quotas run out, PDFs fail and XBRL lags.

## Options
1. **Pub/Sub plus a state store.** Rejected: two systems to keep consistent, and redelivery needs a dedupe store anyway.
2. **A cron batch.** Rejected: it redoes everything, hides failures and can't resume.
3. **Chosen: one ledger that is both the record and the queue.**

## Decision
- **Events.** Each filing is stored once. A revision only when a fixed field changes: symbol, subject, text, URL, time or ISIN. `poll` re-reads a 3-day lookback, and inserts are idempotent.
- **Steps.** `rules`, `read` (the model step `classify`, 20 filings a call), `results`, `people`, `explain`, `size`, `tier`. Each calls the app build's own function.
- **Fingerprints.**
  - A run's fingerprint covers its step's version, prompt, schema, model and fallback chain, plus each input's fingerprint, status and output.
  - A run that doesn't apply leaves the model out, so a new read prompt re-runs only what read touches.
- **Statuses:**
  - done and pending;
  - superseded: a newer revision replaced it before it was read;
  - parked: `no_key`, `quota`, `terms`: waiting on a model key, quota or paid terms;
  - blocked: can't tell whether it applies while an input is parked;
  - not_yet: XBRL lags; NSE is read again after a quarter of the filing's age, 15 minutes to 6 hours, so a 60-day lag costs about 250 reads, not one every drain;
  - degraded: a fallback model answered; re-asked fresh an hour apart, at most twice, and a failed re-ask keeps the answer;
  - dead: `not_pdf` and `too_large` at once, `no_xbrl` 60 days after the filing, anything else after 5 tries.
  
  With no key, a step parks before anything is fetched.
- **Leases.** A short claim transaction on one batch, a 30-minute lease against a 10-minute worst case, work outside it, and completions fenced by lease token. A try is counted at claim, so a crash counts. One writer needs none of this; an overlapping Cloud Run job makes two writers.
- **Facts are versioned and point-in-time.** A fact's key carries its code's version. Revenue for sizing is the four quarters before the filing's, each as its own results filing gave it, if the ledger holds that filing and it was public by the filing's day. A results fact is written once, at first sight, and keeps its filing date, so a later restatement doesn't reach a replay. While the ledger holds a results filing for one of those quarters that is still being read, sizing waits (status pending, error `waiting`, no try counted), so the drain's order doesn't change a size. Where the ledger lacks a quarter, sizing falls back to screener's table, which carries restatements; the fallback is never stored as a fact (`run_ingest.py` checks 22 and 31).
- **Missing XBRL** is dead 60 days after the *filing*, not after the quarter, because late filers exist.
- **Source.** NSE, scraped politely, for now. For real, a licensed feed behind the same `poll`. The ISIN links a company across exchanges.
- **Retiring `build_push.py`.** Once a keyed day gives the same tiers.

## Trade-offs
- SQLite has one writer. For real it's Cloud SQL with `SKIP LOCKED`.
- The write sequence is `MAX(seq) + 1` inside each write, which is safe only because SQLite serialises writers. A Postgres sequence wouldn't fix it: numbers are taken at write and become visible at commit, so a write at 100 that commits after a touch at 101 is skipped by a planner reading "after 101".
- On Postgres, planning changes shape. A completion marks the steps that read its output as dirty for that event, in the same transaction. The planner takes dirty marks with `SKIP LOCKED`, plans those events, and clears each mark only if it hasn't been set again since (compare and set on a counter). A full re-plan each night catches anything missed. Today planning works only events whose inputs changed, by sequence, and the query still visits every event: a quiet 12 Nov drain returns none in 0.02 s on 987 events. A change to a step's own code plans every event again, and changing the fingerprint's form re-runs every run once.
- There is no exactly-once delivery outside the ledger.

## Revisit when
About 100 events a second, or a second consumer of events. Then Pub/Sub fans out from the ledger, and the ledger stays the record.
