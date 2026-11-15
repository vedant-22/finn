"""Is the person in this filing someone we already have a record of?

A wrong match is worse than no match, so the rule is strict and has three answers:

  same       the names are compatible AND something independent ties them (an employer or a school
             both records name), AND nothing contradicts it.
  different  the names are compatible but the records can't be one life: the known person was
             verifiably working somewhere else at the time, or the two careers share nothing.
  possible   the names are compatible and nothing settles it either way. Shown to the investor as a
             question, never as a fact, and nothing further is built on it.

A name alone never gives "same", however rare the name.
"""
import datetime as dt
from dataclasses import dataclass

from . import names
from .people import EXITS

SIZE = {"giant": 1, "large": 1.5}  # everything smaller counts 2; a verdict of "same" needs 2 in all
LAG = dt.timedelta(days=90)     # a contact's record says nothing about a job change until this long after it


@dataclass
class Verdict:
    status: str                 # same, possible, different
    why: str
    ties: list


def _year(stint, asof):
    return (stint.start or 0, asof.year if stint.current else (stint.end or 9999))


def judge(filed, known):
    """`filed` is a person from a filing; `known` is a contact from the investor's own list. None when the names differ."""
    match = names.compare(filed.name, known.name)
    if not match:
        return None
    first = names.clean(known.name).split()[0]
    filed_orgs = {s.org for s in filed.career}
    shared_orgs = [s.org for s in known.career if s.org in filed_orgs]
    shared_schools = [e for e in known.edu if any(e.school == f.school for f in filed.edu)]
    fits = any(k.function == f.function != "other" for k in known.career for f in filed.career if f.org is filed.company)

    # Contradictions. A board seat sits alongside a day job, so only an executive role can clash.
    e = filed.event
    who = first
    if e["seniority"] != "board":
        year = e["effective"].year
        if e["action"] in EXITS or filed.change == "moves":
            # The filed person was inside the company in the year before this date. Was the known person?
            there = any(s.org is filed.company and (s.current or (s.end or 9999) >= year - 1) for s in known.career)
            held = [s for s in known.career if s.start and s.start < year and (s.current or (s.end or 0) >= year - 1)]
            if not there and held and known.asof >= e["effective"] - LAG:
                return Verdict("different", f"{first} was at {held[-1].org.name} ({held[-1].years()}) while this person was at {filed.company.name}.", [])
        elif known.asof >= e["effective"] + LAG:
            # The filed person joined on this date. A record read well after it still shows another job.
            held = [s for s in known.career if s.current]
            if held and not any(s.org is filed.company for s in held):
                return Verdict("different", f"{first} is still at {held[-1].org.name}, on a record read in {known.asof:%B %Y}, after this person joined {filed.company.name}.", [])
    past = [s.org for s in filed.career if s.org is not filed.company]
    starts = [s.start for s in known.career if s.start]
    if len(past) >= 2 and starts and known.asof.year - min(starts) >= 10 and not shared_orgs and not shared_schools:
        return Verdict("different", f"The filing lists {past[0].name} and {past[1].name}; the record of {who} shows neither.", [])

    ties = [o.name for o in dict.fromkeys(shared_orgs)] + [s.name for s in shared_schools]
    # How much a shared employer proves depends on its size: two people of one name at a 200-person
    # firm are one person; at a bank of 200,000 they need not be.
    weight = sum(SIZE.get(o.scale, 2) for o in dict.fromkeys(shared_orgs)) + len(shared_schools) + fits
    if ties and weight >= 2:
        return Verdict("same", "Same name, and both records show " + _list(ties) + ".", ties)
    if ties:
        return Verdict("possible", f"Same name and both records show {ties[0]}, but that is a large employer and nothing else ties them.", ties)
    why = "Same name" + (", and the same line of work" if fits else "") + ", but no employer or school in common"
    if known.asof < e["effective"] + LAG:
        why += f"; your record of {who} is from {known.asof:%B %Y}, before this change"
    return Verdict("possible", why + ".", [])


def _list(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]

