"""The agent's bounds, offline (finn/answer/agent.py). Each planner is scripted, so what is measured is the code around
a model: the limits, the refusals, the grounding and the verifier. Whether a real planner adds correct answers is
ADR 3's keep rule, which needs a key.

    python3 evals/run_agent.py
"""
import json, os, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import config, llm
from finn.answer import agent, tools, verify, workflow
REAL_PLANNER = agent.model_planner   # the evals script the planner; check 25 drives the real one

res, lines = [], []
def check(n, name, ok, detail=""):
    res.append(bool(ok)); lines.append(f"{'ok  ' if ok else 'FAIL'} {n}. {name}" + ("" if ok else f"   [{detail}]"))

def script(*acts, model=None):
    """A planner that plays its turns in order, then gives up; it keeps every prompt it was shown."""
    seen, left = [], list(acts)
    def plan(prompt, room=None):
        seen.append(prompt)
        act = left.pop(0) if left else {}
        if isinstance(act, Exception):
            raise act
        return act, model or config.SMART
    plan.seen = seen
    return plan

runs = {"search": 0}
real_search = tools.TOOLS["search"].fn
def counted(**a):
    runs["search"] += 1
    return real_search(**a)
tools.TOOLS["search"].fn = counted

q = next(x for x in json.loads((ROOT / "evals/answer_questions.json").read_text())["questions"] if x["period"])
S, P, G = q["symbol"], q["period"], q["page"]
page = tools.pages(S, P)[G - 1]
sent = next(s for s in re.split(r"(?<=[.?!])\s+", " ".join(page.split())) if "65,000" in s)
quote = {"kind": "quote", "symbol": S, "period": P, "page": G, "quote": sent}
READ = {"tool": "read", "symbol": S, "period": P, "page": G}
SCHEMA_TEST = {"type": "object", "properties": {"calls": {"type": "array", "items": {"type": "string"}}}}
answer = lambda *items: {"answer": {"answerable": True, "items": list(items)}}

got = agent.run(S, q["q"], planner=script({"calls": [{"tool": "search", "symbol": S, "query": q["q"]}]}, {"calls": [READ]}, answer(quote)))
check(1, "search, read, quote the page read: answered, shown as the page's own text",
      got["verdict"] == "answered" and got["items"][0]["text"].split() == sent.split() and got["trace"]["steps"] == 3, got["trace"])

got = agent.run(S, q["q"], planner=script({"calls": [{"tool": "search", "symbol": S, "query": q["q"]}]}, answer(quote)))
check(2, "a true quote from a page it never read is rejected", got["verdict"] == "rejected" and got["text"] == workflow.NOT_FOUND, got["verdict"])

got = agent.run(S, q["q"], planner=script({"calls": [READ]}, answer(dict(quote, page=str(G)))))
check("2b", "a quote whose page isn't a number is rejected, not a crash", got["verdict"] == "rejected", got["verdict"])

got = agent.run(S, q["q"], planner=script({"calls": [READ]}, answer(dict(quote, quote=sent.replace("65,000", "68,000")))))
check(3, "a doctored quote on a page it read is rejected by the workflow's verifier", got["verdict"] == "rejected", got["verdict"])

runs["search"] = 0
loop = {"calls": [{"tool": "search", "symbol": S, "query": "capacity"}]}
got = agent.run(S, q["q"], planner=script(*[loop] * 50))
check(4, "a planner that repeats one search stops at 6 steps; the repeats aren't run",
      got["trace"]["stop"] == "step_limit" and got["trace"]["steps"] == 6 and runs["search"] == 1 and got["trace"]["codes"].count("repeat") == 5,
      (got["trace"], runs))

many = {"calls": [{"tool": "read", "symbol": S, "period": P, "page": k} for k in range(1, 26)]}
got = agent.run(S, q["q"], planner=script(many, answer(quote)))
check(5, "25 calls asked at once: 10 run, then it stops", got["trace"]["tool_calls"] == 10 and got["trace"]["stop"] == "tool_limit"
      and got["verdict"] == "stopped", got["trace"])

got = agent.run(S, q["q"], planner=script({"calls": [dict(READ, page=k) for k in range(1, 6)]}, answer(quote)), limits=dict(agent.LIMITS, tokens=4000))
check(6, "a step whose prompt would pass the token budget isn't sent, so its answer never arrives",
      got["trace"]["stop"] == "token_limit" and got["verdict"] == "stopped" and got["trace"]["steps"] == 1 and got["trace"]["tokens"] <= 4000, got["trace"])
def heavy(prompt, room=None):
    return answer(quote)["answer"] and {"calls": [READ], **answer(quote)}, config.SMART, {"in": 50000, "out": 20000}
got = agent.run(S, q["q"], planner=heavy)
check("6b", "the API's own token count is used: a reply that passes 60,000 isn't taken, and it is priced at flash's rate",
      got["trace"]["stop"] == "token_limit" and got["verdict"] == "stopped" and got["trace"]["tokens"] == 70000
      and abs(got["trace"]["usd"] - (50000 * 1.5 + 20000 * 9.0) / 1e6) < 1e-9, got["trace"])
check(7, "the limits are ADR 3's: 6 steps, 10 tool calls, 60,000 tokens", agent.LIMITS == {"steps": 6, "tool_calls": 10, "tokens": 60000})

tools.TOOLS["holdings"] = tools.Tool(lambda: "your book", "private", {})
bad = {"calls": [{"tool": "holdings"}, {"tool": "read", "symbol": S, "period": "https://nsearchives.nseindia.com/x.pdf", "page": 1}, {"tool": "fetch"},
                 {"tool": "read", "symbol": S, "period": "Jan 1999", "page": 1}]}
plan = script(bad, {"calls": [READ]}, answer(quote))
got = agent.run(S, q["q"], planner=plan)
del tools.TOOLS["holdings"]
codes = got["trace"]["codes"]
check(8, "a private tool, a URL, an unknown tool and a bad period are refused, go back as codes, and it recovers",
      codes[:4] == ["private_tool", "url_arg", "unknown_tool", "bad_period"] and all(c in plan.seen[1] for c in codes[:4])
      and got["verdict"] == "answered", (codes, got["verdict"]))
check(9, "every tool result reaches the planner marked as filing text", tools.MARK in plan.seen[2], plan.seen[2][-300:])

other = "DIXON" if S != "DIXON" else "LT"
op = next(c["period"] for c in tools.calls(other))
opages = tools.pages(other, op)   # a whole sentence the verifier shows, from the first page that has one (a title page has none)
og, osent = next((g, s) for g in range(2, len(opages) + 1) for s in re.split(r"(?<=[.?!])\s+", " ".join(opages[g - 1].split()))
                 if len(s.split()) >= 8 and (verify.verify(s, opages, g) or {}).get("page") == g)
got = agent.run(S, q["q"], planner=script({"calls": [{"tool": "read", "symbol": other, "period": op, "page": og}]},
                                                answer({"kind": "quote", "symbol": other, "period": op, "page": og, "quote": osent})))
check(10, "a lead into another company's calls is answered, headed with that company",
      got["verdict"] == "answered" and got["items"][0]["label"].startswith(f"{other}, "), got["items"][:1] or got["verdict"])

num = {"kind": "number", "symbol": "DIXON", "metric": "revenue", "quarter": "Sep 2025", "compare": "year ago", "direction": "up"}
got = agent.run("DIXON", "How did revenue do?", planner=script({"calls": [{"tool": "numbers", "symbol": "DIXON", "metric": "revenue", "quarter": "Sep 2025"}]}, answer(num)))
check(11, "a number item's sentence is written by code", got["verdict"] == "answered" and "up from" in got["items"][0]["text"], got["items"])

got = agent.run(S, q["q"], planner=script(llm.LLMError("no_key")))
check(12, "no key: unavailable, never 'Not in the calls I read'", got["verdict"] == "unavailable" and got["text"] == workflow.UNAVAILABLE, got)
got = agent.run(S, q["q"], planner=script({"calls": [READ]}, {"answer": {"answerable": False, "items": []}}))
check(13, "answerable false is 'Not in the calls I read'", got["verdict"] == "not_in_calls" and got["text"] == workflow.NOT_FOUND, got["verdict"])
got = agent.run(S, q["q"], planner=script({"calls": [READ]}, answer(quote), model=config.FAST))
check(14, "an answer from a fallback planner is marked degraded", got["verdict"] == "answered" and got["degraded"], got["trace"])

nothing = lambda prompt, **k: {"result": {"answerable": False, "items": []}, "model": config.FAST}
os.environ.pop("FINN_AGENT", None)
agent.model_planner = lambda public: (_ for _ in ()).throw(AssertionError("the agent ran while off"))
off = workflow.answer(S, "zebra quartz seventeen", public=True, generate=nothing)
os.environ["FINN_AGENT"] = "1"
agent.model_planner = lambda public: script({"calls": [READ]}, answer(quote))
on = workflow.answer(S, "zebra quartz seventeen", public=True, generate=nothing)
os.environ.pop("FINN_AGENT", None)
check(15, "off unless FINN_AGENT=1; on, it runs only after the workflow finds nothing, and its answer is shown",
      not off["escalated"] and off["verdict"] == "not_in_calls" and on["escalated"] and on["verdict"] == "answered", (off["verdict"], on["verdict"]))
last = agent.TRACE.read_text().splitlines()[-1]
check(16, "the trace holds codes and counts, nothing of the question", "zebra" not in last and "quartz" not in last and "steps" in last, last)

# Round 3. The quote must be found on a page the agent read, not within a page of one.
pages_s = tools.pages(S, P)
if G + 2 <= len(pages_s):
    got = agent.run(S, q["q"], planner=script({"calls": [dict(READ, page=G + 2)]}, answer(dict(quote, page=G + 1))))
    check(17, "a quote found on a page it never read, cited to the page between, is rejected", got["verdict"] == "rejected", got["verdict"])
agent.model_planner = lambda public: script(llm.LLMError("quota"))
os.environ["FINN_AGENT"] = "1"
down = workflow.answer(S, "zebra quartz seventeen", public=True, generate=nothing)
os.environ.pop("FINN_AGENT", None)
check(18, "when the agent can't reach its model, the investor is told so, not 'Not in the calls I read'",
      down["escalated"] and down["verdict"] == "unavailable" and down["text"] == workflow.UNAVAILABLE, down["verdict"])
got = agent.run(S, q["q"], planner=script(llm.LLMError("bad_response", usage={"in": 9000, "out": 4000, "usd": 0.05})))
check(19, "a step that failed after paying counts what it paid", got["trace"]["tokens"] == 13000 and got["trace"]["usd"] == 0.05, got["trace"])
got = agent.run(S, q["q"], planner=script(llm.LLMError("budget", usage={"in": 3000, "out": 2000, "usd": 0.02})))
check(20, "a retry refused by the budget stops at the token limit, counted, and isn't 'unavailable'",
      got["trace"]["stop"] == "token_limit" and got["verdict"] == "stopped" and got["trace"]["tokens"] == 5000, got["trace"])

# llm.generate itself, with the HTTP call stubbed: every try is counted, and a retry that would pass the budget isn't sent.
class R:
    def __init__(self, text, pin, pout):
        self.status_code, self.text = 200, ""
        self._d = {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "MAX_TOKENS"}],
                   "usageMetadata": {"promptTokenCount": pin, "candidatesTokenCount": pout}}
    def json(self):
        return self._d
sent = []
def post(url, headers, json, timeout):
    sent.append(json["generationConfig"]["maxOutputTokens"])
    return replies.pop(0)
real_post, real_log, had = llm.requests.post, llm.USAGE_LOG, os.environ.get("GEMINI_API_KEY")
llm.requests.post, llm.USAGE_LOG, os.environ["GEMINI_API_KEY"] = post, ROOT / "evals/__pycache__/usage_test.jsonl", "test"
try:
    replies = [R('{"calls": [', 3000, 2000), R('{"calls": []}', 3000, 500)]
    out = llm.generate("x" * 300, model=config.SMART, schema=SCHEMA_TEST, task="agent", max_tokens=2000, cache=False, public=True, meta=True)
    check(21, "a cut-off reply is retried with more room, and both tries are counted and priced",
          out["usage"]["in"] == 6000 and out["usage"]["out"] == 2500 and sent == [2000, 4000]
          and abs(out["usage"]["usd"] - llm.usd(config.SMART, 6000, 2500)) < 1e-12, (out["usage"], sent))
    replies, sent[:] = [R('{"calls": [', 3000, 2000), R('{"calls": []}', 3000, 500)], []
    try:
        llm.generate("x" * 300, model=config.SMART, schema=SCHEMA_TEST, task="agent", max_tokens=2000, cache=False, public=True, meta=True, budget=8000)
        refused = None
    except llm.LLMError as e:
        refused = e
    check(22, "a retry that could pass the budget isn't sent, and the error carries what was paid",
          refused is not None and refused.code == "budget" and refused.usage["in"] + refused.usage["out"] == 5000 and sent == [2000],
          (refused and refused.code, sent))
    # Round 4. A 200 the client can't read is an error with a code, carrying what was paid; and the agent's own call is capped.
    class Odd(R):
        def __init__(self, d):
            self.status_code, self.text, self._d = 200, "<html>proxy</html>", d
        def json(self):
            if self._d is None:
                raise ValueError("not JSON")
            return self._d
    def fails(make):
        global replies
        replies, sent[:] = [make() for _ in range(8)], []
        try:
            llm.generate("x" * 300, model=config.SMART, schema=SCHEMA_TEST, task="agent", max_tokens=2000, cache=False, public=True, meta=True)
        except llm.LLMError as e:
            return e
        except Exception as e:
            return e
    empty = fails(lambda: Odd({"candidates": [], "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 0}}))
    html = fails(lambda: Odd(None))
    check(23, "a 200 with no candidates, or one that isn't JSON, is a coded error carrying what was paid, never a crash",
          all(isinstance(e, llm.LLMError) and e.code == "bad_response" for e in (empty, html)) and empty.usage["in"] == 400, (repr(empty), repr(html)))
    cut = fails(lambda: R('{"calls": [', 3000, 2000))
    check(24, "when every try is cut off, the error carries all four tries' tokens and dollars",
          isinstance(cut, llm.LLMError) and cut.usage["in"] == 12000 and cut.usage["out"] == 8000
          and abs(cut.usage["usd"] - llm.usd(config.SMART, 12000, 8000)) < 1e-12 and sent == [2000, 4000, 8000, 16000], (repr(cut), sent))
    replies, sent[:] = [R('{"calls": [', 300, 500), R('{"calls": []}', 300, 500)], []
    try:
        REAL_PLANNER(True)("x" * 300, 1000); capped = None
    except llm.LLMError as e:
        capped = e
    check(25, "the agent's own call asks for no more reply than its budget has left, and a retry past the budget isn't sent",
          sent == [899] and capped is not None and capped.code == "budget" and capped.usage["in"] + capped.usage["out"] == 800, (sent, repr(capped)))
finally:
    llm.requests.post, llm.USAGE_LOG = real_post, real_log
    if had is None:
        os.environ.pop("GEMINI_API_KEY", None)
    else:
        os.environ["GEMINI_API_KEY"] = had

ok, n = sum(res), len(res)
lines.append(f"TOTAL {ok}/{n}")
print("\n".join(lines))
(ROOT / "evals/agent_result.txt").write_text("\n".join(lines) + "\n")
sys.exit(0 if ok == n else 1)
