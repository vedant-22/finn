"""Sort exchange filings into the reference categories and decide how loud each one is.

Three tiers, and the policy is the product:
  act    — interrupts you. Results, M&A, top-level management change, litigation/regulatory action,
           fund raising, rating changes, defaults, auditor exits, pledges.
  note   — shown with one line. Orders, capex, dividends, splits, transcripts, investor decks, general updates that say something.
  fold   — counted, not shown. Trading-window notices, newspaper ads, compliance certificates, ESOP allotments, meeting schedules.

NSE's own subject ("desc") settles about 85% of filings for free. A cheap model only sees the vague ones
("General Updates", "Updates", "Press Release", "Outcome of Board Meeting" without results, "Others").
"""
import re
from . import llm, config
from .sources import pdf

RULES = {
    # desc: (category, tier)
    "Acquisition": ("M&A", "act"), "Amalgamation/Merger": ("M&A", "act"), "Demerger": ("M&A", "act"),
    "Sale or disposal": ("M&A", "act"), "Scheme of Arrangement": ("M&A", "act"), "Diversification/Disinvestment": ("M&A", "act"),
    "Other Restructuring": ("M&A", "act"), "Public Announcement-Open Offer": ("M&A", "act"),
    "Change in Management": ("management_change", "act"), "Appointment": ("management_change", "act"),
    "Resignation of Director/KMP/SMP": ("management_change", "act"), "Resignation": ("management_change", "act"),
    "Cessation": ("management_change", "act"), "Retirement": ("management_change", "act"), "Demise": ("management_change", "act"),
    "Change in Director(s)": ("management_change", "act"), "Change in Auditors": ("management_change", "note"),
    "Resignation of Statutory Auditor": ("litigation", "act"),
    "Change in Company Secretary/Compliance Officer": ("management_change", "fold"),
    "Action(s) taken or orders passed": ("litigation", "act"), "Action(s) initiated or orders passed": ("litigation", "act"),
    "Pendency of Litigation(s)/dispute(s) or the outcome impacting the Company": ("litigation", "act"),
    "Corporate Insolvency Resolution Process": ("litigation", "act"), "Fraud/Default/Arrest": ("litigation", "act"),
    "Defaults on Payment of Interest/Principal": ("litigation", "act"), "Initiation of Forensic Audit": ("litigation", "act"),
    "Frauds/Default by employees": ("litigation", "act"), "Delay/default in the payment of fines/penalties/dues etc. to authority": ("litigation", "act"),
    "Strikes/Lockouts/Disturbances": ("litigation", "act"), "Disruption of Operations": ("litigation", "act"),
    "Closure of operations": ("litigation", "act"),
    "Granting/withdrawal/surrender/cancellation/suspension of key licenses/ regulatory approvals": ("litigation", "note"),
    "Qualified Institutional Placement": ("fund_raise", "act"), "Rights Issue": ("fund_raise", "act"),
    "Preferential issue": ("fund_raise", "act"), "Buyback": ("fund_raise", "act"), "Public Announcement - Buyback of Shares": ("fund_raise", "act"),
    "Issue of Securities": ("fund_raise", "note"), "Post Buyback Public Announcement": ("fund_raise", "fold"), "Closure of Buy Back": ("fund_raise", "fold"),
    "Statement of deviation(s) or variation(s) under Reg. 32": ("fund_raise", "fold"), "Monitoring Agency Report": ("fund_raise", "fold"),
    "Utilisation of Funds": ("fund_raise", "fold"),
    "Disclosure under SEBI Takeover Regulations": ("insider_trading", "note"), "Trading Plan under PIT": ("insider_trading", "note"),
    "Credit Rating- Revision": ("credit_rating", "act"), "Credit Rating- New": ("credit_rating", "note"),
    "Credit Rating- Others": ("credit_rating", "fold"), "Credit Rating": ("credit_rating", "fold"),
    "Dividend": ("dividend", "note"), "Record Date": ("dividend", "fold"), "Revised Record date": ("dividend", "fold"),
    "Bonus": ("bonus_split", "note"), "Stock split": ("bonus_split", "note"),
    "Capacity addition": ("capex", "note"), "Commencement of commercial production/operations": ("capex", "note"),
    "Postponement of commercial production/operations": ("capex", "act"), "Adoption of new line(s) of business": ("capex", "note"),
    "Bagging/Receiving of orders/contracts": ("press_release", "note"), "Awarding of order(s)/contract(s)": ("press_release", "note"),
    "Agreements": ("press_release", "note"), "Memorandum of Understanding/Agreements": ("press_release", "note"),
    "Arrangements for strategic, technical, manufacturing, or marketing tie up": ("press_release", "note"),
    "Product launch": ("press_release", "note"), "Rescission/termination(s)": ("press_release", "note"),
    "Rumour Verification - Regulation 30(11)": ("press_release", "note"), "News Verification": ("press_release", "fold"),
    "Monthly Business Updates": ("press_release", "note"), "Related Party Transactions": ("press_release", "note"),
    "Giving guarantees/indemnity/ becoming a surety for third party": ("press_release", "note"),
    "Investor Presentation": ("earnings_call", "note"),
    "Shareholders meeting": ("agm_egm", "fold"), "Extension of Annual General Meeting": ("agm_egm", "fold"),
    "Clarification - Financial Results": ("results", "note"), "Reply to Clarification- Financial results": ("results", "note"),
    "Integrated Filing- Financial": ("results", "fold"), "Integrated Filing- Governance": ("unclassified", "fold"),
    "Reasons for Delayed/Non-submission of Financial Results": ("results", "act"),
    "Spurt in Volume": ("press_release", "fold"), "Price movement": ("press_release", "fold"),
}
FOLD_DESCS = {
    "Certificate under SEBI (Depositories and Participants) Regulations, 2018", "Trading Window", "Copy of Newspaper Publication",
    "ESOP/ESOS/ESPS", "Options to purchase securities", "Structural Digital Database", "Allotment of Securities",
    "Loss of Share Certificates", "Issue of Duplicate Share Certificate", "Committee Meeting Updates", "Amendment to AOA/MOA",
    "Quarterly Compliance Report on Corporate governance - within 21 days from the end of the quarter", "Corrigendum", "Addendum",
    "Registrar & Share Transfer Agent Update", "Address Change", "Increase in Authorised Capital", "Name Change",
    "Name and Symbol Change", "Redemption", "Conversion", "Extension  of Financial Year", "Alteration/revision(s)", "Suspension of Trading",
    "Delisting", "Press Release (Revised)",
}
VAGUE = {"General Updates", "Updates", "Press Release", "Others", "Outcome of Board Meeting", "Disclosure of material issue",
         "Effect(s) on listed entity due to changed regulatory  framework applicable"}

def by_rule(x):
    desc, text = x.get("desc", ""), (x.get("attchmntText") or "").lower()
    if desc == "Analysts/Institutional Investor Meet/Con. Call Updates":
        if "transcript" in text or "transcript" in (x.get("attchmntFile") or "").lower():
            return "earnings_call", "note", "rule"
        if "presentation" in text:
            return "earnings_call", "note", "rule"
        return "investor_meetings", "fold", "rule"
    if desc == "Outcome of Board Meeting" and "financial result" in text:
        return "results", "act", "rule"
    if desc in RULES:
        c, t = RULES[desc]
        return c, t, "rule"
    if desc in FOLD_DESCS:
        return "unclassified", "fold", "rule"
    return None

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "i": {"type": "integer"},
    "category": {"type": "string", "enum": ["results", "M&A", "fund_raise", "management_change", "litigation", "insider_trading",
                                             "earnings_call", "investor_meetings", "credit_rating", "dividend", "bonus_split", "capex",
                                             "press_release", "postal_ballot", "agm_egm", "pledging", "unclassified"]},
    "tier": {"type": "string", "enum": ["act", "note", "fold"]},
    "line": {"type": "string"},
}, "required": ["i", "category", "tier", "line"]}}

PROMPT = """These are corporate filings by Indian listed companies. For each, give:
- category from the list;
- tier: "act" if a long-term shareholder must look today (results, deals, top management change, legal or regulatory action, fund raise, default),
  "note" if worth one line (orders, capacity, launches, business updates with numbers), "fold" if routine paperwork (meeting schedules, newspaper ads, compliance, clarifications with nothing new);
- line: what the filing says, at most 14 words, with any number in it. No adjectives. If the subject says nothing beyond the filing type, write "".

{items}

Return a JSON array with one object per filing, using its index i."""

def classify(rows):
    """Adds category, tier, line, how to each row in place. Batches vague ones 25 at a time."""
    vague = []
    for x in rows:
        r = by_rule(x)
        if r:
            x["category"], x["tier"], x["how"] = r
            x["line"] = ""
        else:
            vague.append(x)
    for x in vague:
        x["_body"] = _body(x) if _says_nothing(x) else ""
    for k in range(0, len(vague), 20):
        batch = vague[k:k + 20]
        items = "\n".join(f"{i}. [{x['sm_name']}] {x['desc']}: {(x.get('attchmntText') or '')[:400]}"
                          + (f"\n   Letter: {x['_body']}" if x["_body"] else "") for i, x in enumerate(batch))
        try:
            out = llm.generate(PROMPT.format(items=items), model=config.FAST, schema=SCHEMA, task="classify", max_tokens=6000)
        except llm.LLMError:
            out = []
        got = {o["i"]: o for o in out if isinstance(o, dict)}
        for i, x in enumerate(batch):
            o = got.get(i)
            if o:
                x["category"], x["tier"], x["line"], x["how"] = o["category"], o["tier"], o["line"], "model"
            else:
                x["category"], x["tier"], x["line"], x["how"] = "unclassified", "note", "", "fallback"
    return rows


def _says_nothing(x):
    """NSE subjects like '...has informed the Exchange about General Updates' carry no information."""
    t = re.sub(r"^.*?has (informed|submitted to) the Exchange( about| regarding)?", "", x.get("attchmntText") or "", flags=re.I)
    t = re.sub(r"(general updates|updates|press release dated [\w ,]+\d{4}\.?|outcome of (the )?board meeting( held on [\w ,]+)?)", "", t, flags=re.I)
    return len(re.findall(r"[A-Za-z]{3,}", t)) < 6

def _body(x, n=900):
    """The letter's text after the letterhead and address block, where the subject line starts."""
    try:
        t = " ".join(" ".join(pdf.pages(x["attchmntFile"], max_pages=2)).split())
    except Exception:
        return ""
    m = re.search(r"\b(Sub(ject)?\s*[:.\-–]|Intimation under|Outcome of|Dear Sir)", t, re.I)
    return (t[m.start():] if m else t[300:])[:n]
