"""How likely two people are to know each other, and how well the investor knows a contact.

Two people who list the same employer have not necessarily met. The estimate below starts from the
size of the organisation and rises with seniority, a shared line of work and time together. It is a
judgement written down as arithmetic so it can be read, argued with and tested; the app shows the
words (strong, good, weak) and the evidence, not the decimal.

  - Years must overlap. Same employer in different years is reported as a near miss, not a link.
  - If either side's years are unknown, the link is kept but marked so and scored at 40%.
  - Two companies in one group are two employers. No link is drawn across a group.
"""
import datetime as dt
from dataclasses import dataclass

from . import names

# Chance that two people picked from one organisation at one time know each other, by headcount band.
BASE = {"tiny": 0.9, "small": 0.55, "mid": 0.25, "large": 0.1, "giant": 0.03, "": 0.2}
# ... if both run large teams (level 3+): leadership groups are small whatever the headcount.
SENIOR = {"tiny": 0.9, "small": 0.75, "mid": 0.55, "large": 0.4, "giant": 0.15, "": 0.4}
# ... if one of them ran the place and the other reported near the top.
TOP = {"tiny": 0.95, "small": 0.85, "mid": 0.7, "large": 0.55, "giant": 0.25, "": 0.5}
SAME_WORK = {"tiny": 0.5, "small": 0.5, "mid": 0.4, "large": 0.3, "giant": 0.12, "": 0.3}
UNDATED = 0.4

HOW = {"family": 0.95, "friend": 0.85, "colleague": 0.75, "classmate": 0.7, "met": 0.45}


@dataclass
class Link:
    kind: str            # worked, board, studied, now
    strength: float
    where: str
    basis: str           # the evidence, as a clause that follows the two names
    years: int = None    # years together, None when not known
    dated: bool = True

    @property
    def label(self):
        return label(self.strength)


def label(x):
    return "strong" if x >= 0.5 else "good" if x >= 0.22 else "weak"


def either(*ps):
    out = 1.0
    for p in ps:
        out *= 1 - p
    return 1 - out


def span(s, year):
    """(start, end) in years. A job announced for next January still starts "now" for our purposes."""
    return (min(s.start, year) if s.start else None), (year if s.current else s.end)


def overlap(a, b, year):
    """Years two stints overlap: a number, 0 when they provably don't, None when a date is missing.
    Someone who left in 2026 (start unknown) and someone there 2016 to now did overlap: counted as 1."""
    (a0, a1), (b0, b1) = span(a, year), span(b, year)
    if (a1 and b0 and a1 < b0) or (b1 and a0 and b1 < a0):
        return 0
    if None not in (a0, a1, b0, b1):
        return max(min(a1, b1) - max(a0, b0), 0.5)  # touching in one calendar year counts as half
    for (x0, x1), (y0, y1) in (((a0, a1), (b0, b1)), ((b0, b1), (a0, a1))):
        if x0 is None and x1 and y0 and y1 and y0 < x1 <= y1:
            return 1
    return None


def worked(a, b, year):
    """The best working link between two people, and the near misses (same employer, different years).
    A job the filing has only just announced can't be a near miss: nobody expects it to overlap the past."""
    best, misses = None, []
    for s in a.career:
        for t in b.career:
            if s.org is not t.org or s.org.is_group:
                continue
            link = _same_org(s, t, year, first(a), first(b))
            if link is None and not _new(s, year) and not _new(t, year):
                misses.append(f"both at {s.org.name}, in different years" +
                              (f" ({s.years()} and {t.years()})" if s.years() and t.years() else ""))
            if link and (best is None or link.strength > best.strength):
                best = link
    return best, misses


def _new(s, year):
    return s.source == "filing" and s.current and bool(s.start) and s.start >= year


def first(person):
    """The name to call someone by in a sentence: the first full word, so "S Ramkumar" is Ramkumar."""
    full = [w for w in names.clean(person.name).replace(".", " ").split() if len(w) > 1]
    return full[0] if full else person.name


def _same_org(s, t, year, a="one", b="the other"):
    yrs = overlap(s, t, year)
    if yrs == 0:
        return None
    org, scale = s.org, s.org.scale
    board = s.function == "board" and t.function == "board"
    if board:
        p = 0.9
    else:
        p = BASE[scale]
        if min(s.level, t.level) >= 3:
            p = either(p, TOP[scale] if max(s.level, t.level) == 5 and "board" not in (s.function, t.function) else SENIOR[scale])
        if s.function == t.function and s.function not in ("other", "general"):
            p = either(p, SAME_WORK[scale])
        if s.division and s.division == t.division:
            p = either(p, 0.5)
    kind = "board" if board else "worked"
    if yrs is None:
        who = b if t.source == "filing" else a
        return Link(kind, p * UNDATED, org.name, f"were both at {org.name}; the filing gives no years for {who}, so whether they overlapped is not known", None, False)
    if _new(s, year) or _new(t, year):
        # One of them has only just arrived: colleagues now, with no history yet.
        old, arrival = (a, b) if _new(t, year) else (b, a)
        return Link("now", min(p, 0.2), org.name, f"are at {org.name} together now; {arrival} has only just arrived, so {old} knows the place, not yet the person", yrs)
    if yrs < 1:
        p *= 0.5
    elif yrs >= 5:
        p = either(p, 0.15)
    lo, hi = max(s.start or 0, t.start or 0), min(span(s, year)[1], span(t, year)[1])
    when = f"up to {hi}" if not (s.start and t.start) else f"{lo}–{hi}" if hi > lo else str(lo)
    when = ", " + when
    both_now = s.current and t.current
    roles = ", ".join(f"{x} as {r}" for x, r in ((a, s.role), (b, t.role)) if r)   # a role no filing states is blank
    if board:
        basis = f"sit on the {org.name} board together" if both_now else f"sat on the {org.name} board together{when}"
    elif label(p) == "weak":
        # Same employer, same years, and nothing else: say so, and say what it is worth.
        basis = (f"are both at {org.name} now" if both_now else f"were both at {org.name}{when}") + \
            (f" ({roles})" if roles else "") + "; at an employer that size they may never have met"
    else:
        basis = (f"work at {org.name} together now" if both_now else f"overlapped at {org.name}{when}") + \
            (f": {roles}" if roles else "")
    return Link(kind, p, org.name, basis, yrs)


def studied(a, b):
    """Same school in the same years. The same school in different years is not a link."""
    best, misses = None, []
    for x in a.edu:
        for y in b.edu:
            if x.school != y.school:
                continue
            if None in (x.start, x.end, y.start, y.end):
                link = Link("studied", 0.05, x.name, f"both studied at {x.name}; years not known", None, False)
            elif x.end <= y.start or y.end <= x.start:
                misses.append(f"both {x.name}, {abs(x.end - y.end)} years apart")
                continue
            elif (x.start, x.end) == (y.start, y.end):
                link = Link("studied", 0.5, x.name, f"were in the same batch at {x.name}, {x.start}–{x.end}", x.end - x.start)
            else:
                lo, hi = max(x.start, y.start), min(x.end, y.end)
                link = Link("studied", 0.2, x.name, f"overlapped at {x.name}, {lo}–{hi}", hi - lo)
            if best is None or link.strength > best.strength:
                best = link
    return best, misses


def between(a, b, year):
    """The strongest link of any kind between two people, plus every near miss."""
    w, m1 = worked(a, b, year)
    s, m2 = studied(a, b)
    links = [l for l in (w, s) if l]
    return (max(links, key=lambda l: l.strength) if links else None), m1 + m2


def tie(contact, today):
    """How well the investor knows a contact, 0 to 1: how they know them, cooled by time since they last
    spoke (the tie loses half its warmth every 30 months) and lifted a little by how often they meet."""
    base = HOW.get(contact.how, 0.4)
    last = contact.last_met()
    months = (today - last).days / 30.4 if last else 120
    warmth = 0.5 ** (months / 30)
    recent = sum(1 for d in contact.met if (today - d).days <= 730)
    return min(1.0, base * (0.5 + 0.5 * warmth) + 0.04 * min(recent, 3))


def months_since(contact, today):
    last = contact.last_met()
    return None if last is None else int((today - last).days / 30.4)
