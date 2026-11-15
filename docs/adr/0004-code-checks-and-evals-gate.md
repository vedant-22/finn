# ADR 4. Code checks every model output, and evals are the merge gate

Status: built, 13 Nov 2026. Code: `evals/gate.py`, `evals/gate.json`, `.github/workflows/gate.yml`.

## Context
A model's output can be wrong and still read well. Models also fall back, get replaced, and prompts drift.

## Options
1. **An LLM as judge.** Rejected: it shares the first model's failure modes, costs a call per check, and can't be audited.
2. **Human spot checks alone.** Rejected as the gate, kept as calibration: 17 of 20 hand-checked grades held, once.
3. **Chosen: code checks each output, and a gate of evals guards each change.**

## Decision
- **Checks on every output:**
  - schema JSON;
  - categories and tiers from fixed lists;
  - quotes found on their page;
  - numbers from code;
  - the model that actually answered, so a fallback becomes `degraded`.
- **Offline floors:**
  - security, network, annual, ingest, answering and the agent, in full;
  - quotes at 74 of 80;
  - recall at 5 of at least 15 of 20;
  - the price study inside its interval.
- **Fingerprints.** Each model step's prompt template, schema, model and fallback chain is hashed, read from the call itself, with every argument that changes what the model is asked (a temperature, a token cap): `classify`, `people`, `explain`, `promise_extract`, `promise_grade`, `answer` and `agent`. The gate scans `finn/`, `api/` and `pipeline/` for model calls, and one that no step owns is red.
  - Classify starts validated: by AST, it matches the commit that recorded its eval.
  - The others start "first seen" and print as skips, never as passes. Each names what can validate it; extraction and grading have only a hand review, and the agent its keep rule.
  - Any changed step is red until its validator passes. An unvalidated one can instead be accepted (`--accept STEP --why`), and `gate.json` records who, the day and why; a validated one can't. Classify and answer have validators that run with a model key. People and explain need labelled sets of their own, because the classify set holds 2 management changes and never sizes a deal; a person labels them, since labels a model writes for its own eval aren't ground truth.
- **`--live` floors.** Classify at least 21/24 and tier at least 20/24, with two fresh runs agreeing on at least 22/24 and no fallback. Answering: two fresh runs, none unavailable or degraded, at least 14 of 20 grounded and 5 of 6 unanswerable said so. *Grounded* means the first three items the investor sees hold the labelled answer: its numbers and units in order, each within three words of the last, not just that it cites the right page, which is reported apart. A model quoting one true sentence a page scores nothing, every label is found on its own page, and the run validates nothing until a person has signed the labels off (`checked_by` in `answer_questions.json`). Both floors were fixed on 13 Nov, before any live run: 14 is most of the 17 questions whose labelled page search finds. A free key suffices.
- **Pull requests.** `gate.py --base` takes what is validated, the floors and the list of evals from the base branch's `gate.json`, not the tree's, so a hand edit passes nothing. An unvalidated step that changed passes only with a new record of who accepted it and why, as `--accept` writes it; that record is in the diff for the code owner, and the step stays a skip, never a pass.
  - An eval, a floor, the pattern that reads an eval's output, or a step dropped from `gate.json` is red. A floor may rise, never fall. An eval that can't run is red, not a skip.
  - A changed validated step passes only by a live run in the same job. The job gets the key only in the run a maintainer starts by labelling the pull request `live-eval`, having read its code; a later push runs without the key until it is labelled again. The key is a secret of the `live-evals` environment only: stored as a repository secret it would reach every pull request's code, so the workflow's first step fails if it arrives unlabelled. The nightly run has its own environment, limited to main with no reviewer, so it runs unattended, and a manual run on any other branch gets no key.
  - A step in the gate with no entry in `gate.json` is red, and the two models are named in code only, so neither a new step nor a new model arrives unseen.
  - `run_security.py` checks each of these.
- **What the gate can't do.** It runs from the tree it checks, so a pull request that edits `evals/` or the workflow can change the gate itself. That is for people: `.github/CODEOWNERS` names who reads a change to `evals/`, `.github/`, `finn/llm.py` and `finn/config.py`. Requiring that review, required reviewers on the `live-evals` environment, and the gate as a required check on main are repository settings; the repo isn't on GitHub yet, so none is set.
- **CI.** Written to run the gate and the claims check on every pull request and push to main. It hasn't run on GitHub yet: the public branch is one commit, with no pull request behind it. The live gate runs nightly with the key from a scoped environment, and uploads `gate.json` for a person to commit; CI never pushes. The page text the evals read is checked in (`evals/fixtures/pages.json.gz`), so they run where NSE is blocked. On a clean export of HEAD in a fresh virtualenv, with the network blocked: 10 pass, 0 fail, 8 skip (measured again on 15 Nov, on the public snapshot). The skips are the six unvalidated steps, the one ingest check that needs the 19 MB archive, and the annual-report check that compares each fixture with its PDF, which a clone doesn't hold.
- **The gate's first catch.** The quotes eval sampled the live promise ledgers and had drifted: 68/81 against a committed 74/80. Its sample is now pinned. The drifted sample also showed the promise ledger's fuzzy check passing a changed number, which is why answering's verifier is exact.

## Trade-offs
- The sets are small, so they catch large regressions only. On one run, a classifier truly 85% accurate clears the 21-of-24 floor half the time, and one at 80% a quarter of the time (binomial).
- A model changed behind the same name changes no fingerprint. Only the nightly live run sees it, and only once the key is a secret.
- For classify, the validated step, the fingerprint also covers its requests as built on the 24 labelled filings, rendered with the model and the fetch stubbed (`evals/render_classify.py`), so cutting how much of a filing goes in is red; the requests at `4718a06` and today are identical. For the other steps it covers the call, not the code that fills the prompt: a change there is caught by review. For the same reason, marking each classify filing as data with its own id, the input-side fix for one filing posing as another, waits on classify's keyed re-validation: it changes what a validated step sees. The output side is in: an index read twice is unread.

## Revisit when
Unchecked model outputs pass 10% of calls. Then 50 hand-labelled cases per step join the gate.
