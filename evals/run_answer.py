"""The answering workflow's checks (finn/answer/). Offline: the model call is a stub that returns recorded or doctored
items, so what is measured is the code around the model. Questions: evals/answer_questions.json.

    python3 evals/run_answer.py           guardrails, doctored items, recall at 5, one end-to-end run, tokens per question
    python3 evals/run_answer.py --live    with a key (a free one: these questions are published): the 26, twice
    python3 evals/run_answer.py --live --agent   and twice more with the agent on: ADR 3's keep rule
"""
import json, pathlib, re, statistics, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn import config, llm
from finn.sources import pdf
from finn.answer import tools, verify, workflow

res, lines = [], []
def check(group, name, ok, detail=""):
    res.append(bool(ok)); lines.append(f"{'ok  ' if ok else 'FAIL'} {group}: {name}" + ("" if ok else f"   [{detail}]"))

def refused(code, name, **args):
    try:
        tools.call(name, **args)
    except tools.ToolError as e:
        return e.code == code
    return False

QS = json.loads((ROOT / "evals/answer_questions.json").read_text())["questions"]
A = [q for q in QS if q["period"]]

# Guardrails: refused before anything runs.
check("guard", "an unknown tool", refused("unknown_tool", "fetch", symbol="LT"))
check("guard", "a URL in an argument", refused("url_arg", "read", symbol="LT", period="https://nsearchives.nseindia.com/x.pdf", page=1))
none = lambda p, **k: {"result": {"answerable": False, "items": []}, "model": config.FAST}
check("guard", "a question naming a website is answered, not refused or crashed", workflow.answer("LT", "Competition from Amazon.in?", public=True, generate=none)["verdict"] == "not_in_calls")
check("guard", "an unknown company is refused before any model call", workflow.answer("NOSUCHCO", "Anything?", public=True, generate=None)["verdict"] == "refused")
check("guard", "a period not in the company's list", refused("bad_period", "read", symbol="LT", period="Jan 1999", page=1))
check("guard", "a page out of range", refused("bad_page", "read", symbol="LT", period="Aug 2026", page=999))
tools.TOOLS["holdings"] = tools.Tool(lambda: "your book", "private", {})
check("guard", "a private tool", refused("private_tool", "holdings"))
del tools.TOOLS["holdings"]
big = tools.call("read", symbol="LT", period="May 2026", page=3)
check("guard", "results cut to 4,000 characters and marked as filing text", len(big["text"]) <= 4000 and big["note"] == tools.MARK)
check("guard", "no tool takes a URL", not any(re.search(r"url|link|href", a) for t in tools.TOOLS.values() for a in t.args))

# Doctored items: each must reject the answer. Controls must pass, or "reject everything" would look perfect.
q = A[0]
page = tools.pages(q["symbol"], q["period"])[q["page"] - 1]
sent = next(s for s in re.split(r"(?<=[.?!])\s+", " ".join(page.split())) if "65,000" in s)
good = {"kind": "quote", "label": "capacity next quarter", "period": q["period"], "page": q["page"], "quote": sent}
num = {"kind": "number", "label": "revenue", "metric": "revenue", "quarter": "Sep 2025", "compare": "year ago", "direction": "up"}
check("doctor", "control: a true quote passes, shown as the page's own text", (got := workflow.check(q["symbol"], [good])) and got[0]["text"].split() == sent.split(), got)
check("doctor", "control: a true number passes, its sentence written by code", (n := workflow.check("DIXON", [num])) and "up from" in n[0]["text"], n)
far = dict(good, page=q["page"] + 3)
check("doctor", "a quote cited to another page", workflow.check(q["symbol"], [far]) is None)
check("doctor", "a number changed inside a quote", workflow.check(q["symbol"], [dict(good, quote=sent.replace("65,000", "68,000"))]) is None)
w = sent.split(); w[2], w[3] = w[3], w[2]
check("doctor", "two words swapped", workflow.check(q["symbol"], [dict(good, quote=" ".join(w))]) is None)
_numbers, tools.numbers = tools.numbers, lambda sym, metric, quarter: {"value": 143.0 if quarter == "Jun 2026" else -531.0}
loss = workflow.check("DIXON", [{"kind": "number", "metric": "pat", "quarter": "Jun 2026", "compare": "previous quarter", "direction": "up"}])
tools.numbers = _numbers
check("doctor", "no percentage is worked off a loss", loss and "%" not in loss[0]["text"] and "PAT was 143.0 crore" in loss[0]["text"] and "up from -531.0 crore" in loss[0]["text"], loss)
check("doctor", "the wrong direction on a number", workflow.check("DIXON", [dict(num, direction="down")]) is None)
check("doctor", "an unknown metric", workflow.check("DIXON", [dict(num, metric="vibes")]) is None)
check("doctor", "one bad item among good ones rejects the answer", workflow.check(q["symbol"], [good, num, far]) is None)
n0 = next(i for i in range(len(sent) - 1) if sent[i].isdigit() and sent[i + 1].isdigit())   # a number of two or more digits
check("doctor", "a quote cut inside a number (its first digit dropped)", workflow.check(q["symbol"], [dict(good, quote=sent[n0 + 1:])]) is None)
check("doctor", "a quote cut inside its last word", workflow.check(q["symbol"], [dict(good, quote=sent.rstrip(".?! ")[:-2])]) is None)
NUM = ["Margins were 15.6% of sales this quarter, on revenue of Rs 14,859 crore, after a -3.2% change last year."]
check("doctor", "control: a quote that starts and ends on whole numbers passes", verify.verify("15.6% of sales this quarter, on revenue of Rs 14,859 crore", NUM, 1))
check("doctor", "a quote starting inside a decimal (15.6% as 6%)", verify.verify("6% of sales this quarter, on revenue", NUM, 1) is None)
check("doctor", "a quote starting inside a number with a comma (14,859 as 859)", verify.verify("859 crore, after a -3.2% change", NUM, 1) is None)
check("doctor", "a quote ending inside a decimal (15.6 as 15)", verify.verify("So margins were 15", ["So margins were 15.6% of sales."], 1) is None and verify.verify("Margins were 15.6% of sales this quarter, on revenue of Rs 14", NUM, 1) is None)
check("doctor", "a quote that drops a minus sign (-3.2% as 3.2%)", verify.verify("3.2% change last year.", NUM, 1) is None)
# Round 3: a quote that would change its meaning by where it stops. The screen shows whole sentences.
T = ["Revenue fell \u22123.2% year on year. We don\u2019t see demand recovering soon. We do not expect margins to improve this year. "
     "The order book stands at Rs 12 lakh crore across segments. Over the year, margins rose by 150 bps. "
     "The loss was (45.2) crore for the segment. Mr. Rao said we will not cut prices in the quarter."]
def shown(quote):
    got = verify.verify(quote, T, 1)
    return got and got["span"]
check("doctor", "a quote that drops a Unicode minus (\u22123.2% as 3.2%)", shown("3.2% year on year.") is None)
check("doctor", "a quote cut inside a word at an apostrophe (don\u2019t as t)", shown("t see demand recovering soon.") is None)
check("doctor", "a quote that drops an accounting minus ((45.2) as 45.2)", shown("45.2) crore for the segment.") is None)
check("doctor", "a quote that leaves out 'not' is shown with it", shown("expect margins to improve this year.") == "We do not expect margins to improve this year.", shown("expect margins to improve this year."))
check("doctor", "a quote that stops at 'lakh' is shown with 'crore'", (shown("The order book stands at Rs 12 lakh") or "").endswith("Rs 12 lakh crore across segments."))
check("doctor", "a quote that stops before 'bps' is shown with it", (shown("the year, margins rose by 150") or "").endswith("150 bps."))
check("doctor", "control: 'Mr.' doesn't end a sentence", shown("Rao said we will not cut prices") == "Mr. Rao said we will not cut prices in the quarter.")
US = ["Yes. I mean we're not exactly in the U.S. and Europe and Japan. In the U.S. Titan sells little: the U.S. Share to our company sales "
      "is just about 2%. He asked \"is it volume?\" and we said it is not volume alone. Thank you."]
def shown_us(quote):
    got = verify.verify(quote, US, 1)
    return got and got["span"]
check("doctor", "dotted initials don't end a sentence (the U.S. and Europe)", shown_us("and Europe and Japan.") == "I mean we're not exactly in the U.S. and Europe and Japan.", shown_us("and Europe and Japan."))
check("doctor", "nor before a capital (the U.S. Share)", shown_us("Share to our company sales is just about 2%.") ==
      "In the U.S. Titan sells little: the U.S. Share to our company sales is just about 2%.", shown_us("Share to our company sales is just about 2%."))
check("doctor", "no sentence starts in lower case (a quoted question mid-sentence)", shown_us("we said it is not volume alone.") ==
      "He asked \"is it volume?\" and we said it is not volume alone.", shown_us("we said it is not volume alone."))
# Round 4: who said it. An analyst's question, word for word on its page, isn't the company's statement.
ASKED = {"kind": "quote", "period": "May 2026", "page": 12, "quote": "When you said that the revenue for the current quarter, you expect a 12% to 15% growth, is it volume?"}
check("doctor", "an analyst's question, true to its page, isn't shown as the company's words", workflow.check("DIXON", [ASKED]) is None)
said = workflow.check("DIXON", [dict(ASKED, quote="Yes, it's the volume growth you're talking about.")])
check("doctor", "control: the company's reply to it, on the same page, is shown", said and said[0]["text"] == "Yes, it's the volume growth you're talking about.", said)
CALL = ["Moderator: The next question is from the line of Asha Joshi from Acme Capital.\nAsha Joshi: You said margins will reach 18% next year, right?\n"
        "Vikram Rao: We said margins should stay near 15% next year.\nISIN: INE000A01010\nAsha Joshi: So prices will be cut by 10% this year.",
        "And volumes will fall by 5% this year.\nVikram Rao: We will not cut prices this year."]
ok_turn = lambda quote, page: bool(verify.verify(quote, CALL, page))
check("doctor", "a questioner's turn is refused on its page and where it runs over the page; the company's turns pass",
      not ok_turn("margins will reach 18% next year", 1) and not ok_turn("volumes will fall by 5% this year", 2)
      and ok_turn("margins should stay near 15% next year", 1) and ok_turn("We will not cut prices this year", 2))
check("doctor", "it can't accuse: with no introduction by the moderator, nothing is refused",
      bool(verify.verify("margins will reach 18% next year", [CALL[0].split("\n", 1)[1]], 1)))
# Round 4: a page break or a blank line cuts a sentence. What the page holds only part of isn't shown.
CUT = ["Demand was steady. And so we do not think that the cement industry will", "Page 9 of 20\n\nbe able to raise prices this year. Next question, please."]
CUT2 = ["Demand was steady. And so we do not think that\n\nPage 8 of 20", "UltraTech Cement Limited\n\nIndia will be able to raise prices this year. Next question, please."]
OK2 = ["Demand was steady. We said so in May.\n\nPage 8 of 20", CUT2[1]]
check("doctor", "the tail of a sentence cut by a page break isn't shown as whole (it loses its 'do not')", verify.verify("be able to raise prices this year", CUT, 2) is None)
check("doctor", "nor a lower-case start with nothing before it to judge by", verify.verify("be able to raise prices this year", [CUT[1].split("\n\n")[1]], 1) is None)
check("doctor", "nor a tail that starts with a capital, after a page footer and header", verify.verify("India will be able to raise prices this year", CUT2, 2) is None)
check("doctor", "nor the head of a cut sentence, which has no full stop", verify.verify("we do not think that the cement industry will", CUT, 1) is None)
check("doctor", "control: the same sentence after a finished page is shown, the header and footer stepped over",
      (verify.verify("India will be able to raise prices this year", OK2, 2) or {}).get("span") == "India will be able to raise prices this year.")
check("doctor", "control: a sentence after a lead-in ending in a colon is shown",
      (verify.verify("The quarter reflected steady execution", ["Turning on to revenues:\n\nThe quarter reflected steady execution."], 1) or {}).get("span") == "The quarter reflected steady execution.")
check("doctor", "a sentence over 1,000 characters isn't shown", verify.verify("one two three four", ["one two three four " + "x " * 600], 1) is None)
check("doctor", "a fragment under 4 words", workflow.check(q["symbol"], [dict(good, quote=" ".join(sent.split()[:3]))]) is None)
check("doctor", "the heading over a quote is the call and page, written by code", got and got[0]["label"] == f"{q['period']} call, page {q['page']}", got)
check("doctor", "a stitched quote from two pages", workflow.check(q["symbol"], [dict(good, quote=sent + " " + " ".join(
      tools.pages(q["symbol"], q["period"])[q["page"] + 2].split()[:12]))]) is None)

# Retrieval: is the labelled page among the 5 pages the model would see?
hits = {x["id"]: json.loads(tools.call("search", symbol=x["symbol"], query=x["q"])["text"]) for x in A}
exact = sum(any((h["period"], h["page"]) == (x["period"], x["page"]) for h in hits[x["id"]]) for x in A)
near = sum(any(h["period"] == x["period"] and abs(h["page"] - x["page"]) <= 1 for h in hits[x["id"]]) for x in A)
lines.append(f"recall at 5: {exact}/{len(A)} exact page, {near}/{len(A)} within a page")
for x in A:
    if not any((h["period"], h["page"]) == (x["period"], x["page"]) for h in hits[x["id"]]):
        lines.append(f"     missed {x['id']} {x['symbol']} {x['period']} p{x['page']} ({x['from']})")

# End to end through a stub model: copy the true sentence for one question; say nothing for an unanswerable one.
def stub(prompt, **kw):
    return {"result": {"answerable": True, "items": [good]} if "65,000" in prompt else {"answerable": False, "items": []}, "model": config.FAST}
e2e = workflow.answer(q["symbol"], q["q"], public=True, generate=stub)
u = next(x for x in QS if not x["period"])
none = workflow.answer(u["symbol"], u["q"], public=True, generate=stub)
check("e2e", "a true quote end to end is answered with the page's text", e2e["verdict"] == "answered" and e2e["items"][0]["page"] == q["page"], e2e["verdict"])
check("e2e", "nothing found reads 'Not in the calls I read.'", none["verdict"] == "not_in_calls" and none["text"] == workflow.NOT_FOUND)
check("e2e", "the trace holds no part of the question", not any(w.lower() in json.dumps(e2e["trace"]).lower() for w in q["q"].split() if len(w) > 4))
priv = workflow.answer(q["symbol"], q["q"])   # an investor's question: private by default, refused on free terms before any request
check("e2e", "a private question on free terms is refused before any request, and says the model wasn't reached",
      priv["trace"]["codes"][0] == "terms" and priv["verdict"] == "unavailable" and priv["text"] == workflow.UNAVAILABLE, priv["trace"])
def quota(prompt, **kw):
    raise llm.LLMError("quota")
qa = workflow.answer(q["symbol"], q["q"], public=True, generate=quota)
check("e2e", "a model error never reads as 'Not in the calls I read.'", qa["verdict"] == "unavailable" and qa["text"] == workflow.UNAVAILABLE, qa["verdict"])
fb = workflow.answer(q["symbol"], q["q"], public=True, generate=lambda p, **kw: dict(stub(p, **kw), model=config.FALLBACK[config.FAST]))
check("e2e", "an answer from a fallback model is marked degraded", fb["verdict"] == "answered" and fb["degraded"] and not e2e["degraded"], fb["verdict"])

# Round 3: the meter. Every call a model answered is priced, failed tries included; nothing reads $0 by accident.
paid = workflow.answer(q["symbol"], q["q"], public=True, generate=lambda p, **kw: dict(stub(p, **kw), usage={"in": 4000, "out": 400}))
check("cost", "an answered call is priced at its model's list rate", abs(paid["trace"]["usd"] - llm.usd(config.FAST, 4000, 400)) < 1e-12
      and paid["trace"]["usd"] > 0, paid["trace"])
def cut_off(prompt, **kw):
    raise llm.LLMError("bad_response", usage={"in": 3000, "out": 2000, "usd": 0.006}, model=config.FAST)
co = workflow.answer(q["symbol"], q["q"], public=True, generate=cut_off)
check("cost", "a call that failed after paying keeps what it paid", co["trace"]["usd"] == 0.006 and co["trace"]["tokens"] == 5000, co["trace"])
def unfetched(**a):
    raise pdf.FetchError("unreachable", "x")
real_read, tools.TOOLS["read"].fn = tools.TOOLS["read"].fn, unfetched
gone = workflow.answer(q["symbol"], q["q"], public=True, generate=stub)
tools.TOOLS["read"].fn = real_read
check("cost", "a page that can't be fetched says the model wasn't reached, never a crash", gone["verdict"] == "unavailable"
      and gone["text"] == workflow.UNAVAILABLE and gone["trace"]["usd"] == 0, gone["verdict"])
try:
    llm.usd("a-model-with-no-price", 1, 1); priced = True
except KeyError:
    priced = False
check("cost", "a model with no list price is an error, not $0", not priced)
_src = (ROOT / "finn/config.py").read_text()
_gone = _src.replace('    "gemini-3.5-flash": (1.50, 9.00),\n', "")
try:
    exec(compile(_gone, "config.py", "exec"), {"__file__": str(ROOT / "finn/config.py"), "__name__": "config_unpriced"}); stopped = False
except RuntimeError:
    stopped = True
check("cost", "a model FINN can call with no list price stops FINN at import", _gone != _src and stopped)

def keep_rule(base, esc):
    """ADR 3's keep rule over two workflow runs and two runs with the agent on, each (grounded of 20, answered of the
    6 unanswerable, dollars). Cost is the agent runs' dollars over the workflow's; a workflow at $0 is a broken meter."""
    gain = min(e[0] for e in esc) - min(b[0] for b in base)
    misses = 20 - min(b[0] for b in base)
    need = min(4, max(2, -(-misses // 2)))   # 4, or half the workflow's misses under 8, and never fewer than 2
    false, spent = max(e[1] for e in esc), sum(b[2] for b in base)
    cost = sum(e[2] for e in esc) / spent if spent > 0 else float("inf")
    return gain >= need and false <= 1 and cost <= 3, gain, need, false, cost
B = [(12, 0, 0.05), (12, 0, 0.05)]
check("keep", "the keep rule passes at 2.9x the workflow's dollars", keep_rule(B, [(16, 1, 0.145)] * 2)[0])
check("keep", "the keep rule fails at 3.1x, though under $1", not keep_rule(B, [(16, 1, 0.155)] * 2)[0], keep_rule(B, [(16, 1, 0.155)] * 2))
check("keep", "the keep rule fails on a workflow priced at $0", not keep_rule([(12, 0, 0.0)] * 2, [(16, 0, 0.01)] * 2)[0])
check("keep", "the keep rule asks for half the misses under 8, and never fewer than 2: a workflow at 18 of 20 isn't beaten by +1",
      [keep_rule([(b, 0, 0.05)] * 2, [(20, 0, 0.1)] * 2)[2] for b in (10, 12, 14, 16, 18, 20)] == [4, 4, 3, 2, 2, 2]
      and not keep_rule([(18, 0, 0.05)] * 2, [(19, 0, 0.1)] * 2)[0] and not keep_rule([(20, 0, 0.05)] * 2, [(20, 0, 0.1)] * 2)[0])
check("keep", "the keep rule fails on too small a gain, or two unanswerables answered",
      not keep_rule(B, [(15, 0, 0.1)] * 2)[0] and not keep_rule(B, [(16, 2, 0.1)] * 2)[0])

# Round 6: a speaker's turn ends a sentence. An analyst's unpunctuated question never runs on into the answer, and no
# span shown holds two speakers' words, on a made page or on any of the 28 checked-in calls.
import gzip as _gz
_turn_page = ("Moderator: The next question is from the line of Amit Mahawar from UBS. Please go ahead.\n"
              "Amit Mahawar: The share of core top line in the order book has been rising so what should we expect for margins\n"
              "Subramanian Sarma: I mean, we expect margins to remain at about 8.5% for the year. That is our guidance.")
_shown_turn = verify.verify("we expect margins to remain at about 8.5%", [_turn_page], 1)
_asked_turn = verify.verify("what should we expect for margins", [_turn_page], 1)
_fixture = json.loads(_gz.decompress((ROOT / "evals/fixtures/pages.json.gz").read_bytes())) if (ROOT / "evals/fixtures/pages.json.gz").exists() else {}
_two = sum(1 for pgs in _fixture.values() for raw in pgs for a, b in verify._spans(raw)
           if any(m.start() > 0 for m in verify.TURN.finditer(raw[a:b].strip())))
check("verify", "an analyst's unpunctuated question isn't shown as the answer's start, and no span on the 28 calls holds two turns",
      _shown_turn and _shown_turn["span"].startswith("Subramanian Sarma: I mean") and "Mahawar" not in _shown_turn["span"]
      and _asked_turn is None and _fixture and _two == 0, (_shown_turn, _asked_turn, _two))

# Right, not just near: a live answer counts as grounded only if what the investor sees holds the labelled answer: the
# label's numbers and units, in order, each within three words of the last ("65,000 MVA" matches "65000 MVA", and
# "10% to 12%" matches "10-12%", but "Page 3 of 25" isn't "Rs 3 trillion" and "1.8x" isn't "below 1x"). Only the first
# three items shown count, so an answer can't win by listing everything. Being on the labelled page is reported apart.
UNITS = {"%", "crore", "lakh", "trillion", "billion", "million", "mva", "bps", "month", "year", "x", "fiscal", "double", "digit",
         "q1", "q2", "q3", "q4"}
_plain = {"months": "month", "years": "year", "crores": "crore", "trillions": "trillion", "billions": "billion"}
def _tokens(s):
    s = re.sub(r"(?<=\d),(?=\d)", "", s.lower()).replace("per cent", "%").replace("percent", "%").replace("basis points", "bps")
    return [_plain.get(t, t) for t in re.findall(r"q[1-4](?![a-z0-9])|\d+(?:\.\d+)?|%|[a-z]+", s)]   # "INR250" is "inr", "250"
def _key(expect):
    k = [t for t in _tokens(expect) if t[0].isdigit() or t in UNITS]
    return [t for n, t in enumerate(k) if t[0].isdigit() or t not in k[n + 1:]]   # a repeated unit counts once, at its last place
def has_expect(expect, shown_text):
    key, toks = _key(expect), _tokens(shown_text)
    def run(at, rest):
        if not rest:
            return True
        return any(toks[p] == rest[0] and run(p, rest[1:]) for p in range(at + 1, min(len(toks), at + 4)))
    return bool(key) and any(t == key[0] and run(p, key[1:]) for p, t in enumerate(toks))
def right(x, r):
    return r["verdict"] == "answered" and has_expect(x["expect"], " ".join(i["text"] for i in r["items"][:3]))
_q = next(x for x in QS if x["expect"] == "65,000 MVA")
_near = {"verdict": "answered", "items": [{"text": "We see good demand in transformers this year."}, {"text": "Margins held at 12.5%."}]}
check("live grade", "an answer counts only if the shown text holds the labelled answer: one true sentence a page doesn't",
      right(_q, {"verdict": "answered", "items": [{"text": "We expect to reach 65000 MVA by the next quarter."}]})
      and not right(_q, _near) and has_expect("10% to 12%", "growth of 10-12% for FY27") and not has_expect("10% to 12%", "growth of 10%")
      and has_expect("double-digit", "we expect double digit growth") and not right(_q, {"verdict": "rejected", "items": []})
      and has_expect("10% to 12%", "we see 10% to 12% growth") and has_expect("INR 250-300 crores", "about Rs. 250 to 300 crore")
      and not has_expect("almost Rs 3 trillion", "Page 3 of 25 ... a trillion-rupee market") and not has_expect("Q4 of this fiscal", "4 plants in fiscal")
      and not has_expect("below 1x", "net debt was 1.8x in Q1") and not has_expect("INR 2 trillion", "an order of INR 2 crore")
      and not right(_q, {"verdict": "answered", "items": [{"text": "x."}] * 3 + [{"text": "We expect to reach 65000 MVA."}]}))

# The grade must be winnable: each label is found, as has_expect reads it, on its labelled page or a page either side.
_unfound = [x["id"] for x in QS if x["period"] and not has_expect(x["expect"], " ".join(
    tools.call("read", symbol=x["symbol"], period=x["period"], page=pg)["text"] for pg in (x["page"] - 1, x["page"], x["page"] + 1) if pg >= 1))]
check("live grade", "every label is found on its own labelled page, so a right answer can score", not _unfound, _unfound)

# Tokens per question, from the 5 pages each would send: what a question costs (feeds ADR 5).
toks = [len(workflow.PROMPT) // 4 + sum(len(tools.call("read", symbol=x["symbol"], period=h["period"], page=h["page"])["text"]) for h in
        json.loads(tools.call("search", symbol=x["symbol"], query=x["q"])["text"])) // 4 for x in QS]
pin, pout = config.PRICES[config.FAST]
usd = (statistics.mean(toks) * pin + 400 * pout) / 1e6
lines.append(f"tokens per question: mean {statistics.mean(toks):,.0f} in (4 characters a token, estimated), about 400 out; "
             f"${usd:.4f} a question at flash-lite list price (finn/config.py)")

if "--live" in sys.argv:
    if not llm.has_key():
        lines.append("SKIP --live: no GEMINI_API_KEY (a free key is enough: these 26 questions are published)")
    else:
        import os; os.environ["FINN_FRESH"] = "1"   # two runs are two runs, not one replayed from cache
        def live_run(label):
            got = [(x, workflow.answer(x["symbol"], x["q"], public=True)) for x in QS]
            on_page = sum(r["verdict"] == "answered" and any(i.get("period") == x["period"] and abs(i.get("page", 0) - (x["page"] or 0)) <= 1
                          for i in r["items"]) for x, r in got if x["period"])
            grounded = sum(right(x, r) for x, r in got if x["period"])   # holds the labelled answer: the floor and the keep rule use this
            right_none = sum(r["verdict"] == "not_in_calls" for x, r in got if not x["period"])
            false = sum(r["verdict"] == "answered" for x, r in got if not x["period"])
            rejected = sum(r["verdict"] == "rejected" for _, r in got)
            down = sum(r["verdict"] == "unavailable" for _, r in got)
            fell = sum(r["degraded"] for _, r in got)
            spent = sum(r["trace"].get("usd", 0) + r["trace"].get("agent", {}).get("usd", 0) for _, r in got)   # dollars at list price
            lines.append(f"{label}: grounded {grounded}/20 (on the labelled page {on_page}/20), 'not in the calls' on {right_none}/6, answered unanswerable {false}/6, "
                         f"rejected by the checks {rejected}/26, unavailable {down}, degraded {fell}, ${spent:.4f}")
            return grounded, false, spent
        base = [live_run(f"live run {k}") for k in (1, 2)]
        if "--agent" in sys.argv:   # ADR 3's keep rule: the same 26, twice more, with the agent on after the workflow
            os.environ["FINN_AGENT"] = "1"
            esc = [live_run(f"live agent run {k}") for k in (1, 2)]
            os.environ.pop("FINN_AGENT")
            keep, gain, need, false, cost = keep_rule(base, esc)
            lines.append(f"keep rule (ADR 3): {gain:+d} grounded over the workflow (needs {need:+d}), answered unanswerable {false} (at most 1), "
                         f"cost {cost:.1f}x in dollars (at most 3x): {'PASS, once a person has judged the answers by hand' if keep else 'FAIL: the agent stays off'}")

ok, n = sum(res), len(res)
lines.append(f"TOTAL {ok}/{n}")
print("\n".join(lines))
(ROOT / "evals/answer_result.txt").write_text("\n".join(lines) + "\n")
sys.exit(0 if ok == n else 1)
