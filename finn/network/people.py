"""People: the investor, their contacts, and everyone named in a management-change filing.

A filing person is built from the company's own SEBI filing (finn/people.py reads it; only records
whose quote was found on the page are used). The same person often appears in several filings, with
the name spelt differently, so records for one company are merged when the names are compatible.
"""
import datetime as dt
import re
from dataclasses import dataclass, field

from . import names, roles

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
SENIORITY = {"top": 3, "board": 2, "senior": 1, "other": 0}
EXITS = {"resigned", "retired", "ceased", "died"}
RELABEL = r"non[- ]?smp|\bcategory\b|\bdesignat"   # "Changed from SMP to Non-SMP category": nobody left a seat

def relabel(e):
    """A filed "ceased" that only moves a person off the senior-management list: still in the job."""
    return e["action"] == "ceased" and bool(re.search(RELABEL, e.get("reason") or "", re.I))
# A seat elsewhere that the filing's own profile opens with: "Founder & CEO of Samara Capital Group, a leading ...".
# Only a title that runs or owns a firm, so "Nominee Director of LIC" (LIC's nominee, not its director) is not read as one.
HOLDS = re.compile(r"^((?:Co-?)?(?:Founder|Chief Executive|CEO|Managing Director|Managing Partner|Partner|Chairman|Chairperson|President)"
                   r"(?:[ ,&-]+[A-Za-z]+)*?) of ([^,.;]+)", re.I)


def parse_date(text, fallback=None):
    """'27th October, 2026', 'October 30, 2026', '05.10.2026' -> date. Anything else -> fallback."""
    t = text.lower()
    m = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", t)
    try:
        if m:
            return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?(?: of)? ([a-z]{3})[a-z]*,? (\d{4})\b", t)
        if m and m.group(2) in MONTHS:
            return dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        m = re.search(r"\b([a-z]{3})[a-z]* (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})\b", t)
        if m and m.group(1) in MONTHS:
            return dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    except ValueError:
        pass
    return fallback


@dataclass
class Stint:
    org: object
    role: str = ""
    start: int = None          # year, or None when not known
    end: int = None            # year, or None when not known or still there
    current: bool = False      # still there when the record was read
    division: str = ""
    source: str = "given"      # given (the investor's own list) or filing

    @property
    def level(self):
        return roles.level(self.role)

    @property
    def function(self):
        return roles.function(self.role, self.org)

    def years(self):
        if self.start and (self.end or self.current):
            return f"{self.start}–{'now' if self.current else self.end}"
        if self.end:
            return f"until {self.end}"
        if self.start:
            return f"from {self.start}"
        return ""


@dataclass
class Study:
    school: str                # registry id, or the raw text when the school isn't known
    name: str
    degree: str = ""
    start: int = None
    end: int = None
    source: str = "given"

    def years(self):
        return "" if not self.start else f"{self.start}–{self.end}"


@dataclass
class Person:
    id: str
    name: str
    kind: str                  # me, contact, filing
    career: list = field(default_factory=list)
    edu: list = field(default_factory=list)
    asof: dt.date = None       # when the career above was last read
    # contacts
    how: str = ""              # family, friend, colleague, classmate, met
    since: int = None
    met: list = field(default_factory=list)
    # filing people
    symbol: str = ""
    company: object = None
    events: list = field(default_factory=list)
    education_text: str = ""
    background: str = ""
    listed: list = field(default_factory=list)   # (organisation, role): earlier employers as the filing lists them, in its order
    holds: tuple = None        # (organisation, role): a seat at another, known organisation that the filing's profile opens with
    inside: bool = False       # known, from the investor's own record, to have been in the company already

    @property
    def current(self):
        now = [s for s in self.career if s.current]
        return now[-1] if now else None

    @property
    def seniority(self):
        return max((e["seniority"] for e in self.events), key=SENIORITY.get, default="other")

    @property
    def change(self):
        """joins, leaves or moves (changes role inside the company), from all of this person's filings."""
        acts = {e["action"] for e in self.events if not relabel(e)}
        if not acts:
            return "moves"                                  # only taken off a list, still in the job (see `stays`)
        inside = any(s.org is self.company and s.source == "filing" and not s.current for s in self.career)
        if acts & EXITS and not acts - EXITS:
            return "leaves"
        if acts & EXITS or "redesignated" in acts or inside or self.inside:
            return "moves"
        return "joins"

    @property
    def stays(self):
        """Every filing about this person is a relabel: the same job, off the senior-management list."""
        return bool(self.events) and all(relabel(e) for e in self.events)

    @property
    def event(self):
        """The filing that best states where this person now stands: the latest, an arrival over an exit."""
        return max(self.events, key=lambda e: (e["action"] not in EXITS, e["effective"], e["at"]))

    def last_met(self):
        return max(self.met) if self.met else None


def _career(reg, rows, source):
    out = []
    for row in rows:
        org_name, role, start, end = row[:4]
        out.append(Stint(reg.org(org_name), role, start, end, current=end is None,
                         division=row[4] if len(row) > 4 else "", source=source))
    return out


def _edu(reg, rows, source):
    out = []
    for school, degree, start, end in rows:
        ids = reg.schools_in(school)
        out.append(Study(ids[0] if ids else school, reg.schools[ids[0]] if ids else school, degree, start, end, source))
    return out


def contact(reg, c, asof, kind="contact"):
    return Person(c["id"], c["name"], kind, _career(reg, c["career"], "given"), _edu(reg, c.get("edu", []), "given"),
                  dt.date.fromisoformat(c.get("asof", asof)), c.get("how", ""), c.get("since"),
                  [dt.date.fromisoformat(d) for d in c.get("met", [])])


def slug(name):
    return "-".join(names.tokens(name)[0] + names.tokens(name)[1])


def from_filings(reg, filings, company_names=None):
    """One Person per human per company, from every verified people record in the filings."""
    people = []
    for f in sorted(filings, key=lambda f: f["at"]):
        filed = dt.date.fromisoformat(f["at"][:10])
        for rec in f.get("people") or []:
            if not rec.get("verified") or not rec.get("name"):
                continue
            who = next((p for p in people if p.symbol == f["symbol"] and names.compare(p.name, rec["name"])), None)
            if who is None:
                company = reg.by_symbol.get(f["symbol"]) or reg.org((company_names or {}).get(f["symbol"], f["symbol"]))
                who = Person(f"{slug(rec['name'])}@{f['symbol']}", names.clean(rec["name"]), "filing",
                             symbol=f["symbol"], company=company, asof=filed)
                people.append(who)
            effective = parse_date(rec.get("effective", ""), filed)
            event = {"filing": f["id"], "at": f["at"], "url": f["url"], "role": rec["role"], "action": rec["action"],
                     "seniority": rec["seniority"], "effective": effective, "reason": rec.get("reason", ""),
                     "stated": parse_date(rec.get("effective", "")) is not None,
                     "quote": rec.get("quote", ""), "page": rec.get("page")}
            same = [e for e in who.events if (e["action"], e["effective"]) == (event["action"], event["effective"])]
            if same:
                same[0].setdefault("also", []).append(f["id"])     # the same change, filed again
            else:
                who.events.append(event)
            who.asof = max(who.asof, filed)
            who.background = who.background or rec.get("background", "")
            m = HOLDS.match((rec.get("background") or "").strip())
            if m and rec["action"] not in EXITS and who.holds is None:
                at = reg.orgs_in(m.group(2))                    # a name the registry knows, never one made up from the text
                if len(at) == 1 and at[0] is not who.company and not (at[0].group and at[0].group == who.company.group):
                    who.holds = (at[0], m.group(1).strip())
            listed = []
            for text in rec.get("previous") or []:
                org, role, _ = reg.stint_parts(text, exact=True)
                if not any(o is org for o, _ in listed):
                    listed.append((org, role))
            if len(listed) > len(who.listed):                   # the fuller filing, when one person has two
                who.listed = listed
            for text in rec.get("previous") or []:
                org, role, division = reg.stint_parts(text, exact=True)
                if not any(s.org is org for s in who.career):
                    who.career.append(Stint(org, role, division=division, source="filing"))
            if rec.get("education") and rec["education"] not in who.education_text:
                who.education_text = (who.education_text + "; " + rec["education"]).strip("; ")
                for sid in reg.schools_in(rec["education"]):
                    if not any(s.school == sid for s in who.edu):
                        who.edu.append(Study(sid, reg.schools[sid], source="filing"))
    for who in people:
        e = who.event
        year = e["effective"].year
        if e["action"] in EXITS and not relabel(e):
            who.career.append(Stint(who.company, e["role"], end=year, source="filing"))
        elif e["action"] == "appointed" and who.change == "joins":
            who.career.append(Stint(who.company, e["role"], start=year, current=True, source="filing"))
        else:
            who.career.append(Stint(who.company, e["role"], current=True, source="filing"))
    return people
