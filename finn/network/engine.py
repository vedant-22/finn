"""The Network: what the investor's contacts can tell them about a company, a person or a theme.

Everything here is computed from three inputs: the investor's own contact list, the people named in
company filings, and a small registry of organisations. No model is called. Every answer carries the
evidence it rests on, and when the evidence is thin the answer says so or stays silent.
"""
import datetime as dt
import json
import math
import pathlib
import re

from . import identity, links, names, people, roles
from .registry import Registry, ROOT

LEVEL_W = {5: 1.0, 4: 1.0, 3: 0.85, 2: 0.65, 1: 0.45}
RELATION_W = {"inside": 1.0, "former": 1.0, "customer": 0.8, "supplier": 0.7, "competitor": 0.6, "watcher": 0.6,
              "group": 0.4, "sector": 0.3}
# Which lines of work can speak to which kind of event.
FOCUS = {"capex": {"projects", "operations", "general", "strategy"}, "litigation": {"legal", "tax_audit", "finance"},
         "M&A": {"strategy", "finance", "general", "investing"}, "fund_raise": {"treasury", "finance"},
         "results": {"finance", "general", "sales", "operations"}, "credit_rating": {"treasury", "finance"},
         "management_change": {"hr", "general", "board"}}
MATERIAL = ("M&A", "capex", "litigation", "fund_raise", "results")
# Which outside seats can speak to which kind of event. A customer sees a capex plan coming; nobody outside sees a bond issue.
OUTSIDE = {"capex": {"customer", "supplier"}, "M&A": {"customer", "supplier"}, "results": {"customer"},
           "litigation": {"watcher"}}
EVENT_WORD = {"M&A": "a deal", "capex": "a capex plan", "litigation": "a legal or tax matter", "fund_raise": "a fund raise",
              "results": "results", "management_change": "a management change"}
ALSO = {"inside": ", {org} itself", "former": ", {org} itself", "competitor": ", a competitor", "customer": ", a customer of {org}",
        "supplier": ", a supplier to {org}"}
# The lines of work a question may set against each other, and the word each goes by in a sentence.
LINE = {"finance": "finance", "treasury": "treasury", "risk": "risk", "operations": "operations", "sales": "sales",
        "legal": "legal", "tax_audit": "audit", "hr": "HR", "purchasing": "purchasing", "projects": "projects",
        "rnd": "R&D", "strategy": "strategy", "it": "IT"}
# Every question FINN can put on a person's path, in one table. A question is written for what the contact
# can know without having met the person: the seat, the institution, the trade. None uses a pronoun.
ASK = {
    "seat_across": "Where did {theirs} and {seat} pull against each other at {company}?",
    "seat_same": "What did the {seat} seat at {company} have to hold the line on?",
    "seat_board": "What should a new {role} at {company} ask about first?",
    "seat_other": "What should a new {role} at {company} fix first?",
    "there_now": "What is {name} remembered for at {employer}?",
    "was_across": "Were you at {employer} with {name}, and what did {theirs} need from the {role}?",
    "was_there": "Were you at {employer} with {name}, and what is {first} remembered for there?",
    "gap": "What catches a new {role} out in {trade}?",
    "interim": "What was the interim brief at {employer}?",
    "gap_room": "What carries over from {employers} to {trade}?",
    "holds": "Does {employer} hold, or deal with, anything connected to {company}?",
    "held": "Did {employer} hold, or deal with, anything connected to {company} in your time there?",
    "only": "What would you look at first in {company}'s {thing}?",
    # A question about this year's numbers goes to someone who sees the market from a seat today, about their own seat:
    # no time in it, and nothing about the other company's figures
    "market": "How does the {trade} market look from {employer}?",
    "supplier": "How does {company} rate as a supplier of {thing}?",
    # ... and the same seat, on the subject of the question it sits under: a margin, or a fall in profit
    "costs": "Which costs are moving most in {trade}, as {employer} sees it?",
    "oneoff": "Which one-off items are hitting {trade}, as {employer} sees it?",
    "charges": "Has {company} changed what it charges {employer} for {thing}?",
    "credit": "How are credit costs moving in {trade}, as {employer} sees it?",
}
# The seats that see the market now, by how the contact's employer stands to the company
NUMBERS = {"competitor": {"finance", "general", "sales", "operations", "strategy", "treasury"},
           "customer": {"purchasing", "operations", "general", "finance", "projects"}}
ONLY_THING = {"results": "results", "capex": "capex plan", "M&A": "deal", "litigation": "legal or tax matter", "fund_raise": "fund raise"}
# The seats that check a company from inside: audit, risk, compliance, legal, the company secretary, finance.
# Read from the title itself, not from the line of work: "Group Head - Vehicle Finance" sells loans and is no control seat.
CONTROL = {"tax_audit", "risk", "legal", "finance"}        # the lines of work whose people can speak to these seats
AREAS = [(r"\baudit", "audit"), (r"\bcompliance", "compliance"), (r"company secretary", "secretarial"), (r"\blegal\b|\bcounsel", "legal"),
         (r"\brisk\b", "risk"), (r"\bunderwriting", "underwriting"),
         (r"\bcfo\b|chief financial|financial controller|finance controller|head of finance|chief accounting", "finance")]
ROUTINE = r"retir|superannuat|tenure|(?<!long.)\bterm\b"    # a departure the filing itself explains as the calendar's
EARLY = r"before|prior to|premature|disagree|differ"  # ... unless it says the tenure was cut short
DENIED = r"\b(?:no|not|nor|without|never)\b[^.;]{0,40}$"   # "no disagreement with the management" says the opposite
RELABEL = people.RELABEL                              # "Changed from SMP to Non-SMP category": nobody left a seat
INTERNAL = r"within the (?:company|group|organi[sz]ation)|redesignat"   # a move inside, in the filing's own words
# What only that seat sees, and nothing about the people who left: how the same seats are held where the contact sits.
SEATS_ASK = {"competitor": "How long does it usually take to fill {areas} seats in {trade}?",
             "former": "Who did {areas} report to at {company} in your time?"}
# One call, two answers: a clause for each kind of pin, in that notice's own words and nothing stronger.
CLAUSE = {"seat": "{company} new {seat}: {first} was {role} there.",
          "there_now": "{company} new {seat} lists {employer}, where {first} is {role}.",
          "was_there": "{company} new {seat} lists {employer}, where {first} was {role}.",
          "gap": "{company} new {seat} lists no {trade} employer; {first} holds the same seat at {employer}.",
          "seats": "{company}: {n} control seats were left {within}; {first} {is_was} {role} at {employer}{how}."}
SEATS_NEXT = "Who holds {areas} at {company} now, and who do they report to?"
INVESTS = {"private equity", "asset management", "family office"}
TAGS = {"seat": "Worked here", "inside": "You know", "there_now": "Works there now", "was_there": "Worked there", "gap": "Same seat, a competitor"}
# In a sentence, a station on the path says where: "now at the Dani family office", "used to work at IDFC Limited"
STATION = {"there_now": "now at {}", "was_there": "used to work at {}"}
CAPTION = "The path is the filing's, and it gives no years. The people are yours."
PINS = 4              # a path asks at most this many people
FLOOR = 0.08          # a route weaker than this is not shown at all
GOOD = 0.22           # a route weaker than this is never pushed; it is shown only when the investor asks
STOP = set("the and for with from head chief officer vice president senior general manager director business india "
           "limited company board approved received order year years financial quarter ended group".split())


def when(d):
    return f"{d:%b %Y}"


def first(p):
    return links.first(p)


def half_life(years_ago, half):
    return 0.5 ** (max(years_ago, 0) / half)


class Network:
    def __init__(self, filings, investor, registry=None, decisions=None, company_names=None, today=None):
        self.reg = registry or Registry()
        self.short = company_names or {}                 # ticker -> the name the app calls the company by
        self.companies, self.researched = dict(self.short), []
        self.asof = (today or dt.date.fromisoformat(investor["asof"])).isoformat()
        self.label = investor.get("label", "")
        self.today = today or dt.date.fromisoformat(investor["asof"])
        self.year = self.today.year
        self.me = people.contact(self.reg, investor["me"], investor["asof"], "me")
        self.contacts = [people.contact(self.reg, c, investor["asof"]) for c in investor["contacts"]]
        self.filings = {f["id"]: f for f in filings}
        self.filed = people.from_filings(self.reg, filings, company_names)
        # Is anyone in a filing someone the investor already knows?
        self.decisions = decisions or {}
        self.verdicts = {}
        self.asks, self.said = set(), set()          # the pairs the engine asks about, and those the investor has answered
        for p in self.filed:
            for c in self.contacts:
                v = identity.judge(p, c)
                if v:
                    key, said = f"{p.id}|{c.id}", self.decisions.get(f"{p.id}|{c.id}")
                    if v.status == "possible":
                        self.asks.add(key)
                        if said in ("same", "different"):     # only a question the engine asked can be answered
                            v = identity.Verdict(said, "You confirmed this." if said == "same" else "You said this is someone else.", v.ties)
                            self.said.add(key)
                    self.verdicts.setdefault(p.id, []).append((c, v))
        for p in self.filed:
            c = self.known(p)
            if c:
                self._merge(p, c)
        self.by_id = {p.id: p for p in [self.me, *self.contacts, *self.filed]}
        self._ties = {c.id: links.tie(c, self.today) for c in self.contacts}

    @classmethod
    def load(cls, root=ROOT, decisions=None, slim=None):
        d = pathlib.Path(root) / "data" / "network"
        read = lambda name: json.loads((d / name).read_text())
        slim = slim or read("filings.json")              # the pipeline passes the one it is about to write
        net = cls(slim["filings"], read("investor.json"), Registry(d / "registry.json"),
                  decisions, slim.get("companies"), dt.date.fromisoformat(slim["asof"][:10]))
        net.companies = slim.get("companies", {})        # the portfolio: ticker -> name
        net.researched = slim.get("researched", [])     # companies read beyond the portfolio, with a page of their own
        net.asof = slim["asof"]
        net.build = slim.get("build", "")                # the hash of network.json, written by the pipeline
        return net

    @staticmethod
    def _merge(p, c):
        """The filing person is a contact, so the two records are one life. The contact's dated career is
        the fuller one; the filing adds the newest step. If the contact was already inside the company
        the filing is a move, not an arrival. Both records then carry the merged career."""
        year, leaving = p.event["effective"].year, p.change == "leaves"
        inside = [s for s in c.career if s.org is p.company and s.current]
        earlier = [people.Stint(s.org, s.role, s.start, year if s in inside else s.end, s.current and s not in inside,
                                s.division, s.source) for s in c.career]
        news = [s for s in p.career if s.org is p.company and s.source == "filing" and (s.current or not inside)]
        p.career = c.career = earlier + ([] if leaving and inside else news)
        p.edu = c.edu or p.edu
        p.inside = bool(inside)
        c.asof = max(c.asof, p.asof)

    # -- small views --------------------------------------------------------------------------------
    def tie(self, c):
        return self._ties[c.id]

    def tie_label(self, c):
        t = self.tie(c)
        return "close" if t >= 0.7 else "warm" if t >= 0.45 else "cool"

    def contact_view(self, c):
        now = c.current or (c.career[-1] if c.career else None)
        m = links.months_since(c, self.today)
        return {"id": c.id, "name": c.name, "how": c.how,
                "now": f"{now.role}, {now.org.name}" if now and now.current else (f"formerly {now.role}, {now.org.name}" if now else ""),
                "tie": self.tie_label(c), "last": when(c.last_met()) if c.met else "", "months": m}

    def person_view(self, p):
        e = p.event
        return {"id": p.id, "name": p.name, "role": e["role"], "company": p.company.name, "symbol": p.symbol,
                "change": p.change, "seniority": p.seniority, "effective": e["effective"].isoformat(),
                "filing": e["filing"], "url": e["url"], "page": e["page"], "background": p.background}

    def known(self, p):
        """The contact this filing person is, when that is established."""
        return next((c for c, v in self.verdicts.get(p.id, []) if v.status == "same"), None)

    def identity_notes(self, p):
        out = []
        for c, v in self.verdicts.get(p.id, []):
            line = {"same": f"This is the {c.name} you know.", "possible": f"This may be the {c.name} you know.",
                    "different": f"Not the {c.name} you know."}[v.status]
            key = f"{p.id}|{c.id}"
            out.append({"status": v.status, "contact": self.contact_view(c), "line": line, "why": v.why, "key": key, "said": key in self.said})
        return out

    # -- second-degree reach ------------------------------------------------------------------------
    def reach(self, p, limit=4):
        """Who the investor knows who knows this person, strongest route first."""
        known = self.known(p)
        you, near = links.between(self.me, p, self.year)
        near = [f"You: {m}" for m in near]
        paths = []
        for c in self.contacts:
            if known:
                break                                   # the investor knows this person directly
            link, misses = links.between(c, p, self.year)
            near += [f"{c.name}: {m}" for m in misses if " at " in m]   # a contact's school years apart is no news
            if not link:
                continue
            strength = self.tie(c) * link.strength
            if strength < FLOOR:
                continue
            m = links.months_since(c, self.today)
            line = f"{first(c)} and {first(p)} {link.basis}."
            paths.append({"contact": self.contact_view(c), "kind": link.kind, "where": link.where, "strength": round(strength, 2),
                          "label": links.label(strength), "link": link.label, "dated": link.dated, "line": line,
                          "spoke": f"You last spoke to {first(c)} in {when(c.last_met())}." if m is not None else ""})
        paths.sort(key=lambda x: -x["strength"])
        return {"person": self.person_view(p), "identity": self.identity_notes(p),
                "you": {"line": f"You and {first(p)} {you.basis}.", "label": you.label, "kind": you.kind} if you else None,
                "paths": paths[:limit], "more": max(len(paths) - limit, 0), "near": near}

    # -- diligence on a person ----------------------------------------------------------------------
    def diligence(self, p):
        """Career path, overlaps with the network, and what is worth asking."""
        path = [{"org": s.org.name, "role": s.role, "years": s.years(), "now": s.current, "source": s.source}
                for s in p.career]
        edu = [{"school": e.name, "degree": e.degree, "years": e.years(), "source": e.source} for e in p.edu]
        out = self.reach(p)
        out.update({"path": path, "edu": edu, "education": p.education_text, "ask": self.questions(p), "prep": self.prep(p),
                    "sources": (f"The new role is from the company's filing. The earlier career is from your own record of {first(p)}." if self.known(p) else
                                "The role and earlier employers are from the brief profile the company filed with the appointment, in its order and with no years."
                                if p.listed or p.background else "The role is from the company's filing, which gives no years.")})
        return out

    def _roots(self, themes):
        out = set()
        for t in themes:
            while self.reg.themes[t]["in"]:
                t = self.reg.themes[t]["in"]
            out.add(t)
        return out

    def questions(self, p):
        """Things a careful investor would ask, each raised by a rule and shown with what raised it."""
        e, asks, co = p.event, [], p.company
        fn = roles.function(e["role"], co)
        past = [s for s in p.career if s.org is not co]
        joined = p.change == "joins" and e["action"] not in people.EXITS
        add = lambda ask, because, source="filing": asks.append({"ask": ask, "because": because, "source": source})
        if joined and e["seniority"] != "board" and fn not in ("legal", "hr", "it", "tax_audit", "other"):
            known = [s for s in past if s.org.known and s.org.themes]
            home = self._roots(co.themes)
            in_group = any(s.org.group and s.org.group == co.group for s in past)
            if known and home and not in_group and not any(self._roots(s.org.themes) & home for s in known):
                trade = sorted(home)[0] if len(home) == 1 else co.themes[0]
                came = ", ".join(f"{s.org.name} ({s.org.themes[0]})" for s in known[:3])
                add(ASK["gap_room"].format(employers=_list([s.org.name for s in known[:2]]), trade=trade),      # the filing's silence is not "never"
                    f"No {trade} employer in the filing's profile. It lists {came}.")
        for s in past:
            if re.search(r"\binterim\b|\bacting\b", s.role, re.I):
                add(ASK["interim"].format(employer=s.org.name), f"The filing gives the earlier role as \"{s.role}, {s.org.name}\".")
        if joined:
            # Gaps and short stays are read from years. A filing gives none, so these rest on the investor's own
            # record of someone they know.
            jobs = sorted((s.start, s.end or self.year, s.org.name) for s in past if s.start)
            for (a0, a1, an), (b0, b1, bn) in zip(jobs, jobs[1:]):
                studying = sum(min(x.end, b0) - max(x.start, a1) for x in p.edu if x.start and x.end and x.start < b0 and x.end > a1)
                if b0 - a1 - studying > 1 and self.year - b0 < 20:
                    add(f"What was {first(p)} doing between {a1} and {b0}?",
                        f"Nothing is listed between {an} (to {a1}) and {bn} (from {b0}).", "record")
            for s in past:
                if s.start and s.end and s.end - s.start < 2 and self.year - s.end < 12:
                    add(f"Why did {first(p)} leave {s.org.name} so soon?", f"{s.role}, {s.years()}.", "record")
        day_job = [s for s in p.career if s.current and s.org is not co and INVESTS & set(s.org.themes)]
        if self._day_job(p):                                 # the filing's own profile states it
            asks.append(self._day_job(p))
        elif e["seniority"] == "board" and joined and day_job:
            s = day_job[0]
            add(f"Does {s.org.name} hold, or deal with, anything connected to {co.name}?",
                f"{first(p)} joins as an independent director while {s.role} of {s.org.name}, an investment firm.", "record")
        if joined:
            asks.extend(self._predecessor(p))
        exits = self.exits(p.symbol)
        if len(exits) >= 3 and (p in exits or (joined and e["seniority"] in ("top", "senior"))):
            add(f"Why are so many senior people leaving {co.name} at once?",
                f"{len(exits)} senior exits filed within {(max(q.event['effective'] for q in exits) - min(q.event['effective'] for q in exits)).days + 1} days: "
                + ", ".join(f"{q.name} ({q.event['role']})" for q in exits) + ".")
            asks[-1]["about"] = "company"            # for someone who has worked there, not for the person in the filing
        return asks

    def _day_job(self, p):
        """A new director whose filing opens with a seat at an investment firm: does that firm touch this company?
        Read from the filing alone. For the person, in the room."""
        e, co = p.event, p.company
        if not p.holds or e["seniority"] != "board" or p.change != "joins" or not INVESTS & set(p.holds[0].themes):
            return None
        o, r = p.holds
        return {"ask": ASK["holds"].format(employer=o.name, company=self.short.get(p.symbol, co.name)),
                "because": f"The filing gives {first(p)} as {r} of {o.name}, an investment firm.", "source": "filing"}

    def _predecessor(self, p):
        """Whose chair is this? Someone who gave up a role of the same kind and rank, within 60 days. Filings only."""
        e, co = p.event, p.company
        if e["seniority"] == "board":
            return []
        fn = roles.function(e["role"], co)
        for q in self.filed:
            gave_up = [x for x in q.events if x["action"] in people.EXITS and not people.relabel(x) and abs((x["effective"] - e["effective"]).days) <= 60
                       and roles.function(x["role"], co) == fn and roles.level(x["role"]) == roles.level(e["role"])]
            if q.symbol == p.symbol and q is not p and gave_up:
                x = gave_up[0]
                reason = x["reason"] if x["reason"] and x["reason"].lower() != "not stated" else ""
                return [{"ask": f"What is {first(p)} expected to do differently from {q.name}?",
                         "because": f"{q.name} {x['action']} as {x['role']} with effect from {x['effective']:%-d %b %Y}" +
                                    (f". Reason given: {reason[0].lower() + reason[1:].rstrip('.')}." if reason else "; the filing gives no reason."),
                         "source": "filing"}]
        return []

    # -- before a meeting: the path, and the investor's own people on it ------------------------------
    def _held(self, org):
        """Contacts who work or worked at this organisation, best placed first: (score, contact, stint, now)."""
        out = []
        for c in self.contacts:
            a = next((a for a in self._angles(c, org) if a[1] in ("inside", "former") and a[3].org is org), None)
            if a:
                out.append((a[0] * (0.5 + 0.5 * self.tie(c)), c, a[3], a[1] == "inside"))
        return sorted(out, key=lambda x: (-x[0], x[1].id))

    def _gap(self, p):
        """The trade the company is in, when no employer the filing lists is in it. None when the rule doesn't hold."""
        e, co = p.event, p.company
        fn = roles.function(e["role"], co)
        if p.change != "joins" or e["seniority"] == "board" or fn in ("legal", "hr", "it", "tax_audit", "other"):
            return None
        known = [o for o, _ in p.listed if o is not co and o.known and o.themes]
        home = self._roots(co.themes)
        if not known or not home or any(o.group and o.group == co.group for o in known) or any(self._roots(o.themes) & home for o in known):
            return None
        return co.themes[0]

    def prep(self, p, least=2):
        """Before a meeting: the person's path as the filing lists it, and at each station the one contact who
        can answer one question about it. Reads the filing and the investor's own records only, and never claims
        that two people overlapped. None for someone leaving, someone the investor knows,
        or a path with fewer than two people to ask: one person is a row, not a path."""
        if p.change == "leaves" or self.known(p):
            return None
        e, co, me = p.event, p.company, first(p)
        full = names.clean(p.name)              # said in full the first time: the contact may never have met them
        here = self.short.get(p.symbol, co.name)
        fn, seat = roles.function(e["role"], co), _seat(e["role"])
        used, stations = set(), []

        def pin(kind, c, s, basis, ask, caution=""):
            used.add(c.id)
            return {"contact": self.contact_view(c), "kind": kind, "tag": TAGS[kind], "basis": basis, "ask": ask, "caution": caution,
                    "role": s.role, "org": s.org.name, "now": s.current}

        desk = lambda c: self._inside(c, co)                # someone inside the company now is never asked, at any station

        # The new seat: someone who held a seat there and has left. Someone still inside is named, never asked.
        held = self._held(co)
        was = next((x for x in held if not x[3] and not desk(x[1]) and not (x[2].end and self.year - x[2].end < 1)), None)
        now = next((x for x in held if x[3]), None)
        filed = dt.date.fromisoformat(e["at"][:10])
        top = {"kind": "seat", "org": co.name, "role": e["role"],
               "when": f"from {e['effective']:%-d %b}" if e.get("stated") else f"filed {filed:%-d %b}", "pin": None}
        if was:
            _, c, s, _ = was
            theirs = s.function
            if e["seniority"] == "board" or fn == "board":
                ask = ASK["seat_board"].format(role=seat, company=here)
            elif fn in LINE and theirs in LINE and fn != theirs:
                ask = ASK["seat_across"].format(theirs=LINE[theirs], seat=LINE[fn], company=here)
            elif fn in LINE and theirs == fn:
                ask = ASK["seat_same"].format(seat=LINE[fn], company=here)
            else:
                ask = ASK["seat_other"].format(role=seat, company=here)
            top["pin"] = pin("seat", c, s, _basis(s), ask)
        elif now:
            _, c, s, _ = now
            top["pin"] = pin("inside", c, s, f"{s.role} there now", "", "Works there now. Keep the conversation to what is public.")
        stations.append(top)

        # Each employer the filing lists, in the filing's order: first someone there now, then someone who was.
        # A seat elsewhere that the filing says the person holds comes first, and its one question is the firm's, not the person's.
        listed = [(o, r) for o, r in p.listed if o is not co]
        holds = p.holds if p.holds and not any(o is p.holds[0] for o, _ in listed) else None
        firm = self._day_job(p)
        rows = [{"kind": "listed", "org": o.name, "role": r, "when": "", "pin": None} for o, r in listed]
        if holds:
            listed.insert(0, holds)
            rows.insert(0, {"kind": "listed", "org": holds[0].name, "role": holds[1], "when": "now", "pin": None})
        for want_now in (True, False):
            for (o, r), row in zip(listed, rows):
                if row["pin"] or not o.known:
                    continue
                x = next((x for x in self._held(o) if x[3] == want_now and x[1].id not in used and not desk(x[1])), None)
                if not x:
                    continue
                _, c, s, _ = x
                their, its = s.function, roles.function(r, o) if r else None
                if holds and o is holds[0]:
                    if firm:                                # someone there now can answer for today; someone who left, for their time
                        row["pin"] = pin("there_now" if want_now else "was_there", c, s, s.role if want_now else _basis(s),
                                         ASK["holds" if want_now else "held"].format(employer=o.name, company=here))
                        firm = None if want_now else firm
                elif want_now:
                    row["pin"] = pin("there_now", c, s, s.role, ASK["there_now"].format(name=full, employer=_the(o.name)))
                elif its in LINE and their in LINE and its != their:
                    row["pin"] = pin("was_there", c, s, _basis(s), ASK["was_across"].format(name=full, theirs=LINE[their], role=_seat(r), employer=_the(o.name)))
                else:
                    row["pin"] = pin("was_there", c, s, _basis(s), ASK["was_there"].format(name=full, first=me, employer=_the(o.name)))
        stations += rows

        # The gap: no listed employer in the company's own trade. Someone in the same seat at a competitor knows what that costs.
        room = []
        trade = self._gap(p)
        if trade:
            best = None
            for c in self.contacts:
                if c.id in used or desk(c):
                    continue
                a = next((a for a in self._angles(c, co, (fn,)) if a[1] == "competitor" and a[3].function == fn and a[3].current
                          and a[3].level == roles.level(e["role"])), None)     # the same seat: the line of work and the rank
                if a and (best is None or a[0] * (0.5 + 0.5 * self.tie(c)) > best[0]):
                    best = (a[0] * (0.5 + 0.5 * self.tie(c)), c, a[3])
            row = {"kind": "gap", "org": "", "role": "", "when": "", "line": f"No {trade} employer in the filing", "pin": None}
            if best:
                _, c, s = best
                row["pin"] = pin("gap", c, s, f"{s.role}, {s.org.name}", ASK["gap"].format(role=seat, trade=trade))
                stations.append(row)
            else:
                room.append({"ask": ASK["gap_room"].format(employers=_list([o.name for o, _ in listed][:2]), trade=trade),
                             "because": "No " + trade + " employer in the filing. It lists " + _list([o.name for o, _ in listed][:3]) + ".", "source": "filing"})

        # At most four people are asked; the last-listed employers give way first.
        asked = [r for r in stations if r["pin"] and r["pin"]["ask"]]
        for r in [r for r in reversed(stations) if r["kind"] == "listed" and r["pin"] and r["pin"]["ask"]][:max(len(asked) - PINS, 0)]:
            r["pin"] = None
        # In the room: what the filing raises about the person is for the person.
        for o, r in listed:
            if re.search(r"\binterim\b|\bacting\b", r, re.I):
                room.append({"ask": ASK["interim"].format(employer=o.name), "because": f"The filing gives the earlier role as \"{r}, {o.name}\".", "source": "filing"})
        room += [firm] if firm else []
        room += self._predecessor(p) if p.change == "joins" else []
        asked = [r["pin"] for r in stations if r["pin"] and r["pin"]["ask"]]
        on_path = sum(1 for r in stations if r["kind"] != "gap" and r["pin"] and r["pin"]["ask"])
        if len(asked) < least:
            return None
        # The investor's own record against the filing: an opener for the room, never a claim that they overlapped
        you, _ = links.between(self.me, p, self.year)
        mine = f"You and {me} {you.basis}." if you else ""
        sheet = [f"Before you meet {p.name}, {e['role']}, {co.name}", ""]
        for r in stations:
            x = r["pin"]
            if x and x["ask"]:
                at = STATION[x["kind"]].format(_the(r["org"])) if r["kind"] == "listed" and x["kind"] in STATION else x["tag"] + (f", {r['org']}" if r["kind"] == "listed" else "")
                sheet += [f"{x['contact']['name']} ({at[0].upper() + at[1:]}: {x['basis']})", x["ask"], ""]
        if room or mine:
            sheet += ["In the room", *([mine] if mine else []), *[a["ask"] for a in room], ""]
        return {"person": {"id": p.id, "name": p.name, "role": e["role"], "company": co.name, "symbol": p.symbol},
                "q": f"Brief me on {p.name} at {co.name}", "caption": CAPTION, "stations": stations, "room": room, "you": mine, "pins": len(asked), "on_path": on_path,
                "line": f"{_people(on_path)} have worked where {p.name} works or has worked." if on_path >= 2 else "",
                "sheet": "\n".join(sheet).strip()}

    # -- patterns across filings: each too small to show alone ----------------------------------------
    def patterns(self, symbol, days=30):
        """What two or more of a company's filings say together. One rule so far, control seats: two or more
        different people leave seats in audit, risk, compliance, legal, the company secretary's office or finance,
        with effective dates `days` apart or less, in separate filings. A departure the filing gives as retirement,
        superannuation or a completed tenure is the calendar's and does not count. The line holds only the company,
        filed titles, a count and a span of days; the evidence only names, titles, dates and the filed reasons."""
        symbol = symbol.upper()
        org = self.reg.by_symbol.get(symbol)
        reason = lambda q: (q.event["reason"] or "").strip()
        early = lambda q: any(not re.search(DENIED, reason(q)[:m.start()], re.I) for m in re.finditer(EARLY, reason(q), re.I))
        routine = lambda q: (q.event["action"] == "retired" or re.search(ROUTINE, reason(q), re.I)) and not early(q)
        relabelled = lambda q: re.search(RELABEL, reason(q), re.I)     # still in the job; only the designation changed
        died = lambda q: q.event["action"] == "died" or re.search(r"\bdemise\b|\bdeath\b|passed away", reason(q), re.I)
        left = sorted([q for q in self.filed if q.symbol == symbol and q.change == "leaves" and q.seniority != "board"
                       and _area(q.event["role"]) and not routine(q) and not died(q) and not relabelled(q)], key=lambda q: (q.event["effective"], q.id))
        ids = lambda q: {x for e in q.events for x in [e["filing"], *e.get("also", [])]}
        # the latest window of `days` that holds two or more departures, each in a filing of its own
        run = []
        for q in left:
            win = []
            for x in left:
                if 0 <= (q.event["effective"] - x.event["effective"]).days <= days and not any(ids(x) & ids(y) for y in win):
                    win.append(x)
            if len(win) >= 2:
                run = win
        if org is None or len(run) < 2:
            return []
        span = (run[-1].event["effective"] - run[0].event["effective"]).days + 1
        areas = _list(list(dict.fromkeys(_area(q.event["role"]) for q in run)))
        here = self.short.get(symbol, org.name)
        within = "on the same day" if span == 1 else f"within {_count(span).lower()} days"
        # what each filing says happened, in its own terms: a move inside the company is said as one
        did = lambda q: "resigned" if q.event["action"] == "resigned" else \
            "moved to another role in the company" if re.search(INTERNAL, reason(q), re.I) else "left the seat"
        line = f"{here}: {within}, " + _list([f"the {_title(q.event['role'])} {did(q)}" for q in run]) + "."
        on = lambda q: f"on {q.event['effective']:%-d %b}" if q.event.get("stated") else f"(filed {dt.date.fromisoformat(q.event['at'][:10]):%-d %b})"
        why = [f"{q.name}, {q.event['role']}, {q.event['action']} {on(q)}. " +
               (f"Reason filed: {reason(q).rstrip('.')}." if reason(q) and reason(q).lower() != "not stated" else "The filing gives no reason.")
               for q in run]
        took = lambda q: any(p.symbol == symbol and p is not q and p.change != "leaves" and _areas(p.event["role"]) & _areas(q.event["role"]) for p in self.filed)
        if not any(took(q) for q in run):
            why.append(f"No successor is filed for {'either' if len(run) == 2 else 'any of them'}.")
        folded = [q for q in run if all(self.filings.get(x, {}).get("tier") == "fold" for x in ids(q))]
        if folded and len(folded) < len(run):
            why.append("Read alone, " + _list([f"the {_title(q.event['role'])}'s" for q in folded]) + " filing was folded as routine.")
        # Who to ask: someone whose own work is one of these seats, at a competitor or once inside. Never anyone with a desk there now.
        pin = None
        for r in self.who_to_call(org, CONTROL, limit=99):
            c = self.by_id[r["contact"]["id"]]
            if r["fn"] not in CONTROL or r["relation"] not in SEATS_ASK or r["caution"] or self._inside(c, org):
                continue
            _, _, trade, st = next(a for a in self._angles(c, org, CONTROL) if a[1] == r["relation"])
            if r["relation"] == "competitor" and not st.current:
                continue                                    # the question is about where the contact sits today
            pin = {"contact": r["contact"], "relation": r["relation"], "role": st.role, "org": st.org.name, "now": st.current,
                   "basis": f"{st.role}, {st.org.name}" + (", a competitor" if r["relation"] == "competitor" else f", {st.years()}" if st.years() else ""),
                   "ask": SEATS_ASK[r["relation"]].format(company=here, employer=st.org.name, areas=areas, trade=trade)}
            break
        return [{"kind": "seats", "symbol": symbol, "line": line, "why": " ".join(why), "pin": pin, "span": span,
                 "none": "" if pin else "Nobody you know has held one of these seats there or at a competitor.",
                 "next": SEATS_NEXT.format(areas=areas, company=here), "at": run[-1].event["effective"].isoformat(),
                 "people": [q.id for q in run], "filings": sorted(set().union(*[ids(q) for q in run])), "filing": run[-1].event["filing"]}]

    def fit(self, symbol):
        """Who fits a question about the company, by its kind: one choice, used by the card, Who to ask and the end band.
        leave: a CEO, CFO or MD has left; someone who worked inside and left over a year ago, asked the seat question
        from where they sat. numbers: a question about results, margins or guidance; someone at a competitor or a customer
        today, asked about their own seat. Nobody who has left is on a numbers row; nobody inside is asked. None: silence."""
        symbol = symbol.upper()
        org = self.reg.by_symbol.get(symbol)
        if org is None:
            return {"leave": None, "numbers": None}
        here = self.short.get(symbol, org.name)
        leave = None
        gone = sorted((q for q in self.filed if q.symbol == symbol and q.change == "leaves" and q.seniority == "top"),
                      key=lambda q: (q.event["effective"], q.id))
        if gone:
            fn, seat = roles.function(gone[-1].event["role"], org), _seat(gone[-1].event["role"])
            x = next((x for x in self._held(org) if not x[3] and not self._inside(x[1], org) and not (x[2].end and self.year - x[2].end < 1)), None)
            if x:
                _, c, st, _ = x
                theirs = st.function
                ask = (ASK["seat_across"].format(theirs=LINE[theirs], seat=LINE[fn], company=here) if fn in LINE and theirs in LINE and fn != theirs
                       else ASK["seat_same"].format(seat=LINE[fn], company=here) if fn in LINE and theirs == fn
                       else ASK["seat_other"].format(role=seat, company=here))
                leave = {"contact": self.contact_view(c), "relation": "former", "basis": f"{st.role} there" + (f", {st.years()}" if st.years() else ""),
                         "ask": ask, "person": gone[-1].id}
        best = None
        for c in self.contacts:
            if self._inside(c, org):
                continue
            a = next((a for a in self._angles(c, org, FOCUS["results"]) if a[1] in NUMBERS and a[3].current and a[3].function in NUMBERS[a[1]]), None)
            if a and a[0] >= 0.12 and (best is None or a[0] * (0.5 + 0.5 * self.tie(c)) > best[0]):
                best = (a[0] * (0.5 + 0.5 * self.tie(c)), c, a)
        numbers = None
        if best:
            _, c, (_, kind, detail, st) = best
            f = dict(trade=detail, employer=st.org.name, company=org.name, thing=detail)
            ask = ASK["market" if kind == "competitor" else "supplier"].format(**f)
            on = {"margin": ASK["costs" if kind == "competitor" else "charges"].format(**f), "profit": ASK["oneoff"].format(**f) if kind == "competitor" else ask,
                  "credit": ASK["credit"].format(**f) if kind == "competitor" else ask}
            numbers = {"contact": self.contact_view(c), "relation": kind, "basis": f"{st.role}, {st.org.name}, a {kind}", "ask": ask, "on": on}
        return {"leave": leave, "numbers": numbers}

    def _inside(self, c, org):
        """True when this contact has a desk at the organisation today, whatever else their career holds."""
        return any(s.current and s.org is org for s in c.career)

    # -- one call, two answers: the join of a person with several of the month's questions ------------
    def answers(self, days=30):
        """Every open question of the window that is pinned on a contact: the pins of each path that shows, each
        pattern's pin, and each material event's person to ask. contact id -> [(symbol, clause, date, inside now)]."""
        since, out = self.today - dt.timedelta(days=days), {}
        put = lambda c_id, sym, clause, at, inside=False, what="": out.setdefault(c_id, []).append((sym, clause, at, inside, what))
        for p in self.filed:
            at, d = dt.date.fromisoformat(p.event["at"][:10]), None
            if at >= since:
                d = self.prep(p)
            for r in (d or {}).get("stations", []):
                x = r["pin"]
                if not x or not x["ask"]:
                    continue
                c = self.by_id[x["contact"]["id"]]
                put(c.id, p.symbol, CLAUSE[x["kind"]].format(company=_s(self.short.get(p.symbol, p.company.name)), seat=_seat(p.event["role"]), first=first(c),
                                                           role=x["role"], employer=_the(x["org"]), trade=p.company.themes[0] if p.company.themes else "")
                    + f" Ask: {x['ask']}", at, False, f"a new {_seat(p.event['role'])} at {self.short.get(p.symbol, p.company.name)}")
        for sym in dict.fromkeys(p.symbol for p in self.filed):
            for pat in self.patterns(sym):
                x, at = pat["pin"], dt.date.fromisoformat(pat["at"])
                if x and at >= since:
                    c = self.by_id[x["contact"]["id"]]
                    put(c.id, sym, CLAUSE["seats"].format(company=self.short.get(sym, sym), n=_count(len(pat["people"])).lower(),
                                                          within="on the same day" if pat["span"] == 1 else f"within {_count(pat['span']).lower()} days",
                                                          first=first(c), is_was="is" if x["now"] else "was", role=x["role"], employer=_the(x["org"]),
                                                          how=", a competitor" if x["relation"] == "competitor" else "") + f" Ask: {x['ask']}", at,
                        False, f"control seats left at {self.short.get(sym, sym)}")
        seen = set()
        for f in sorted(self.filings.values(), key=lambda f: f["at"], reverse=True):
            at = dt.date.fromisoformat(f["at"][:10])
            if at < since or f["category"] == "results":
                continue
            for r in self.for_event(f, limit=1):
                if (f["symbol"], f["category"], r["contact"]["id"]) not in seen:
                    seen.add((f["symbol"], f["category"], r["contact"]["id"]))
                    put(r["contact"]["id"], f["symbol"], f"{self.reg.by_symbol[f['symbol']].name}: {f['line'].rstrip('.')}. {first(self.by_id[r['contact']['id']])} is the person to ask.",
                        at, r["relation"] == "inside", f"{EVENT_WORD[f['category']]} at {self.short.get(f['symbol'], f['symbol'])}")
        return out

    def one_call(self, days=30):
        """The contact who is the answer at two or more different companies this window, and inside none of them now.
        One a day: the most companies, then the closest tie. The rule is not tuned towards a name."""
        found = []
        for c_id, rows in self.answers(days).items():
            c, by_co = self.by_id[c_id], {}
            for sym, clause, at, inside, *what in rows:
                by_co.setdefault(sym, (clause, at, inside, what[0] if what else ""))   # one answer a company: the first raised
            orgs = [self.reg.by_symbol.get(sym) for sym in by_co]
            if len(by_co) < 2 or any(x[2] for x in by_co.values()) or any(s.current and s.org in orgs for s in c.career):
                continue
            found.append((-len(by_co), -self.tie(c), c.id, c, by_co))
        if not found:
            return None
        _, _, _, c, by_co = min(found, key=lambda x: x[:3])
        n = len(by_co)
        by_co = dict(sorted(by_co.items(), key=lambda kv: kv[1][1], reverse=True))      # the freshest company first
        spoke = f" You last spoke in {when(c.last_met())}." if c.met else ""
        # For the card's full view and its call sheet: each company's clause and its one question, apart
        rows = [{"symbol": sym, "line": x[0].partition(" Ask: ")[0], "ask": x[0].partition(" Ask: ")[2], "at": x[1].isoformat()} for sym, x in by_co.items()]
        now = c.current
        who = f"{c.name}, {_seat(now.role)} at {now.org.name}" if now else c.name
        sheet = [f"One call: {who}", ""] + [t for r in rows for t in (r["line"], r["ask"], "")] + ([spoke.strip()] if spoke else [])
        happened = [x[3] for x in by_co.values() if x[3]]
        card = (_list(happened)[:1].upper() + _list(happened)[1:] + f": one call to {who}{',' if ',' in who else ''} has a question for each." if len(happened) == len(by_co)
                else f"One call answers a question at each: {who}.")
        return {"contact": self.contact_view(c), "line": f"One call, {_count(n).lower()} answers: {c.name}.",
                "why": " ".join(x[0] for x in by_co.values()) + spoke, "companies": list(by_co),
                "at": max(x[1] for x in by_co.values()).isoformat(), "also": sorted(x[3].name for x in found if x[3] is not c),
                "rows": rows, "sheet": "\n".join(sheet).strip(), "who": who, "card": card}

    def exits(self, symbol, days=45):
        """Senior people who left this company inside one window."""
        gone = sorted([q for q in self.filed if q.symbol == symbol and q.change == "leaves" and q.seniority in ("top", "senior")],
                      key=lambda q: q.event["effective"])
        return gone if gone and (gone[-1].event["effective"] - gone[0].event["effective"]).days <= days else []

    # -- who should I call about a company ----------------------------------------------------------
    def _angles(self, c, org, focus=(), words=()):
        """Every way this contact's career bears on the organisation, best first."""
        out = []
        for s in c.career:
            kind, detail = self.reg.relation(s.org, org)
            watched = [t for t in self.reg.themes_in(f"{s.role} {s.division}") if any(self.reg.within(t, o) for o in org.themes)]
            if kind == "same":
                here = [x for x in c.career if x.org is s.org]
                if not s.current and any(x.current for x in here):
                    continue                    # an earlier role at a company they are still at: counted with the current one
                kind = "inside" if s.current else "former"
                first_year = min((x.start for x in here if x.start), default=None)
            elif kind is None and watched and s.org is not org:
                kind, detail = "watcher", watched[0]
            elif kind is None and self._roots(s.org.themes) & self._roots(org.themes):
                kind, detail = "sector", sorted(self._roots(s.org.themes) & self._roots(org.themes))[0]
            if kind is None or s.function == "board" and kind not in ("inside", "former"):
                continue
            fn = s.function
            w = roles.WEIGHT[fn]
            if kind in ("customer", "supplier"):
                w = 1.0 if fn in ("purchasing", "sales", "operations", "general") else 0.6
                if _shares_word(s.role, detail):
                    w *= 1.25
            if focus:
                w = 1.15 if fn in focus else w * 0.7
            if words and _shares_word(s.role + " " + s.division, " ".join(words)):
                w *= 1.3
            ago = 0 if s.current else self.year - (s.end or self.year - 6)
            start = first_year if kind == "inside" else s.start
            tenure = min(1.0, 0.5 + ((self.year if s.current else s.end) - start) / 10) if start else 0.7
            rel = RELATION_W[kind] * LEVEL_W[s.level] * w * half_life(ago, 8) * tenure
            out.append((rel, kind, detail, s))
        return sorted(out, key=lambda a: -a[0])

    def who_to_call(self, org, focus=(), words=(), limit=5, floor=0.12):
        """Contacts who can speak to this organisation: worked there, at a competitor, a supplier or a customer.
        Ranked by what they would know first and how easy they are to reach second."""
        rows = []
        for c in self.contacts:
            angles = self._angles(c, org, focus, words)
            if not angles:
                continue
            top = angles[0]
            # Time inside the company outranks an outside view of similar weight.
            ins = next((a for a in angles if a[1] in ("inside", "former")), None)
            if ins and ins[0] >= 0.6 * top[0]:
                top = ins
            other = next((a for a in angles if a[3].org is not top[3].org and a[1] in ALSO and a[0] >= 0.12), None)
            rel = links.either(max(top[0], angles[0][0]), 0.5 * other[0]) if other else top[0]
            if rel < floor:
                continue
            _, kind, detail, s = top
            knows = roles.KNOWS[s.function]
            job = f"{s.role} at {s.org.name}" + (f", {s.years()}" if s.years() else "")
            if kind == "inside":
                line = f"{s.role} there now. Knows {knows}."
            elif kind == "former":
                line = f"{s.role} there, {s.years()}. Knows {knows}."
            elif kind == "customer":
                line = f"{job}, which buys {detail} from {org.name}. Knows how {org.name} is rated as a supplier and what it is paid."
            elif kind == "supplier":
                line = f"{job}, which sells {detail} to {org.name}. Knows how {org.name} buys and how it pays."
            elif kind == "competitor":
                line = f"{job}, a competitor in {detail}. Knows {knows}, and how {org.name} looks from across the market."
            elif kind == "watcher":
                line = f"{job}. The role covers {detail}. Knows {knows}."
            elif kind == "group":
                line = f"{job}, in the same group as {org.name}. Knows how the group moves capital and people."
            else:
                line = f"{job}, in {detail}. Knows the wider sector rather than {org.name} itself."
            if other:
                o = other[3]
                line += f" Also {o.role} at {o.org.name}" + (f", {o.years()}" if o.years() else "") + ALSO[other[1]].format(org=org.name) + "."
            caution = ""
            if kind == "inside":
                caution = "Works there now. Keep the conversation to what is public."
            elif kind == "former" and s.end and self.year - s.end < 1:
                caution = "Left within the last year and may still hold unpublished information."
            rows.append({"contact": self.contact_view(c), "relation": kind, "line": line, "caution": caution, "fn": s.function,
                         "relevance": round(rel, 2), "score": round(rel * (0.5 + 0.5 * self.tie(c)), 3)})
        rows.sort(key=lambda r: -r["score"])
        return rows[:limit]

    # -- expertise map ------------------------------------------------------------------------------
    def expertise(self, theme, limit=6):
        """The investor's go-to people for a theme, by depth of experience first, ease of reaching second."""
        rows = []
        for c in self.contacts:
            pts, orgs, watched, yrs_total, now = 0.0, [], False, 0, None
            for s in c.career:
                own = [t for t in self.reg.stint_themes(s.org, s.role, s.division) if self.reg.within(t, theme)]
                named = [t for t in self.reg.themes_in(f"{s.role} {s.division}") if self.reg.within(t, theme)]
                if not own and not named:
                    continue
                yrs = ((self.year if s.current else s.end) - s.start) if s.start else 3
                ago = 0 if s.current else self.year - (s.end or self.year - 6)
                pts += min(yrs, 12) * LEVEL_W[s.level] * roles.WEIGHT[s.function] * half_life(ago, 8) * (1.0 if own else 0.8)
                yrs_total += yrs
                watched = watched or not own
                if s.org.name not in orgs:
                    orgs.append(s.org.name)
                if s.current:
                    now = s
            if pts <= 0:
                continue
            depth = 1 - math.exp(-pts / 5)
            if depth < 0.15:
                continue
            last = now or [s for s in c.career if s.org.name in orgs][-1]
            line = f"{yrs_total} years " + ("covering" if watched and len(orgs) == 1 else "in") + f" {theme} at {_list(orgs)}. "
            line += f"{last.role} at {last.org.name} now." if now else f"Last there as {last.role}, {last.org.name}, until {last.end}."
            rows.append({"contact": self.contact_view(c), "depth": round(depth, 2), "years": yrs_total, "orgs": orgs,
                         "current": bool(now), "line": line, "score": round(depth * (0.5 + 0.5 * self.tie(c)), 3)})
        rows.sort(key=lambda r: -r["score"])
        return rows[:limit]

    # -- push: what a filing means for the network --------------------------------------------------
    def for_event(self, f, limit=2):
        """For a material filing, the people best placed to give context. Empty unless someone clears a real bar:
        time inside the company, or an outside seat that bears on this kind of event."""
        org = self.reg.by_symbol.get(f["symbol"])
        cat = f["category"]
        if org is None or cat not in MATERIAL or f.get("downgraded") or f["tier"] == "fold":
            return []
        words = [w for w in re.findall(r"[a-z]{3,}", f.get("line", "").lower()) if w not in STOP]
        ok = {"inside", "former"} | OUTSIDE.get(cat, set())
        rows = self.who_to_call(org, FOCUS.get(cat, ()), words, limit=9, floor=0.5 if cat == "results" else 0.3)
        return [r for r in rows if r["relation"] in ok and r["fn"] in FOCUS[cat]][:limit]

    def for_filing(self, f):
        """The Network's part of one Push card, or None when it has nothing worth the space."""
        block = {}
        mine = [p for p in self.filed if any(e["filing"] == f["id"] or f["id"] in e.get("also", []) for e in p.events)]
        ppl = []
        for p in mine:
            r = self.reach(p, limit=9)
            asks = self.questions(p)
            paths = [x for x in r["paths"] if x["strength"] >= GOOD]
            d = self.prep(p)                                  # a path qualifies a person on its own
            if r["identity"] or paths or r["you"] or asks or d:
                ppl.append({"person": r["person"], "identity": r["identity"], "you": r["you"], "paths": paths[:2],
                            "weaker": len(r["paths"]) - len(paths[:2]), "ask": asks[:2], "prep": d})
        if ppl:
            block["people"] = ppl
        call = self.for_event(f)
        if call:
            block["call"] = call
        return block or None

    # -- keeping the network warm -------------------------------------------------------------------
    def warm(self, quiet_months=9, window_days=30, limit=8):
        """Contacts the investor hasn't spoken to in a while, each with a fresh, real reason to call."""
        rows = []
        since = self.today - dt.timedelta(days=window_days)
        for c in self.contacts:
            m = links.months_since(c, self.today)
            if m is None or m < quiet_months:
                continue
            best = None
            for p in self.filed:                                    # the contact is in a filing themself
                if self.known(p) is c and p.event["effective"] >= since:
                    e = p.event
                    verb = {"joins": "has joined", "moves": "has a new role at", "leaves": "has left"}[p.change]
                    best = (3.0, f"{first(c)} {verb} {p.company.name}" + (f" as {e['role']}" if p.change != "leaves" else "") + f" ({e['effective']:%-d %b}).", e["filing"], p.symbol, e["effective"])
            for f in self.filings.values():
                if best and best[0] >= 3 or f["category"] not in MATERIAL or f["tier"] == "fold" or f.get("downgraded"):
                    continue
                said = _results(f)
                if f["category"] == "results" and not said:
                    continue            # a cover letter without figures: the filing that carries them is the reason
                at = dt.date.fromisoformat(f["at"][:10])
                org = self.reg.by_symbol.get(f["symbol"])
                if at < since or org is None:
                    continue
                for s in c.career:
                    if s.org is not org:
                        continue
                    # The occasion must fit the person: a tax order is no reason to call a purchasing head
                    if s.function not in FOCUS.get(f["category"], ()) and not _shares_word(f"{s.role} {s.division}", f.get("line", "")):
                        continue
                    ago = 0 if s.current else self.year - (s.end or self.year - 6)
                    weight = (1.5 if f["tier"] == "act" else 1.0) * (1.2 if f["category"] != "results" else 1.0) * LEVEL_W[s.level] \
                        * (1.6 if s.function in FOCUS.get(f["category"], ()) else 1.0) * half_life(ago, 8) + (at - since).days / 1000
                    where = f"{first(c)} is {s.role} there" if s.current else f"{first(c)} was {s.role} there until {s.end}"
                    if said:                # results are a reason to call when they say something: the exchange's figures
                        reason = f"{org.name} reported {f['results']['quarter'].split()[0]} on {at:%-d %b}: {said} on a year ago. {where}."
                    else:
                        what = f.get("line") or f"{org.name} reported {EVENT_WORD[f['category']]}."
                        reason = f"{org.name}, {at:%-d %b}: {what.rstrip('.')}. {where}."
                    if best is None or weight > best[0]:
                        best = (weight, reason, f["id"], f["symbol"], at)
            if best:
                quiet = f"{m // 12} year{'s' if m >= 24 else ''}" if m >= 12 else f"{m} months"
                rows.append({"contact": self.contact_view(c), "quiet": quiet, "reason": best[1], "filing": best[2], "symbol": best[3], "at": best[4].isoformat(),
                             "score": round(best[0] * links.HOW.get(c.how, 0.4) * min(m, 48) / 24, 2)})
        rows.sort(key=lambda r: -r["score"])
        return rows[:limit]

    def only_one(self, symbols, quiet_months=9, days=30):
        """The quiet contact who is the single person in the network to have worked inside a holding, when there is
        a reason to call now. One a day: the longest silence that has a reason. The reason is a new arrival whose
        path already asks this contact about the company (then it is said on that path, once), or else a filing
        that fits what the contact did there, with one question about it. No reason, no notice."""
        found = []
        for sym in symbols:
            org = self.reg.by_symbol.get(sym)
            held = self._held(org) if org else []
            if len(held) != 1:
                continue
            _, c, s, now = held[0]
            m = links.months_since(c, self.today)
            if m is not None and m >= quiet_months:
                found.append((-m, sym, c, s, org))
        since = self.today - dt.timedelta(days=days)
        for _, sym, c, s, org in sorted(found, key=lambda x: (x[0], x[1])):
            here = self.short.get(sym, org.name)
            out = {"contact": self.contact_view(c), "symbol": sym, "company": org.name, "others": len(found) - 1, "person": "", "ask": "", "filing": "",
                   "line": f"{c.name} is the only person you know who has worked inside {here}."}
            spoke = f"You last spoke in {when(c.last_met())}."
            # a new arrival there whose path asks this contact about the seat: the path says it
            for p in self.filed:
                if p.symbol != sym or dt.date.fromisoformat(p.event["at"][:10]) < since:
                    continue
                d = self.prep(p)
                x = d and d["stations"][0]["pin"]
                if x and x["ask"] and x["contact"]["id"] == c.id:
                    return {**out, "person": p.id, "ask": x["ask"], "at": p.event["at"][:10], "filing": p.event["filing"],
                            "said": f"{first(c)} is the only person you know who has worked inside {here}; you last spoke in {when(c.last_met())}.",
                            "why": f"{_basis(s)}. {spoke}"}
            # or a filing that fits what the contact did there
            w = next((w for w in self.warm(quiet_months, days, limit=99) if w["contact"]["id"] == c.id and w["symbol"] == sym), None)
            f = self.filings.get(w["filing"]) if w else None
            if f and f["category"] in ONLY_THING:
                ask = ASK["only"].format(company=here, thing=ONLY_THING[f["category"]])
                return {**out, "ask": ask, "at": f["at"][:10], "filing": f["id"],
                        "why": f"{_basis(s)}. {spoke} " + w["reason"].rsplit(f" {first(c)} ", 1)[0] + f" Ask: {ask}"}
        return None

    # -- blind spots --------------------------------------------------------------------------------
    def coverage(self, symbols):
        """For each holding, how the network covers it: someone inside or formerly inside, an outside view, or nobody."""
        out = []
        for sym in symbols:
            org = self.reg.by_symbol.get(sym)
            if org is None:
                continue
            calls = self.who_to_call(org, limit=20)
            inside = [r for r in calls if r["relation"] in ("inside", "former")]
            # Anyone with a seat there, now or once, counts, whatever their strongest angle is today: a former
            # insider now at a competitor has still worked inside.
            held = {c.id: links.months_since(c, self.today) for _, c, _, _ in self._held(org)}
            held.update({r["contact"]["id"]: r["contact"]["months"] for r in inside})
            level = "inside" if held else "outside" if calls else "none"
            best = (inside or calls or [None])[0]
            stale = bool(held) and all((m or 0) >= 24 for m in held.values())
            out.append({"symbol": sym, "company": org.name, "level": level, "people": len(calls), "stale": stale,
                        "best": {"name": best["contact"]["name"], "relation": best["relation"], "last": best["contact"]["last"]} if best else None})
        return out


    # -- pull: the network's view of one company ----------------------------------------------------
    def org_for(self, symbol, name="", sector=""):
        """The organisation behind a ticker. One the registry has never seen still gets an answer: its name
        is matched against every career, and its sector, if given, places it among the themes."""
        org = self.reg.by_symbol.get(symbol.upper())
        if org is None:
            org = self.reg.org(name or symbol)
            if not org.known and sector and not org.themes:
                org.themes = self.reg.themes_in(sector)[:1]
        return org

    def company(self, symbol, name="", sector="", focus=(), words=()):
        """Everything the network holds on one company: who to call, the people in its recent filings and
        the routes to them, and anything unusual about who is coming and going."""
        org = self.org_for(symbol, name, sector)
        call = self.who_to_call(org, focus, words)
        ppl = []
        for p in sorted((p for p in self.filed if p.symbol == symbol.upper()), key=lambda p: (-people.SENIORITY[p.seniority], p.name)):
            r = self.reach(p, limit=1)
            best = r["paths"][0] if r["paths"] and r["paths"][0]["strength"] >= GOOD else None
            has = bool(self.prep(p))                       # the path speaks for this person; no second line about an overlap
            ppl.append({"person": r["person"], "identity": r["identity"], "you": r["you"], "path": None if has else best, "prep": has})
        gone = self.exits(symbol.upper())
        gone = gone if len(gone) >= 3 else []
        inside = {r["contact"]["id"] for r in call if r["relation"] in ("inside", "former")} | {c.id for _, c, _, _ in self._held(org)}
        if inside:
            cover = f"{_people(len(inside), word=False)} {'has' if len(inside) == 1 else 'have'} worked inside {org.name}."
        elif call:
            cover = f"Nobody you know has worked inside {org.name}. {len(call)} can speak to it from outside."
        elif org.known or org.themes:
            cover = f"Nobody you know has worked at {org.name}, a competitor, a supplier or a customer."
        else:
            cover = f"Nobody you know has worked at {org.name}. FINN has no sector on file for it, so it cannot look for competitors."
        return {"symbol": symbol.upper(), "company": org.name, "themes": org.themes, "cover": cover, "call": call, "people": ppl,
                "exits": self._exits_line(gone) if gone else "", "patterns": self.patterns(symbol), "fit": self.fit(symbol),
                "counted": sorted(inside)}                    # who the cover's count names: the page lists each of them

    def _exits_line(self, gone):
        days = (gone[-1].event["effective"] - gone[0].event["effective"]).days + 1
        return f"{len(gone)} senior people left within {days} days: " + ", ".join(f"{q.name} ({roles.short(q.event['role'])})" for q in gone) + "."

    def team(self, symbol):
        """Before a management meeting: each person in the company's recent filings who is there now, with
        their path, the routes to them and what to ask."""
        here = [p for p in self.filed if p.symbol == symbol.upper() and p.change != "leaves"]
        execs = [p for p in here if p.seniority in ("top", "senior")]
        # Management first. With no executive in a new seat, a new director with a path is who there is to prepare for.
        return [self.diligence(p) for p in execs or [p for p in here if self.prep(p)]]

    def contact_brief(self, c, symbols=()):
        """One contact, turned round: which holdings they can speak to, and who in recent filings they know."""
        helps = []
        for sym in symbols:
            org = self.reg.by_symbol.get(sym)
            row = org and next((r for r in self.who_to_call(org, limit=99) if r["contact"]["id"] == c.id), None)
            if row and row["relation"] != "sector":
                helps.append({"symbol": sym, "company": org.name, "relation": row["relation"], "line": row["line"],
                              "caution": row["caution"], "relevance": row["relevance"]})
        knows = []
        for p in self.filed:
            link, _ = links.between(c, p, self.year)
            if link and link.strength >= GOOD and self.known(p) is not c:
                knows.append({"person": self.person_view(p), "label": link.label, "line": f"{first(c)} and {first(p)} {link.basis}."})
        themes = [t for t in dict.fromkeys(t for s in c.career for t in self.reg.stint_themes(s.org, s.role, s.division))
                  if any(r["contact"]["id"] == c.id for r in self.expertise(t, limit=3))]
        path = [{"org": s.org.name, "role": s.role, "years": s.years(), "now": s.current} for s in c.career]
        return {"contact": self.contact_view(c), "path": path, "helps": sorted(helps, key=lambda h: -h["relevance"]),
                "knows": knows, "themes": themes}

    # -- what the network noticed --------------------------------------------------------------------
    def notices(self, symbols=(), days=30, limit=12):
        """The short list a person would not have put together themselves, most worth knowing first.
        Each entry says what was noticed, the evidence, and the contact it points to."""
        since, out = self.today - dt.timedelta(days=days), []

        def add(weight, kind, line, why, at=None, symbol="", contact=None, filing="", person="", key="", card=None):
            out.append({"kind": kind, "line": line, "why": why, "at": at.isoformat() if at else "", "symbol": symbol,
                        "contact": self.contact_view(contact) if contact else None, "filing": filing, "person": person,
                        "key": key, "weight": round(weight, 2)})
            if card:
                out[-1]["card"] = card

        by_id = {c.id: c for c in self.contacts}
        for p in self.filed:
            e, co = p.event, p.company.name
            filed = dt.date.fromisoformat(e["at"][:10])
            if filed < since:
                continue
            role, rank = roles.short(e["role"]), people.SENIORITY[p.seniority]
            for c, v in self.verdicts.get(p.id, []):
                if v.status == "same":
                    verb = {"joins": f"has joined {co} as {role}", "moves": f"is now {role} at {co}", "leaves": f"has left {co}"}[p.change]
                    key = f"{p.id}|{c.id}"
                    inside = " Works there now: keep the conversation to what is public." if p.change != "leaves" else ""
                    add(0.9, "contact", f"{c.name}, who you know, {verb}.", v.why + f" Filed {filed:%-d %b}." + inside, filed, p.symbol, c, e["filing"], p.id,
                        key if key in self.said else "")     # an answer the investor gave can be changed where it shows
                elif v.status == "different" and f"{p.id}|{c.id}" in self.said and p.change != "leaves":
                    # Someone else, as the investor said: the answer stays where the question was, so a mis-tap can be undone
                    add(0.55 + 0.3 * self.tie(c), "different", f"You said {_s(co)} new {role}, {p.name}, is not the {c.name} you know.",
                        f"Filed {filed:%-d %b}.", filed, p.symbol, c, e["filing"], p.id, f"{p.id}|{c.id}")
                elif v.status == "possible" and p.change != "leaves":
                    now = c.current
                    add(0.55 + 0.3 * self.tie(c), "identity",
                        f"{_s(co)} new {role} is a {p.name}. You know a {c.name}" + (f", {now.role} at {now.org.name}" if now else "") + ". Is it the same person?",
                        v.why, filed, p.symbol, c, e["filing"], p.id, f"{p.id}|{c.id}")
            if self.known(p):
                continue
            r = self.reach(p, limit=1)
            if r["you"] and r["you"]["label"] != "weak":
                add(0.8, "reach", f"You may know {_s(co)} {'new ' if p.change == 'joins' else ''}{role}, {p.name}, yourself.", r["you"]["line"], filed, p.symbol, None, e["filing"], p.id)
            d = self.prep(p)
            if d:
                # The path is the notice: who is on it and where, from the filing and the investor's own records
                on = [f"{x['pin']['contact']['name']} ({STATION[x['pin']['kind']].format(_the(x['org'])) if x['kind'] == 'listed' and x['pin']['kind'] in STATION else x['pin']['tag'].lower()})"
                      for x in d["stations"] if x["kind"] != "gap" and x["pin"] and x["pin"]["ask"]]
                off = next((f" {x['pin']['contact']['name']} holds the same seat at a competitor." for x in d["stations"] if x["kind"] == "gap" and x["pin"]), "")
                add(0.6 + 0.05 * d["pins"] + 0.03 * rank, "path", d["line"] or f"{_each(d['pins'])} about {p.name}.",
                    f"{_s(co)} {'new ' if p.change == 'joins' else ''}{role}, filed {filed:%-d %b}. " + _list(on) + "." + off, filed, p.symbol, None, e["filing"], p.id)
                out[-1]["q"] = d["q"]
                continue
            best = r["paths"][0] if r["paths"] else None
            if not best or best["strength"] < GOOD or rank == 0:
                continue
            c = by_id[best["contact"]["id"]]
            if p.change == "leaves":
                if best["strength"] >= 0.3 and rank >= 2:
                    add(0.3 + 0.3 * best["strength"], "reach", f"{first(c)} can tell you about {p.name}, who is leaving {co} as {role}.",
                        best["line"] + " " + best["spoke"], filed, p.symbol, c, e["filing"], p.id)
            else:
                add(0.4 + 0.4 * best["strength"] + 0.05 * rank, "reach",
                    f"You are one call from {_s(co)} {'new ' if p.change == 'joins' else ''}{role}, {p.name}.",
                    best["line"] + " " + best["spoke"], filed, p.symbol, c, e["filing"], p.id)
        for sym in dict.fromkeys(p.symbol for p in self.filed):
            gone = self.exits(sym)
            if len(gone) >= 3 and gone[-1].event["effective"] >= since:
                org = self.reg.by_symbol.get(sym) or gone[0].company
                call = [r for r in self.who_to_call(org, limit=3) if r["relation"] in ("inside", "former")]
                c = by_id[call[0]["contact"]["id"]] if call else None
                add(0.75 if c else 0.6, "exits", f"{org.name}: " + self._exits_line(gone),
                    (f"{c.name} can say what is behind it. {call[0]['line']}" if c else "Nobody you know has worked inside the company."),
                    gone[-1].event["effective"], sym, c, gone[-1].event["filing"])
        for sym in dict.fromkeys(p.symbol for p in self.filed):
            for pat in self.patterns(sym):
                at = dt.date.fromisoformat(pat["at"])
                if at >= since:
                    pin = pat["pin"]
                    # A join of filings that Push reads one by one, with one person to ask: it may raise a card on Today
                    card = {"symbols": [sym], "line": pat["line"].split(": ", 1)[1][:1].upper() + pat["line"].split(": ", 1)[1][1:]} if pin else None
                    add(0.8 if pin else 0.65, pat["kind"], pat["line"],
                        pat["why"] + (f" Ask {pin['contact']['name']}, {pin['basis']}: {pin['ask']}" if pin else " " + pat["none"]),
                        at, sym, by_id[pin["contact"]["id"]] if pin else None, pat["filing"], card=card)
        seen = set()
        for f in sorted(self.filings.values(), key=lambda f: f["at"], reverse=True):
            at = dt.date.fromisoformat(f["at"][:10])
            if at < since or f["category"] == "results":
                continue
            for r in self.for_event(f, limit=1):
                if (f["symbol"], f["category"], r["contact"]["id"]) in seen:
                    continue
                seen.add((f["symbol"], f["category"], r["contact"]["id"]))
                org = self.reg.by_symbol[f["symbol"]]
                # Someone you know whose own filing is news at this company: an event there that day joins that row, said once
                mine = next((o for o in out if o["kind"] == "contact" and o["symbol"] == f["symbol"] and o["contact"]["id"] == r["contact"]["id"]
                             and o["at"] == at.isoformat()), None)     # the same day only: a later filing keeps its own row and date
                if mine:
                    also = f" Also filed {at:%-d %b}: {f['line'].rstrip('.')}."
                    cut = mine["why"].find(" Works there now:")
                    mine["why"] = mine["why"][:cut] + also + mine["why"][cut:] if cut >= 0 else mine["why"] + also
                    continue
                add(0.35 + 0.4 * r["relevance"] + (0.1 if f["tier"] == "act" else 0), "event",
                    f"{org.name}: {f['line'].rstrip('.')}. {r['contact']['name']} is the person to ask.", r["line"] + (" " + r["caution"] if r["caution"] else ""),
                    at, f["symbol"], by_id[r["contact"]["id"]], f["id"])
        one = self.one_call(days)
        if one:
            add(0.85, "onecall", one["line"], one["why"], dt.date.fromisoformat(one["at"]), "", by_id[one["contact"]["id"]],
                card={"symbols": one["companies"], "line": one["card"], "rows": one["rows"], "sheet": one["sheet"]})
        only = self.only_one(symbols)
        on_path = next((o for o in out if only and o["kind"] == "path" and o["person"] == only["person"]), None)
        if on_path:
            on_path["why"] += " " + only["said"]             # said once, where the question already is
        elif only:
            add(0.6, "only", only["line"], only["why"], dt.date.fromisoformat(only["at"]), only["symbol"], by_id[only["contact"]["id"]], only["filing"])
        taken = {o["contact"]["id"] for o in out if o["contact"]} | ({only["contact"]["id"]} if only else set())
        for w in [w for w in self.warm() if w["contact"]["id"] not in taken][:3]:
            # dated by its reason, so a window shows it only while the reason is in it
            add(0.3 + min(w["score"], 1.5) / 5, "warm", f"A reason to call {w['contact']['name']}, after {w['quiet']} of silence.", w["reason"],
                dt.date.fromisoformat(w["at"]), w["symbol"], by_id[w["contact"]["id"]], w["filing"])
        cover = self.coverage(symbols)
        blind = [x["company"] for x in cover if x["level"] != "inside"]
        if blind:
            add(0.35, "gap", f"Nobody you know has worked inside {len(blind)} of your {len(cover)} holdings.", _list(blind) + ".")
        cold = [x for x in cover if x["stale"] and not (only and only["symbol"] == x["symbol"])]     # said once, above
        if cold:
            add(0.3, "gap", f"Your inside view of {len(cold)} holding{'s' if len(cold) > 1 else ''} is going cold.",
                "; ".join(f"{x['company']}: {x['best']['name']}, last spoken to in {x['best']['last']}" for x in cold) + ".")
        out.sort(key=lambda x: -x["weight"])
        return out[:limit]


def _results(f):
    """A results filing's figures in words, from the exchange's XBRL as push.json carries them:
    'revenue up 20.9%, profit down 33.4%'. Empty when the filing carries no figures."""
    r = f.get("results") or {}
    said = [f"{label} {'up' if v >= 0 else 'down'} {abs(v):.1f}%" for label, v in ((r.get("top_label", "").lower(), r.get("top_yoy")), ("profit", r.get("pat_yoy")))
            if label and v is not None]
    return ", ".join(said)


def _s(name):
    return name + ("'" if name.endswith("s") else "'s")


def _shares_word(a, b):
    """True when two phrases share a meaningful word, allowing endings: tax/taxation, tyre/tyres, project/projects."""
    wa = [w for w in re.findall(r"[a-z]{3,}", a.lower()) if w not in STOP]
    wb = [w for w in re.findall(r"[a-z]{3,}", b.lower()) if w not in STOP]
    return any(x.startswith(y) or y.startswith(x) for x in wa for y in wb)


def _the(name):
    """'Dani family office' reads as 'the Dani family office' in a sentence; 'IDFC Limited' stands as it is."""
    return ("the " if re.search(r"\b(office|group)$", name, re.I) else "") + name


SEATS = [(r"chief financial officer|\bcfo\b", "CFO"), (r"chief operating officer|\bcoo\b", "COO"), (r"chief risk officer", "CRO"),
         (r"chief human resources officer|\bchro\b", "CHRO"), (r"chief technology officer|\bcto\b", "CTO"),
         (r"company secretary", "company secretary"), (r"compliance", "compliance officer"), (r"general counsel", "general counsel")]


def _seat(role):
    """The seat a role is, short enough for a question: 'Interim CFO' -> 'CFO', 'Managing Director & Chief Executive Officer' -> 'MD & CEO'."""
    r = roles.short(re.sub(r"\b(interim|acting|additional|designate)\b", "", role, flags=re.I).strip(" ,-–"))
    if r == "MD & CEO" or r.islower():
        return r
    head, _, rest = r.partition(", ")
    if rest and head.lower() in roles.GENERIC | {"executive vice president", "senior vice president"}:
        r = rest                                   # a rank and a seat: the seat is what the question is about
    return next((short for pattern, short in SEATS if re.search(pattern, role.lower())), r)


def _title(role):
    """A filed title as it reads in a sentence: 'Head – Internal Audit, Risk & Control' -> 'Head of Internal Audit, Risk & Control'."""
    return re.sub(r"^((?:Group )?Head)\s+[–-]\s+", r"\1 of ", role.strip())


def _area(role):
    """The seat's line of work in a word, from the filed title: 'Compliance Officer' -> 'compliance'."""
    return next((word for pattern, word in AREAS if re.search(pattern, role.lower())), "")


def _areas(role):
    """Every line of work a filed title names: 'Company Secretary & Compliance Officer' is two."""
    return {word for pattern, word in AREAS if re.search(pattern, role.lower())}


def _basis(s):
    return s.role + (f", {s.years()}" if s.years() else "")


def _count(n):
    return ["No", "One", "Two", "Three", "Four", "Five", "Six"][n] if n < 7 else str(n)


def _people(n, word=True):
    """'One person you know', 'Three people you know'; '1 person you know' with word=False"""
    return f"{_count(n) if word else n} {'person' if n == 1 else 'people'} you know"


def _each(n):
    return f"{_people(n)} can answer one question" if n == 1 else f"{_people(n)} can each answer one question"


def _list(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
