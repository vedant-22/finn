"""Reading a job title: how senior it is, what the person does all day, and what they would know.

Rules on words, in a fixed order, so the same title always reads the same way and each reading can be tested.
"""
import re

LEVELS = [
    (5, r"\bceo\b|managing director|\bmd\b|chief executive|founder|chairman|chairperson|managing partner"),
    (4, r"\bchief\b.*\bofficer|\bc[fomtir]o\b|\bchro\b|(?<!vice )\bpresident|executive director|whole-?time director"),
    (2, r"\bregional\b|\bzonal\b|general manager|fund manager|senior manager|\bprincipal\b"),
    (3, r"\bpartner\b|vice president|\bdirector\b|\bhead\b|general counsel"),
]

# Professional firms: the firm's trade is the person's work, whatever the title says.
TRADE = {"law": "legal", "audit": "tax_audit", "consulting": "consulting"}

FUNCTIONS = [
    ("board", r"independent director|non-?\s?executive|nominee director|additional director|chairperson of the board"),
    ("legal", r"\blegal|\bcounsel|company secretary|\bcompliance"),
    ("tax_audit", r"\btax|\baudit"),
    ("treasury", r"\btreasury"),
    ("risk", r"\brisk|\bcredit\b|\bunderwriting"),
    ("finance", r"\bcfo\b|\bfinanc|\baccounts\b|\bcontroller"),
    ("hr", r"human resources|\bhr\b|\bchro\b"),
    ("purchasing", r"\bpurchas|\bprocurement|supply chain|\bsourcing"),
    ("projects", r"\bprojects?\b"),
    ("operations", r"\bproduction|\bplant\b|\bmanufacturing|\boperations|\boperating officer|\bcoo\b|\bdelivery|\bservices?\b|\bzonal|regional manager"),
    ("rnd", r"r&d|\btechnology officer|\bcto\b|\bchemistry|\bbiology|\bengineer|\bassembly"),
    ("sales", r"\bsales|\bmarketing|\bbrand\b|\bcmo\b|\bretail (?:head|officer)|chief retail"),
    ("research", r"\banalyst|\bresearch"),
    ("investing", r"\binvestments?\b|fund manager|\bcio\b"),
    ("strategy", r"\bstrategy|corporate development|\bgrowth"),
    ("it", r"\binformation\b|\bcyber"),
    ("general", r"\bceo\b|managing director|\bmd\b|founder|chief executive|\bpresident|chairman|\bbusiness\b|sbu head|ic head|executive director"),
]

# What someone in each line of work knows about their employer, in a few words.
KNOWS = {
    "general": "how the business is run and where it makes its money",
    "finance": "how the numbers are put together, the funding and the auditors",
    "treasury": "the funding costs and the lenders",
    "tax_audit": "the tax positions and the disputes behind them",
    "legal": "the disputes, the regulators and how the company handles them",
    "risk": "how credit is underwritten and where the book is weak",
    "hr": "who is leaving, who is being hired and why",
    "purchasing": "the suppliers, what they are paid and who gets the volume",
    "projects": "how capex is planned and whether projects land on time and budget",
    "operations": "the operations, the costs and what goes wrong day to day",
    "rnd": "the pipeline and what the labs and engineers can really do",
    "sales": "the customers, the pricing and where share is won or lost",
    "research": "how the market reads the sector and its managements",
    "investing": "how investors size up the business",
    "strategy": "the deals and bets management is weighing",
    "it": "the systems the business runs on",
    "board": "what the board is asked to approve and how management answers it",
    "consulting": "the industry's economics, seen across several clients",
    "other": "",
}

# How much a line of work says about the industry itself (as against the back office).
WEIGHT = {"general": 1.0, "sales": 1.0, "operations": 1.0, "rnd": 1.0, "purchasing": 1.0, "projects": 0.9,
          "risk": 1.0, "strategy": 0.9, "research": 0.9, "investing": 0.8, "consulting": 0.8, "finance": 0.8,
          "treasury": 0.7, "board": 0.7, "hr": 0.5, "legal": 0.4, "tax_audit": 0.4, "it": 0.4, "other": 0.3}


def level(role):
    """5 runs the organisation, 4 runs a function of it, 3 a large team, 2 a region or a desk, 1 everyone else."""
    r = role.lower()
    for n, pattern in LEVELS:
        if re.search(pattern, r):
            return n
    return 1


def function(role, org=None):
    r = role.lower()
    if re.search(FUNCTIONS[0][1], r):
        return "board"
    if org is not None:
        for theme, fn in TRADE.items():
            if theme in org.themes:
                return fn
    for fn, pattern in FUNCTIONS[1:]:
        if re.search(pattern, r):
            return fn
    if org is not None and {"private equity", "family office"} & set(org.themes):
        return "investing"
    return "general" if level(role) >= 3 else "other"


GENERIC = {"head", "group head", "president", "vice president", "senior vice president", "executive vice president", "director"}


def short(role):
    """A role short enough to sit in a sentence: 'Vice President - Transformer Business' -> 'Vice President,
    Transformer Business'; 'Managing Director & Chief Executive Officer' -> 'MD & CEO'. Board seats read as what they are."""
    r = role.lower()
    if re.search(FUNCTIONS[0][1], r) or "director (non" in r or "vice chairman" in r:
        return ("vice chairman" if "vice chair" in r else "chairperson" if "chair" in r else "independent director" if "independent" in r
                else "nominee director" if "nominee" in r else "director")
    if re.search(r"managing director|\bmd\b", r) and re.search(r"\bceo\b|chief executive", r):
        return "MD & CEO"
    head = re.split(r"\s+[-–]\s+|\s+&\s+(?=IC |SBU |Head|Chief|Company|Compliance)|,|\s+\(", role)[0].strip()
    rest = re.split(r",|\s+&\s+|\s+and\s+|\)", role[len(head):].lstrip(" ,-–&("))[0].strip()
    return f"{head}, {rest}" if head.lower() in GENERIC and rest else head
