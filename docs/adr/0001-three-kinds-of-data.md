# ADR 1. Three kinds of data, and which a model may read

Status: accepted, 13 Nov 2026. Code: `finn/llm.py` (`public=`). Checks: `evals/run_security.py`, terms.

## Context
FINN holds three kinds of data:
- public filings;
- what an investor holds and who they know;
- what they ask.

Gemini's free tier may use prompts to improve Google's products. Paid terms may not.

## Options
1. **Redact holdings inside prompts.** Rejected: a symbol and a quantity identify a book, and no feature needs holdings in a prompt.
2. **One project split by IAM alone.** Rejected: one wrong binding crosses the line silently. A perimeter with no egress fails closed.
3. **Chosen: decide per kind of data, in code, with private as the default.**

## Decision
- **Public filings.** A model may read them, once for everyone, on free terms. Callers pass `public=True`.
- **Holdings and contacts.** Code only. In production they live in a project with Vertex disabled and no egress (ADR 5).
  - The investor consents item by item, before anything is read, and can withdraw in the app; withdrawal deletes the item.
  - A contact isn't a user and agreed to nothing. FINN holds only what the investor's own export says of them, for that investor alone, and removes them when they ask. Whether the firm may hold contacts at all under the DPDP Act is counsel's call before launch.
- **Questions.**
  - A model reads them only on paid terms, never with a name or holdings, and they aren't stored or cached.
  - `generate` refuses private text unless `FINN_MODEL_TERMS=paid`, and never caches it.
  - In production a stateless service gets the question and the symbol, never an investor id, with request logging and the prompt cache off.
- **What is read reveals interest.** A filing's text carries no investor, but the choice of texts can: reading only a book's filings, or a symbol as it is typed, tells the model provider what someone holds or researches. So production reads the whole market whatever anyone holds, and looking up a symbol is answered from that reading, never read on demand. The demo doesn't: a model read its 22 companies, the 18 holdings among them, and with a model key Look up reads a typed symbol live, on public terms; both companies and the investor are public or invented.
- **Region: unconfirmed.** Whether flash-lite is served in Mumbai is to be confirmed with Google before launch. The rule:
  - questions use an `asia-south1` endpoint;
  - if flash-lite isn't served there, the newest flash-lite that is replaces it, after passing the gate's live floors.

## Trade-offs
No model reasons over a book. Questions cost paid calls and can't be cached.

## Revisit when
A feature needs a model to see holdings. Then a model on the device, or in the private project, must pass a 20-item holdings eval at **≥ 18/20**, with nothing of the book in its logs or output.

## What the app says
- **Filings.** FINN reads what companies file. A model helps, once for everyone. Every quote was found on its page.
- **Your book and your people.** They stay with FINN's own code. No model sees them. Close your account and they're gone, backups included.
- **Your questions.** They go to a model that is not allowed to train on them. They go without your name or holdings, and FINN doesn't keep them.
