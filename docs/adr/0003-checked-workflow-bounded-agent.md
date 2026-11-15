# ADR 3. Answering: a checked workflow, with a bounded agent behind it

Status: the workflow and the agent are built and checked offline; the agent is off until its keep rule passes on a keyed run. Code: `finn/answer/`. Checks: `evals/run_answer.py` on `evals/answer_questions.json`, and `evals/run_agent.py`.

## Context
Take the question "what did L&T say about the Middle East?" The risk is a fluent answer that isn't on any page. An agent earns its place only when the path depends on what is found.

## Options
1. **An agent first.** Rejected: its answers can't be measured without a key, and BM25 already puts the right page in the top 5 for 17 of 20 questions.
2. **A vector store.** Rejected for now: BM25 in code reaches 17 of 20 (18 within a page), with no index to refresh.
3. **Chosen: a fixed workflow on a tool registry, and an agent on the same tools as its escalation, built, bounded, and off.**

## Decision
- **The workflow.** BM25 search over the last four calls, then the top 5 pages, then one flash-lite call, then verification.
- **Evidence, not prose.**
  - A quote must match its page, or the page either side, exactly, starting and ending where a word or number does. The screen shows the page's own text, as the whole sentences the quote sits in: a model that leaves out "not", "crore" or "bps" can't change what the investor reads. A sentence the page holds only part of, cut by a page break, isn't shown.
  - A number is looked up by code, which writes the sentence.
  - A quote from a turn the moderator introduced as a question is refused: the company didn't say it.
  - One failed item turns the answer into "Not in the calls I read."
- **Tools.** Each carries a plane, and a private tool is refused. No tool takes a URL. Results are capped at 4,000 characters and marked as filing text.
- **Privacy and cost.** Questions are private by default. The trace keeps codes and timings, and nothing of the question. A question costs about $0.002.
- **The escalation** (`finn/answer/agent.py`). When the workflow finds nothing, a planner on flash picks tools from the same registry. Code bounds it:
  - 6 steps, 10 tool calls and 60,000 tokens, with no call repeated;
  - refusals go back as codes;
  - a quote must pass the same verifier, and be found on a page it read;
  - an item from another company's calls is headed with that company.

  Scripted planners test each bound offline (`run_agent.py`, 27 checks), and each bound was broken on purpose to see its check fail.
- **Keep rule, written before any number exists.** `run_answer.py --live --agent` computes it. On the 26 questions, over two runs, hand-judged, the agent must:
  - add 4 net correct answers, or half the workflow's misses where it misses fewer than 8, and never fewer than 2, so a workflow at 18 of 20 isn't beaten by one answer;
  - give at most 1 false answer on the 6 unanswerable;
  - cost at most 3× the workflow, in dollars at each model's list price. A workflow priced at $0 fails the rule rather than passing it (`run_answer.py`, keep).
- **Keys.** A free key measures the workflow. The agent's planner runs on flash, whose free tier allows 20 calls a day, so the keep rule needs billing on: at most about $5 for its two runs, by the token budget at flash's list price. Paid terms gate only investors' own questions.

## Trade-offs
- The workflow can't follow a lead to another call or another company. The agent can, but it stays off until it is measured.
- The budget counts the tokens the API reports for every try, retries included, summed over every step, since each step re-sends what came before. The only estimate is the check before sending: a prompt at 3 characters a token, on the high side, plus its longest reply must fit what is left, and a retry that might not fit isn't sent. So 60,000 is a ceiling, up to that estimate's error.
- Exact matching rejects quotes the model tidies, and how often isn't measured yet.
- A quote carries no speaker's name. The questioner check works where the moderator introduces questioners, as 26 of the 28 checked-in calls do, and it can miss: page furniture such as "ISIN:" looks like a turn's start. Names need each call's list of participants.
- Numbers cover reported results only.

## Revisit when
- A key exists and the agent clears the keep rule (its gain, at most 1 false, at most 3× the cost): then `FINN_AGENT=1` in production.
- Recall at 5 falls under 15 of 20.
