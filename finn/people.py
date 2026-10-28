"""Management changes: who is coming, who is going, and where the new person comes from.

SEBI's disclosure rules make the company file a "brief profile" of every incoming director or KMP,
so the background comes from the company's own filing. No LinkedIn scraping.
"""
from . import llm, config
from .sources import pdf

SCHEMA = {"type": "object", "properties": {
    "people": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"},
        "role": {"type": "string"},
        "action": {"type": "string", "enum": ["appointed", "resigned", "retired", "ceased", "redesignated", "re-appointed", "died"]},
        "seniority": {"type": "string", "enum": ["top", "board", "senior", "other"]},
        "effective": {"type": "string"},
        "reason": {"type": "string"},
        "background": {"type": "string"},
        "previous": {"type": "array", "items": {"type": "string"}},
        "education": {"type": "string"},
        "quote": {"type": "string"},
        "page": {"type": "integer"},
    }, "required": ["name", "role", "action", "seniority", "effective", "reason", "background", "previous", "education", "quote", "page"]}},
}, "required": ["people"]}

PROMPT = """This is a filing by {company} to the stock exchange about a change in its management. Pages are marked [[PAGE n]].

For each person joining, leaving or changing role:
- seniority: "top" ONLY for CEO, MD, CFO, chairman, or an executive/whole-time director (or a CEO-designate of the whole company); "board" for independent or non-executive directors; "senior" for other senior management, including business/SBU/division heads, presidents, vice presidents and functional heads; "other" for company secretary, compliance officer and similar.
- reason: for exits, the stated reason in at most 10 words, or "not stated".
- background: for people joining, who they are in at most 22 words, from the profile in this filing. "" for exits.
- previous: up to 3 earlier employers or roles, as "Role, Organisation", from this filing.
- education: degrees from this filing, short.
- quote: 12 to 40 words copied exactly from the filing that support the name and role. page: its page.
Use only this filing.

FILING:
{text}"""

def from_filing(company, url):
    pages = pdf.pages(url, max_pages=15)
    out = llm.generate(PROMPT.format(company=company, text=pdf.paged_text(pages)[:40000]),
                       model=config.FAST, schema=SCHEMA, task="people", max_tokens=4000)
    people = []
    for p in out.get("people", []):
        p["verified"] = pdf.verify_quote(p.get("quote", ""), pages, p.get("page") or 1) is not None
        people.append(p)
    return people
