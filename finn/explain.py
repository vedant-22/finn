"""One line for a filing whose subject says nothing ("...has informed the Exchange about Acquisition"),
plus the rupee amount if there is one, so code can size it against the company."""
from . import llm, config
from .sources import pdf

SCHEMA = {"type": "object", "properties": {
    "line": {"type": "string"},
    "amount_cr": {"type": "number", "nullable": True},
    "routine": {"type": "boolean"},
}, "required": ["line", "amount_cr", "routine"]}

PROMPT = """Exchange filing by {company}, filed as "{desc}". Pages marked [[PAGE n]].
- line: what happened, at most 16 words, plain, with the key number. No adjectives, no "the company".
- amount_cr: the main rupee amount involved (deal value, penalty, demand, order size, capex) in Rs crore, or null. Convert lakh to crore (1 crore = 100 lakh). If the filing says the impact is not material or not quantifiable, use null.
- routine: true if this is a small, procedural matter (e.g. a tax demand the company says it will appeal with no material impact, incorporation of a small subsidiary, a routine order under appeal).
Use only this filing.

{text}"""

def explain(company, desc, url):
    pages = pdf.pages(url, max_pages=5)
    return llm.generate(PROMPT.format(company=company, desc=desc, text=pdf.paged_text(pages)[:20000]),
                        model=config.FAST, schema=SCHEMA, task="explain", max_tokens=1500)
