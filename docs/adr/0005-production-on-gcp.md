# ADR 5. Production on Google Cloud, in Mumbai, in two projects

Status: designed, 13 Nov 2026. Nothing here is deployed.

## Context
Running FINN for the firm needs:
- a schedule for the whole market;
- a store per investor that the firm can erase;
- data held in India;
- a hard line between public readings and private data (ADR 1).

The model is Gemini.

## Options
1. **AWS or Azure.** Rejected: either could do this, but every prompt and floor would have to be re-measured on another model family.
2. **Another model family on the same cloud.** Not ruled out: Vertex serves other families too, and which are offered in Mumbai would decide it. Gemini is chosen for its free tier on public text, structured output, and a Mumbai endpoint, which is unconfirmed for flash-lite (ADR 1). Every prompt is fingerprinted with its model, so a switch is a measured change, not a rewrite.
3. **Kubernetes.** Rejected: two jobs and two services don't need a cluster, and Cloud Run scales to zero.
4. **Stay on Vercel.** Rejected: no egress control, no per-investor keys, and no database in India behind a perimeter.
5. **Chosen: GCP `asia-south1`, with recovery in `asia-south2`, in two projects.**

## Decision
- **The public project.**
  - Cloud Scheduler starts Cloud Run jobs: `poll` every 15 minutes in market hours, then `drain`.
  - The ledger in Cloud SQL is the queue, with `SKIP LOCKED` claims, leases and fenced completions.
  - Cloud Storage holds the archive.
  - Answering reaches Vertex through workload identity, so no model key exists.
- **The private project:** holdings, contacts, identity answers, lines.
  - Vertex is disabled.
  - No NAT, a deny-all egress rule, and Private Service Connect for Cloud SQL and KMS.
  - A VPC Service Controls perimeter with no egress rules.
  - Nothing inside can call out. Two things come in: the exporter writes public facts, and each investor's signed-in phone reaches the private API, which answers with that investor's rows only.
- **Notifying.** The private project has no way out, so the public project sends the push. When an act filing lands anywhere in the market, it wakes every enrolled phone with a push that carries no content, at most one per poll. The phone then asks the private API what is new for its own book, and notifies only if something crossed its investor's lines (the thresholds they set). The wake-up depends on the market alone, so it reveals no holding.
- **This needs a native app.** A web app must show a notification for every push: Chrome shows one of its own if the app doesn't, and Safari revokes a subscription that receives silent pushes. So production ships the same app shell inside a native wrapper. On Android an FCM data message wakes it silently. On iOS a push that carries nothing is a background push, which iOS throttles. The dependable path is a notification service extension that asks the private API and fills the notification in. Dropping a notification that crossed no line needs Apple's notification-filtering entitlement, granted on request. Until the native app ships, the web app has no push, and an investor sees interrupts when they open it.
- **Erasure.** Rows, caches and exports are encrypted with a data key wrapped by the investor's own KMS key. Destroying every version of that key erases every copy, backups included, after at least 24 hours. Recovery in Delhi needs keys there, and Cloud KMS has no location inside India that spans both regions, so each investor has a key in each, the data key is wrapped by both, and erasure destroys both.
- **Matching.** A long-running matcher keeps unwrapped data keys in memory for at most an hour, so about one unwrap per investor an hour. It joins holdings to facts in memory.
- **Access.** The firm's sign-in through Identity Platform, Cloud Armor limits per user, and audited staff access.
- **Between investors.** Every request carries the investor's signed identity, and Postgres row-level security returns only that investor's rows to the API's role. Cloud KMS grants decrypt to a service account, not to an investor, so the API's account can unwrap any investor's key. What keeps it to one is code: it unwraps only the key named for the signed-in identity. Every unwrap is a data-access audit log entry, and one with no matching sign-in raises an alert. The matcher's account can unwrap every key by design. A stolen API or matcher account can unwrap every key until it is revoked, which is why each holds no network path but the database and KMS.

## Cost
A month at whole-market scale, at list prices. Counts are measured in this repo; *estimated* and *assumed* mark what isn't.

| Line | Basis | A month |
|---|---|---|
| Reading filings | 12 Nov: 987 filings, 157–246 calls, $0.24–0.38. The archive averages 15,150 filings a month | $4–6 |
| Calls read and graded | $0.06 a call, 4 a year, 2,700 companies | about $54 |
| Questions | $0.0022 each, *estimated* from characters at 4 a token (`evals/answer_result.txt`); *assumed* 5,000 investors asking 10 a month | about $110 |
| Keys and unwraps | $0.06 a key version, two per investor (Mumbai and Delhi), $0.03 per 10,000 unwraps; *assumed* 5,000 investors | about $611 |
| Two Cloud SQL instances, public and private | *assumed* list price: 2 vCPU, 8 GB, high availability, 100 GB each | about $480 |
| Cloud Run: poll and drain jobs, the matcher, answering | *assumed*: jobs a minute every 15 minutes; one always-on matcher | about $60 |
| Cloud Storage: the archive and PDFs | *assumed* 50 GB | about $1 |

The model is not the cost. The databases and the keys are, and the keys buy erasure that reaches backups. Infrastructure prices are assumed list prices, to be checked for Mumbai before a budget.

**A pilot of 50 investors** costs mostly the databases and reading the market. Keys come to about $6 and questions about $1. Two small instances without high availability, about $120 (*assumed*), would serve until the pilot proves out: about $250 a month in all, with $60 of it reading every filing and call.

## Trade-offs
- Debugging is slower, by design.
- Key prices come from a third-party listing, not Google's own table, so they need checking before a budget.
- Crypto-shredding holds only if no plaintext copy exists.
- A push can be late: iOS throttles pushes that carry nothing, so without the filtering entitlement an interrupt can wait for the app's next background fetch. And every phone wakes on every act filing in the market, which is the price of a private project with no way out.

## Revisit when
- About 100,000 investors: index holdings with a blind index, an HMAC of the symbol under each investor's key.
- A second region.
