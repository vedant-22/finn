"""The promise ledger: what management said it would do, and whether it did.

Step 1 (cheap model, one call per transcript): pull out forward-looking commitments with a
verbatim quote and page. Code then checks every quote against the PDF and drops any it can't find.
Step 2 (stronger model, one call per company): grade each older promise against the reported
numbers and the latest call. Evidence quotes are verified the same way.
"""
from . import llm, config
from .sources import pdf

PROMISE_SCHEMA = {
    "type": "object",
    "properties": {
        "call_quarter": {"type": "string", "description": "Quarter the call discusses, e.g. Q2 FY27"},
        "promises": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "quote": {"type": "string"},
                "page": {"type": "integer"},
                "speaker": {"type": "string"},
                "topic": {"type": "string"},
                "metric": {"type": "string", "enum": ["revenue_growth", "margin", "profit", "volume", "capex", "capacity", "debt", "working_capital", "market_share", "launch", "other"]},
                "target": {"type": "string"},
                "by_when": {"type": "string"},
                "hard": {"type": "boolean"},
            },
            "required": ["quote", "page", "speaker", "topic", "metric", "target", "by_when", "hard"],
        }},
        "soft_count": {"type": "integer"},
    },
    "required": ["call_quarter", "promises", "soft_count"],
}

EXTRACT_PROMPT = """You are reading an Indian listed company's earnings-call transcript ({period} call).
Pages are marked [[PAGE n]].

List the forward-looking commitments made by MANAGEMENT (not analysts, not the moderator).
A commitment is a statement about what the company WILL achieve or do, looking forward from the date of the call: growth, margins, capex, capacity, launches, debt, working capital, market share.
Do not list things already done at the time of the call ("we invested", "the plant was commissioned"). Do not list historical results.

Rules:
- "quote" must be copied character for character from the transcript, 12 to 45 words, one continuous span. Do not fix grammar. Do not stitch sentences together.
- "page" is the [[PAGE n]] the quote is on.
- "target" is the commitment in at most 10 words, with the number if there is one (e.g. "EBITDA margin 12-13%", "commission Ghiloth plant").
- "by_when" is the time frame as stated ("FY27", "next 2 quarters", "by March 2027"). Use "unspecified" if none.
- hard = true only if the commitment has a number or a concrete deliverable AND a time frame. Everything else (e.g. "we remain confident of strong growth") is hard = false.
- At most 8 hard commitments, the most material ones. Include soft ones only if they concern margins, growth or capex, at most 4.
- soft_count = how many other vague, optimistic forward statements management made that you did not list.
- If a commitment repeats, list it once, from the clearest statement.
- Use only this transcript. Do not use anything you know about the company from elsewhere.

TRANSCRIPT:
{text}
"""

def extract_promises(url, period):
    pages = pdf.pages(url, max_pages=60)
    text = pdf.paged_text(pages)
    out = llm.generate(EXTRACT_PROMPT.format(period=period, text=text[:180000]),
                       model=config.FAST, schema=PROMISE_SCHEMA, task="promise_extract", max_tokens=6000)
    kept, dropped = [], 0
    for p in out.get("promises", []):
        found = pdf.verify_quote(p["quote"], pages, p.get("page") or 1)
        if found is None:
            dropped += 1
            continue
        p["page"] = found
        p["period"] = period
        p["url"] = url
        kept.append(p)
    return {"period": period, "call_quarter": out.get("call_quarter"), "url": url,
            "pages": len(pages), "promises": kept, "dropped_unverified": dropped,
            "soft_count": out.get("soft_count", 0)}

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "grades": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "repeat_of": {"type": "integer", "description": "id of an earlier promise that is the same commitment restated, else -1"},
                "status": {"type": "string", "enum": ["kept", "missed", "partly", "pending", "quiet", "unclear"]},
                "verdict": {"type": "string"},
                "evidence_kind": {"type": "string", "enum": ["numbers", "quote", "none"]},
                "evidence": {"type": "string"},
                "evidence_page": {"type": "integer"},
            },
            "required": ["id", "repeat_of", "status", "verdict", "evidence_kind", "evidence"],
        }},
        "read": {"type": "string"},
        "questions": {"type": "array", "items": {"type": "string"}},
        "bull": {"type": "array", "items": {"type": "string"}},
        "bear": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["grades", "read", "questions", "bull", "bear"],
}

GRADE_PROMPT = """You are an analyst at a long-only fund checking whether management of {name} did what it said.
Today is {today}. The latest results are for {latest_q}.

PROMISES made on earlier calls (id, call, speaker, target, by when, quote):
{promises}

REPORTED NUMBERS ({basis}, Rs crore) from the company's filed results:
{numbers}

LATEST CALL ({latest_period}), pages marked [[PAGE n]]:
{latest}

For each promise decide (if a promise restates an earlier one, set repeat_of to the earlier id and grade it the same way):
- kept: delivered, or clearly on track with the reported numbers or a concrete statement on the latest call.
- missed: the time frame has passed (or the numbers make it impossible) and it was not delivered.
- partly: some delivered, some not, or delivered late.
- pending: the time frame has not passed and nothing yet says it is off track.
- quiet: the time frame matters now, but management did not mention it on the latest call and the numbers cannot settle it.
- unclear: the numbers we have cannot measure it (e.g. a segment number we don't have) and the call doesn't settle it.

Only settle a promise with numbers that measure the same thing. Company-wide OPM cannot settle a segment margin or a "contribution margin" promise; company revenue cannot settle a segment's growth. In those cases use the latest call, or mark it unclear.

"verdict": one plain sentence, at most 18 words, saying what was promised against what happened, with the numbers. No adjectives like "strong" or "impressive".
"evidence_kind": "numbers" if the reported numbers settle it (then "evidence" states the exact figures used, e.g. "OPM Q1 FY27 7%, Q2 FY27 9%"), "quote" if the latest call settles it (then "evidence" is copied character for character from the latest call, 12 to 45 words, and "evidence_page" is its page), else "none".

Then:
- "read": two sentences at most on how far this management's word can be relied on, based only on the grades above. If fewer than three promises are kept, missed or partly, say plainly that there is too little settled yet to judge, and say what falls due next.
- "questions": the 2 or 3 questions an investor should put to management on the next call, each under 20 words, pointed at missed, partly or quiet promises.
- "bull" and "bear": 2 or 3 points each, under 18 words, each resting on a number above or a graded promise.

Write like an analyst's margin note: short, concrete, with the numbers. Name the pattern if there is one (for example "hits revenue targets, misses margin targets", "dates slip by a quarter"). Never use: demonstrates, strong, robust, healthy, execution capability, generally, aligned, overall, notably, solid.

Use only the material above. If something is not in it, do not say it. Do not use outside knowledge of the company or the industry.
"""

def grade(name, basis, today, latest_q, promises, numbers_text, latest_period, latest_url):
    latest_pages = pdf.pages(latest_url, max_pages=60) if latest_url else []
    lines = [f"{i}. [{p['period']} call, p{p['page']}] {p['speaker']}: {p['target']} | by {p['by_when']} | \"{p['quote']}\""
             for i, p in enumerate(promises)]
    prompt = GRADE_PROMPT.format(name=name, today=today, latest_q=latest_q, promises="\n".join(lines) or "(none)",
                                 basis=basis, numbers=numbers_text, latest_period=latest_period,
                                 latest=pdf.paged_text(latest_pages)[:160000] if latest_pages else "(no transcript available)")
    out = llm.generate(prompt, model=config.SMART, schema=GRADE_SCHEMA, task="promise_grade", max_tokens=16000, temperature=0.2)
    for g in out.get("grades", []):
        if g.get("evidence_kind") == "quote":
            found = pdf.verify_quote(g.get("evidence", ""), latest_pages, g.get("evidence_page") or 1)
            if found is None:
                # The model's evidence quote isn't in the transcript. Keep the grade only if it doesn't depend on it.
                g["evidence_kind"], g["evidence"] = "none", ""
                if g["status"] in ("kept", "missed", "partly"):
                    g["status"] = "unclear"
                    g["verdict"] = "Could not verify the evidence for this one in the latest call."
            else:
                g["evidence_page"] = found
                g["evidence_url"] = latest_url
    return out
