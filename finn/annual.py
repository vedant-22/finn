"""The FY26 annual report's notes where the story and the numbers can part, read by rules.

Three things are read: the auditor's reports on the financial statements (the opinion, each emphasis of
matter, a going-concern uncertainty, the audit-trail exception), the contingent-liability note (claims
not acknowledged as debt, both years), and the related-party note (the holding company, by name). The
wording of all three is set by regulation (SA 700 and 706 headings, Schedule III's heads, Ind AS 24),
so it repeats across companies in a way that prose does not. No model reads any of it.

Two stages. cut() takes every page of the PDF and keeps the few the reader needs, by their headings,
and sweeps the whole PDF for the headings an auditor uses to modify or qualify a report. read() works
only on the kept pages. Pages are keyed by the PDF's own page number, which is what `url#page=N` opens.

What a reader may show is held to its page: a quote matches the cited page exactly once whitespace and
hyphenated line breaks are joined (no fuzzy match, no neighbouring page), and a figure is shown as it
is printed. Where a rule can't read a note it shows the note's page and says why, never a guess.
"""
import re

# ---------- text ----------

def flat(t):
    """One line: a word broken over a line by a hyphen joined, every run of whitespace one space."""
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", t)        # control characters some PDFs carry
    t = re.sub("(\\w)[-­]\\s*\\n\\s*(?=[a-z])", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def on_page(quote, pages, page):
    """True only if the quote is on that very page, exactly, after flat()."""
    return bool(quote) and page in pages and flat(quote) in flat(pages[page])


# ---------- the cut ----------

# SA 700's heading for the audit of a set of financial statements; a report with no other set omits the word
AUDIT_HEAD = re.compile(r"Report\s+on\s+the\s+Audit\s+of\s+the\s+(?:(Standalone|Consolidated)\s+)?(?:Ind\s*AS\s+)?Financial\s+Statements", re.I)
# Where a report's own text has ended and its annexures or the statements begin
REPORT_END = re.compile(r"(?im)^[ \t]*Annexure[ \t]*[-–]?[ \t]*[\"“‘']?[ \t]*(?:A|1|I)\b[ \t]*[\"”’']?\s*(?:to\s+the|referred)"
                        r"|^[ \t]*(?:Standalone\s+|Consolidated\s+)?Balance\s+Sheet\s+as\s+at")
REPORT_MAX = 14          # pages; the longest read so far, a bank's consolidated report, runs 12 before its annexures

# The headings an auditor uses when a report is modified or a matter is stressed (SA 705, SA 706, SA 570)
SWEEP = [
    ("emphasis", re.compile(r"Emphasis\s+of\s+Matters?\b", re.I)),
    ("going_concern", re.compile(r"Material\s+Uncertainty\s+Related\s+to\s+Going\s+Concern", re.I)),
    ("qualified", re.compile(r"(?<![Uu]n)(?<![Uu]n-)\bQualified\s+Opinion\b", re.I)),
    ("adverse", re.compile(r"\bAdverse\s+Opinion\b", re.I)),
    ("disclaimer", re.compile(r"\bDisclaimer\s+of\s+Opinion\b", re.I)),
]
# A sweep hit outside the financial-statement audit reports belongs to one of these, by a named rule
OUT_OF_SCOPE = [
    ("sustainability assurance", re.compile(r"BRSR|Sustainability|Reasonable\s+Assurance|Limited\s+Assurance", re.I)),
    ("secretarial audit", re.compile(r"Secretarial\s+Audit", re.I)),
    ("board's report", re.compile(r"Board.?s\s+Report|Directors.?\s+Report|Report\s+of\s+the\s+Board", re.I)),
]

# A numbered note heading ("31.", "Note 31 a :", "NOTE [32]", "Note 42: Commitments and contingencies"), or a bank's Schedule 12
NOTE_HEAD = re.compile(
    r"(?im)^[ \t]*(?:note[ \t]*)?\[?[ \t]*\d{1,3}(?:\.\d{1,2})?[ \t]*\]?(?:[ \t]*[a-z](?![a-z]))?[ \t]*[.:]?[ \t]*(?:\n[ \t]*)?(?:\(?[a-z]\)[ \t]*)?"
    r"(?:contingent\s+liabilit|commitments\s+and\s+contingenc|contingencies\s+and\s+commitments)"
    r"|^[ \t]*schedule[ \t]*12[ \t]*[-–:]?[ \t]*contingent\s+liabilit")
# "Claims against the Company not acknowledged as debt", and the forms seen beside it: "disputed and", "Claims/Suits filed
# against the Group", "Claims (excluding claims by employees ...) not acknowledged as debts"
CLAIMS = re.compile(r"claims?(?:\s*/\s*suits?)?(?:\s*\((?:[^()]|\([^()]*\))*\))?\s+(?:made\s+|filed\s+)?(?:against\s+the\s+\w+(?:\s+\w+)?\s+)?"
                    r"(?:disputed\s+and\s+)?(?:which\s+are\s+)?not\s+acknowledged\s+as\s+debts?", re.I)
POLICY = re.compile(r"contingent\s+liabilit(?:y|ies)\s+(?:is|are)\s+(?:a\s+possible|disclosed|not\s+recognised)", re.I)
NONE_STATED = re.compile(r"there\s+(?:are|were)\s+no\s+contingent\s+liabilit", re.I)
RP_HEAD = re.compile(r"related\s+part(?:y|ies)", re.I)
HOLDING = re.compile(r"(?:ultimate\s+)?holding\s+company", re.I)


def audit_reports(pages):
    """Each set's audit report: {set, start, end}, from the SA 700 heading to the page before its annexures."""
    out, seen = [], set()
    n = max(pages)
    for p in sorted(pages):
        m = AUDIT_HEAD.search(pages[p])
        if not m:
            continue
        kind = (m.group(1) or "standalone").lower()
        if kind in seen:
            continue
        seen.add(kind)
        end = p
        while end + 1 <= min(n, p + REPORT_MAX - 1) and end + 1 in pages and not REPORT_END.search(pages[end + 1][:800]):
            end += 1
        out.append({"set": kind, "start": p, "end": end})
    return out


def set_ranges(reports, n):
    """The pages of each set's statements: from its audit report to the next report, or the end."""
    starts = sorted((r["start"], r["set"]) for r in reports)
    return {kind: (s, (starts[i + 1][0] - 1) if i + 1 < len(starts) else n) for i, (s, kind) in enumerate(starts)}


def find_note(pages, rng):
    """The contingent-liability note's page in one set: a numbered heading, the one the claims follow."""
    best = None
    for p in range(rng[0], rng[1] + 1):
        t = pages.get(p, "")
        for m in NOTE_HEAD.finditer(t):
            after = t[m.end():m.end() + 4000] + "\n" + pages.get(p + 1, "")[:1500]
            score = 2 if CLAIMS.search(after) else 1 if NONE_STATED.search(after[:400]) else 0
            if score == 0 and re.search(r"\d\.\d", m.group(0)) and POLICY.search(after[:600]):
                continue                     # a numbered accounting policy ("2.23 Contingent liabilities"), not the note
            if best is None or score > best[0] or (score == best[0] and score == 0):
                best = (score, p, m.start(), m.group(0))
    if best is None or best[0] == 0:
        # No heading the rules know has claims under it: the claims line itself is the anchor, where a
        # contingent-liability title stands within the 600 characters above it (Havells' "A Contingent liabilities")
        for p in range(rng[0], rng[1] + 1):
            t = pages.get(p, "")
            for m in CLAIMS.finditer(t):
                head = [h for h in re.finditer(r"contingent\s+liabilit", t[max(0, m.start() - 600):m.start()], re.I)]
                if head and not POLICY.search(t[m.start():m.start() + 300]):
                    at = max(0, m.start() - 600) + head[-1].start()
                    nos = re.findall(r"(?im)^[ \t]*(?:note[ \t]*)?(\d{1,3})[ \t]*[.:]?[ \t]+[A-Z]", t[:at])
                    return {"page": p, "at": at, "found_claims": True, "note": nos[-1] if nos else None}
    if best is None:
        return None
    no = "Schedule 12" if re.search(r"schedule", best[3], re.I) else re.search(r"\d{1,3}(?:\.\d{1,2})?", best[3]).group(0)
    return {"page": best[1], "at": best[2], "found_claims": best[0] == 2, "note": no}


def find_related(pages, rng):
    """Pages in one set that name the holding company in the related-party note."""
    return [p for p in range(rng[0], rng[1] + 1)
            if RP_HEAD.search(pages.get(p, "")) and HOLDING.search(pages.get(p, ""))][:4]


def sweep(pages, reports):
    """Every page with a modifying heading, and where it sits: in a cut audit report, or out of scope by rule."""
    spans = [(r["start"], r["end"], r["set"]) for r in reports]
    hits = []
    for p in sorted(pages):
        for kind, rx in SWEEP:
            if not rx.search(pages[p]):
                continue
            where = next((f"{s} audit report" for a, b, s in spans if a <= p <= b), None)
            if where is None:
                where = next((name for name, orx in OUT_OF_SCOPE if orx.search(pages[p])), "unaccounted")
            hits.append({"page": p, "heading": kind, "where": where})
    return hits


def cut(pages):
    """The pages the reader needs, and what the sweep found. `pages` is {pdf page number: text}, every page."""
    n = max(pages)
    reports = audit_reports(pages)
    ranges = set_ranges(reports, n)
    keep = set()
    for r in reports:
        keep.update(range(r["start"], r["end"] + 1))
    notes, related = {}, {}
    for kind, rng in ranges.items():
        note = find_note(pages, rng)
        if note:
            notes[kind] = note
            keep.update(x for x in (note["page"] - 1, note["page"], note["page"] + 1, note["page"] + 2) if x in pages)
        related[kind] = find_related(pages, rng)
        keep.update(x for p in related[kind] for x in (p, p + 1) if x in pages)
    hits = sweep(pages, reports)
    keep.update(h["page"] for h in hits)
    return {"pages": {p: pages[p] for p in sorted(keep)}, "reports": reports, "ranges": ranges,
            "notes": notes, "related": related, "sweep": hits, "pages_total": n}


# ---------- figures ----------

NUM = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?\s*\*{0,2}$")
# The rupee sign comes out of these PDFs' fonts as ₹, `, ¢, v, C or I
UNIT = re.compile(r"(?:₹|`|¢|\bRs\.?|\bINR\b|Rupees|\bv\b|\bC\b|\bI\b|\bH\b)\s*(?:in\s+|/\s*)?(crores?|lakhs?|millions?|thousands?)\b"
                  r"|\(\s*in\s+(crores?|lakhs?|millions?|thousands?)\s*\)", re.I)       # "( in crores)": the sign lost
PER_CRORE = {"crore": 1, "lakh": 100, "million": 10, "thousand": 10000}
YEAR = re.compile(r"(?:March|Mar)\W{0,3}(?:31(?:st)?\W{0,3})?(20\d\d)|31(?:st)?\W{0,3}(?:March|Mar|0?3)\W{1,3}(20\d\d)", re.I)


THOUSANDS = re.compile(r"(?:₹|`|¢|\bRs\.?|\bINR\b|\bC\b|\bI\b)\s*(?:in\s+)?[‘’']000\b")


def year_columns(before, after):
    """The two years a table's columns are headed with, in their order: after the claims line if two are
    there, otherwise the last two distinct years above it."""
    ys = lambda t: [int(a or b) for a, b in YEAR.findall(t)]
    a = [y for i, y in enumerate(ys(after)) if y not in ys(after)[:i]]
    if len(a) >= 2:
        return a[:2]
    last = []
    for y in reversed(ys(before)):
        if y not in last:
            last.append(y)
        if len(last) == 2:
            break
    return last[::-1]


def unit_of(s):
    m = UNIT.search(s)
    if m:
        return (m.group(1) or m.group(2)).lower().rstrip("s")
    return "thousand" if THOUSANDS.search(s) else None


def number(s):
    """A printed figure as a float: '1,11,006' and '(12.5)' too. Not a figure: None."""
    s = s.strip().rstrip("*").strip()
    if not NUM.match(s):
        return None
    neg = s.startswith("(") or s.startswith("-")
    v = float(s.strip("()-").replace(",", ""))
    return -v if neg else v


def to_crore(v, unit):
    return v / PER_CRORE[unit]


def crore_text(v):
    """₹ crore as an investor reads it: '531', '1,804', '8.4'; halves round up (628.5 is 629)."""
    from decimal import Decimal, ROUND_HALF_UP
    places = "1" if abs(v) >= 100 else "0.1" if abs(v) >= 1 else "0.01"
    d = Decimal(repr(v)).quantize(Decimal(places), rounding=ROUND_HALF_UP)
    s = f"{d:,}"
    return s.rstrip("0").rstrip(".") if "." in s and abs(v) >= 1 else s


# ---------- the auditor ----------

EOM_HEAD = re.compile(r"Emphasis\s+of\s+Matters?\b", re.I)
EOM_END = re.compile(r"Our\s+(?:audit\s+)?opinion\s+is\s+not\s+modified\s+in\s+respect\s+of\s+(?:this|these|the\s+above|the\s+said|such)\s+matters?\.?"
                     r"|Key\s+Audit\s+Matters?\b|Other\s+Matters?\b|Information\s+Other\s+than|Management.?s\s+(?:and\s+Board.?s\s+)?Responsibilit|Responsibilities\s+of\s+Management", re.I)
NOTE_NO = re.compile(r"Notes?\s*(?:No\.?\s*)?(\d{1,3}(?:\.\d{1,2})?)\s*(\(\s*[A-Za-z0-9]{1,4}\s*\))?(\s*\(\s*[ivx]{1,4}\s*\))?")
ITEM = re.compile(r"(?:^|\s)(?:\(\s*(?:i{1,3}|iv|v|vi{1,3}|[a-h])\s*\)|•|[a-h]\.)\s+(?=(?:Note|We|The|As|In)\b)")
GOING = re.compile(r"Material\s+Uncertainty\s+Related\s+to\s+Going\s+Concern", re.I)
MODIFIED = re.compile(r"Basis\s+for\s+(?:Qualified|Adverse)\s+Opinion|(?<![Uu]n)\bQualified\s+Opinion\b|\bAdverse\s+Opinion\b|Disclaimer\s+of\s+Opinion", re.I)
TRAIL = re.compile(r"audit\s+trail", re.I)
# An audit-trail clause with an exception: the software lacked the feature, or it did not run for all of the year
TRAIL_EXCEPT = re.compile(r"\bexcept\b|not\s+(?:been\s+)?enabled|did\s+not\s+(?:operate|have)|was\s+not\s+operat|not\s+operated|not\s+available|does\s+not\s+have|unable\s+to\s+comment", re.I)
DEFINED = re.compile(r"([A-Z][A-Za-z-]+(?:\s+(?:of|and|for|on|the|[A-Z][A-Za-z-]+)){0,7})\s*\(\s*(?:the\s+)?[‘“\"'’]?\s*([A-Z]{2,6})\s*[’”\"'‘]?\s*\)")


def defined_term(text):
    """The first term the auditor defines in the paragraph: an abbreviation and its expansion as written."""
    for m in DEFINED.finditer(text):
        abbr, words = m.group(2), m.group(1).split()
        for i in range(len(words)):
            caps = [w for w in words[i:] if w[0].isupper()]
            if words[i][0].isupper() and "".join(w[0] for w in caps) == abbr:
                return {"abbr": abbr, "expansion": " ".join(words[i:])}
    return None


def note_label(m):
    """'38(B)', '59(a)', '33(b)', '36' from a 'Note ...' match."""
    return (m.group(1) + (re.sub(r"\s+", "", m.group(2)) if m.group(2) else "") + (re.sub(r"\s+", "", m.group(3)) if m.group(3) else ""))


def read_report(pages, rep):
    """One audit report: opinion modified or not, each emphasis of matter (note, quote, defined term), the audit trail."""
    span = [(p, pages[p]) for p in range(rep["start"], rep["end"] + 1) if p in pages]
    out = {"set": rep["set"], "page": rep["start"], "pages": [rep["start"], rep["end"]],
           "modified": False, "going_concern": None, "emphasis": [], "trail": None}
    for p, t in span:
        if MODIFIED.search(t):
            out["modified"] = True
        if out["going_concern"] is None and GOING.search(t):
            out["going_concern"] = p
    for p, t in span:
        ft = flat(t)
        m = EOM_HEAD.search(ft)
        if not m or not re.search(r"draw\s+(?:your\s+)?attention", ft[m.end():m.end() + 300], re.I):
            continue
        body = ft[m.end():]
        e = EOM_END.search(body)
        para = body[:e.start()].strip() if e else body[:1500]
        para = re.sub(r"^[\s.:\d]+", "", para)
        # One item per matter when the paragraph lists them; otherwise the paragraph is one matter
        cuts = [x.start() for x in ITEM.finditer(para)]
        parts = [para[a:b].strip() for a, b in zip([0] + cuts, cuts + [len(para)])] if cuts else [para]
        for part in parts:
            n = NOTE_NO.search(part)
            if not n:
                continue
            out["emphasis"].append({"note": note_label(n), "page": p, "quote": part, "term": defined_term(part)})
        break
    out["trail"] = read_trail(span)
    return out


def clip(text, a, b, before=300, after=600):
    """A quote around text[a:b]: from the start of its sentence (or a word, within 300 characters before) to the
    end of a sentence (or a word, within 600 after). Whole words only, so it is still exact on its page."""
    lo = max(text.rfind(". ", 0, a) + 2, a - before, 0)
    if lo > 0 and text[lo - 1] != " ":
        lo = text.find(" ", lo) + 1
    # A sentence's end, not a list marker's ("i.", "(a).", "ii.")
    end = next((m.start() for m in re.finditer(r"\. ", text[b:b + after]) if not re.search(r"(?:^|[\s(])(?:[ivx]{1,4}|[a-zA-Z])\)?$", text[b:b + m.start()])), None)
    end = b + end if end is not None else -1
    hi = end + 1 if end >= 0 else (len(text) if len(text) <= b + after else text.rfind(" ", b, b + after))
    return text[lo:hi].strip()


LEAD = re.compile(r"Based\s+on\s+our\s+examination", re.I)
PRESERVED = re.compile(r"(?:audit\s+trail|it)\s+(?:of\s+(?:the\s+)?(?:relevant\s+)?prior\s+years?\s+)?has\s+(?:not\s+)?been\s+preserved|preserved\s+by\s+the", re.I)


def read_trail(span):
    """The Rule 11(g) clause: from its 'Based on our examination' (on this page or the one before) to the end of
    the sentence after the first 'audit trail'. Its exception, if any, is quoted from the page it is printed on."""
    flats = [(p, flat(t)) for p, t in span]
    for i, (p, ft) in enumerate(flats):
        m = TRAIL.search(ft)
        if not m:
            continue
        pieces = []                                   # (page, text) parts of the clause, in order
        lead = [x for x in LEAD.finditer(ft, 0, m.start())]
        if lead:
            start = lead[-1].start()
        else:
            start = max(ft.rfind(". ", 0, m.start()), ft.rfind(": ", 0, m.start()))
            start = 0 if start < 0 else start + 2
            if i > 0:
                prev_p, prev = flats[i - 1]
                before = [x for x in LEAD.finditer(prev)]
                if before and not TRAIL.search(prev, before[-1].start()) and not re.search(r"\.\s", ft[:m.start()][:start]):
                    pieces.append((prev_p, prev[before[-1].start():]))
                    start = 0
        stop = ft.find(". ", m.end())
        stop = ft.find(". ", stop + 2) if stop >= 0 else -1
        # The clause ends with the sentence on preserving the audit trail, where an exception is also printed
        # (Dixon's subsidiary, Sun Pharma's two applications): on this page, or early on the next
        pres = PRESERVED.search(ft, m.end(), m.end() + 2500)
        tail = None
        if pres:
            stop = max(stop, ft.find(". ", pres.end()) if ft.find(". ", pres.end()) >= 0 else len(ft) - 1)
        elif i + 1 < len(flats):
            nxt_p, nxt = flats[i + 1]
            np_ = PRESERVED.search(nxt, 0, 1500)
            if np_:
                e = nxt.find(". ", np_.end())
                tail = (nxt_p, nxt[:e + 1 if e >= 0 else len(nxt)])
        pieces.append((p, ft[start:stop + 1 if stop >= 0 else len(ft)]))
        if tail:
            pieces.append(tail)
        for page, text in pieces:
            x = TRAIL_EXCEPT.search(text)
            if x:
                return {"page": page, "exception": True, "quote": clip(text, x.start(), x.end())}
        return {"page": p, "exception": False, "quote": clip(pieces[-1][1], 0, 0)}
    return None


# ---------- contingent liabilities ----------

def read_claims(pages, note):
    """Claims not acknowledged as debt, both years, from the head row the note prints them on.

    Read only when the note prints the figures on the head row itself (one row, or a row per kind as a bank
    does) under a header that puts 31 March 2026 before 31 March 2025, with a unit on the page. A note that
    lists claims by head without printing their total gets its page and no figure: heads are never summed.
    """
    p = note["page"]
    t = pages[p][note["at"]:] + "\n" + pages.get(p + 1, "")
    out = {"page": p, "rows": [], "unit": None, "why": None}
    if NONE_STATED.search(t[:400]):
        m = NONE_STATED.search(t[:400])
        s = flat(t[m.start():m.start() + 300])
        out["none"] = s[:s.find(".") + 1] if "." in s else s
        return out
    lines = [x.strip() for x in t.split("\n")]
    flatlines = "\n".join(lines)
    first = CLAIMS.search(flatlines)
    if not first:
        out["why"] = "no claims line"
        return out
    # The year columns, read nearest the claims line: a header after it, else the last two years printed above it
    # (between the note's title and the claims line, or just above the title, as Sun Pharma prints it)
    before = pages[p][max(0, note["at"] - 600):note["at"]] + "\n" + flatlines[:first.start()]
    head = before + "\n" + flatlines[first.start():first.end() + 600]
    years = year_columns(before, flatlines[first.end():first.end() + 600])
    if years != [2026, 2025]:
        out["why"] = "year columns not 2026 then 2025"
        return out
    unit = unit_of(head) or unit_of(pages[p][:500])
    if not unit:
        out["why"] = "no unit on the page"
        return out
    out["unit"] = unit
    # Walk the lines: a claims label, its wrapped end if any, then two figures on the lines that follow
    i, starts = 0, []
    while i < len(lines):
        # The label on one line, or starting on this line and wrapping onto the next
        one = CLAIMS.search(lines[i])
        two = None if one or i + 1 >= len(lines) else CLAIMS.search(lines[i] + " " + lines[i + 1])
        if not one and not (two and two.start() < len(lines[i])):
            i += 1
            continue
        starts.append(i)
        j = i + (1 if one else 2)
        label = " ".join(lines[i:j])
        # A wrapped end is a fragment ("below)", "(refer note 4)"), never a label of its own ("Sales tax and entry tax")
        while j < len(lines) and j <= i + 3 and number(lines[j]) is None and lines[j] and len(lines[j]) < 60 \
                and not label.rstrip(" *").endswith(":") and re.match(r"[a-z(\[*]", lines[j]) \
                and not re.search(r"as\s+at|march|20\d\d|particulars|^\(?[a-z0-9]{1,4}[.)]\s*$|^\(?[ivx]{1,4}[.)]", lines[j], re.I):
            label += " " + lines[j]
            j += 1
        a = number(lines[j]) if j < len(lines) else None
        b = number(lines[j + 1]) if j + 1 < len(lines) else None
        if a is not None and b is not None and not label.rstrip(" *").endswith(":"):
            out["rows"].append({"label": flat(label), "fy26": lines[j].rstrip("*").strip(), "fy25": lines[j + 1].rstrip("*").strip(),
                                "fy26_cr": to_crore(a, unit), "fy25_cr": to_crore(b, unit)})
            i = j + 2
        else:
            i += 1
    if not out["rows"] and starts:
        total = printed_total(lines, starts[0], unit)
        if total:
            out["rows"].append(total)
    if not out["rows"]:
        out["why"] = "claims listed by head, no total printed"
    return out


ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
MARK = re.compile(r"^\(?((?:i{1,3}|iv|v|vi{1,3}|ix|x)|[a-zA-Z]|\d{1,2})[.)]")
END = re.compile(r"guarantee|commitments", re.I)


def next_mark(tok):
    """The marker after this one at the same level: (a) to (b), (A) to (B), (i) to (ii), (iii) to (iv), 1 to 2."""
    low = tok.lower()
    if tok.isdigit():
        return str(int(tok) + 1)
    if low == "i" or (len(tok) > 1 and low in ROMAN[:-1]):     # a lone i is roman: (i) runs to (ii)
        r = ROMAN[ROMAN.index(low) + 1]
        return r.upper() if tok.isupper() else r
    return chr(ord(tok) + 1) if len(tok) == 1 and tok.isalpha() else None


def block_end(lines, start):
    """Where the claims block ends: at the next marker of the claims line's own level, or at guarantees or
    commitments. A claims line with no marker ends only at those (a sub-head's '(ii)' never ends it)."""
    tok = None
    for x in (lines[start], lines[start - 1] if start else ""):
        m = MARK.match(x.strip())
        if m:
            tok = m.group(1)
            break
    nxt = next_mark(tok) if tok else None
    sib = re.compile(rf"^\(?{re.escape(nxt)}[.)]") if nxt else None
    for k in range(start + 1, min(len(lines), start + 90)):
        if END.search(lines[k]) or (sib and sib.match(lines[k].strip())):
            return k
    return min(len(lines), start + 90)


def dash(s):
    """A figure cell: a number, or a dash or Nil for none."""
    return 0.0 if s.strip() in ("-", "–", "—", "Nil", "nil") else number(s)


def printed_total(lines, start, unit):
    """A claims block that lists heads and closes with one printed Total, read only if its rows add up to it.

    The block runs from the claims line to its sibling head ("(b)", guarantees, commitments). It must hold
    exactly one Total (Maruti prints one per tax head, so none is read there), and every figure pair above
    the Total must sum to it in both years, so a sub-total can't pass for the whole."""
    end = block_end(lines, start)
    block = lines[start + 1:end]
    totals = [k for k, x in enumerate(block) if re.fullmatch(r"total", x, re.I)]
    if len(totals) != 1:
        return None
    k = totals[0]
    if k + 2 >= len(block) + 1 or number(block[k + 1]) is None or number(block[k + 2]) is None:
        return None
    pairs, x = [], 0
    while x < k - 1:
        a, b = dash(block[x]), dash(block[x + 1])
        if a is not None and b is not None:
            pairs.append((a, b)); x += 2
        else:
            x += 1
    t26, t25 = number(block[k + 1]), number(block[k + 2])
    if len(pairs) < 2 or abs(sum(a for a, _ in pairs) - t26) > 0.015 or abs(sum(b for _, b in pairs) - t25) > 0.015:
        return None
    return {"label": "Total", "fy26": block[k + 1].rstrip("*").strip(), "fy25": block[k + 2].rstrip("*").strip(),
            "fy26_cr": to_crore(t26, unit), "fy25_cr": to_crore(t25, unit), "summed_check": len(pairs)}


# ---------- related parties ----------

HOLDING_NAME = re.compile(r"(?:Ultimate\s+)?Holding\s+Company\s*[:\-–]?\s*\n?\s*([A-Z][A-Za-z.&,() ]{3,80}?(?:Limited|Ltd\.?|Corporation|AG|GmbH|plc|Inc\.?|N\.V\.|S\.A\.))", re.M)


def read_holding(pages, plist):
    """The holding company as the related-party note names it, with its page, or None."""
    for p in plist:
        t = pages.get(p, "")
        for m in HOLDING_NAME.finditer(t):
            name = flat(m.group(1))
            if re.search(r"subsidiar|associate|joint|entities|company\s+of", name, re.I):
                continue
            return {"name": name, "page": p}
    return None


# ---------- the notes against the calls ----------

WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
# The report's own term keeps its name; this says it once in plain words, after the figures
CLAIMS_PLAIN = " These are claims made on the company that it has not accepted as owed."
READABLE_PAGES = 3      # a call file with text on fewer pages is a cover letter or a notice, not a transcript


def term_patterns(term):
    """The abbreviation, case-sensitive and word-bounded; the expansion, any case, any space or hyphen between
    its words, a trailing 'of India' or 'Limited' optional (so the shorter form is what is searched and named)."""
    short = re.sub(r"\s+(?:of\s+India|Limited|Ltd\.?)$", "", term["expansion"]) if term.get("expansion") else None
    pats = [("abbr", term["abbr"], re.compile(rf"(?<![A-Za-z0-9]){re.escape(term['abbr'])}(?![A-Za-z0-9])"))]
    if short:
        pats.append(("expansion", short, re.compile(r"[\s\-]+".join(re.escape(w) for w in short.split()), re.I)))
    return pats


def readable_calls(company, call_pages):
    """The company's calls whose transcript FINN has: text on at least three pages, oldest first."""
    out = []
    for c in company.get("calls", []):
        got = call_pages.get(c["url"])
        if c.get("error") or not got:
            continue
        if sum(1 for t in got.values() if len(t.strip()) > 200) >= READABLE_PAGES:
            out.append(c)
    return out


def search_calls(term, company, call_pages):
    """Where the paragraph's own defined term appears in the calls already on the company's page."""
    pats = term_patterns(term)
    calls = readable_calls(company, call_pages)
    hits = []
    for c in calls:
        pages = {int(k): v for k, v in call_pages[c["url"]].items()}
        for p in sorted(pages):
            ft = flat(pages[p])
            m = next((x for _, _, rx in pats for x in [rx.search(ft)] if x), None)
            if not m:
                continue
            # The sentence the term sits in, as printed
            a = max(ft.rfind(". ", 0, m.start()), ft.rfind("? ", 0, m.start()))
            a = 0 if a < 0 else a + 2
            b = ft.find(". ", m.end())
            sentence = ft[a:b + 1 if b >= 0 else len(ft)]
            if len(sentence) > 320:
                lo = max(0, m.start() - a - 150)
                sentence = sentence[lo:lo + 300].strip()
            hits.append({"period": c["period"], "url": c["url"], "page": p, "sentence": sentence})
            break
    return {"names": [n for _, n, _ in pats], "calls": [c["period"] for c in calls],
            "files": len(company.get("calls", [])), "hits": hits}


def calls_line(found):
    """The measured fact, in the words that were measured."""
    names, n, files = found["names"], len(found["calls"]), found["files"]
    if not n:
        return None
    q = [f"‘{x}’" for x in names]
    span = found["calls"][0] if n == 1 else f"{found['calls'][0]} to {found['calls'][-1]}"
    if found["hits"]:
        k = len({h["period"] for h in found["hits"]})
        terms = " or ".join(q)
        where = f"all {n} calls" if k == n and n > 1 else f"{k} of the {n} calls" if n > 1 else "the one call"
        last = found["hits"][-1]
        return {"text": f"{terms} appears in {where} FINN read. The latest is {last['period']}, page {last['page']}.",
                "quote": last["sentence"], "url": last["url"], "page": last["page"], "negative": False}
    neither = f"Neither {q[0]} nor {q[1]}" if len(q) == 2 else f"{q[0]} never"
    if n == 1:
        rest = files - 1
        tail = f"; the other {WORDS.get(rest, rest)} {'file' if rest == 1 else 'files'} couldn’t be read" if rest else ""
        text = f"{neither} appears in the one call FINN could read ({span}){tail}."
    else:
        text = f"{neither} appears in the {n} calls FINN read ({span})."
    if len(q) == 1:
        text = text.replace(" never appears", " appears in none of") if n > 1 else text
    return {"text": text, "negative": True}


# ---------- what the page shows ----------

def _src(kind, page):
    return {"label": f"{kind.capitalize()} report, page {page}", "page": page}


def _years(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def compose(sym, meta, cutmeta, pages, company, call_pages):
    """The served file for one company: a verdict for the closed row, three short blocks, at most two questions.

    Every sentence is made here from parsed fields; every quote and printed figure is checked on its page
    by evals/run_annual.py. `meta` is the report's url and filing; `cutmeta` the cut's reports and notes.
    """
    url = meta["url"]
    reports = {r["set"]: read_report(pages, r) for r in cutmeta["reports"]}
    kind = "consolidated" if "consolidated" in reports else "standalone"
    main = reports.get(kind)
    other = reports.get("standalone" if kind == "consolidated" else "consolidated")
    pat = None
    snap = company.get("snapshot", {})
    if snap.get("years") and snap["years"][-1] == "Mar 2026" and company.get("basis") == kind and snap["pat"][-1] and snap["pat"][-1] > 0:
        pat = snap["pat"][-1]
    out = {"symbol": sym, "read": True, "url": url, "filed": meta["filed"], "source": meta.get("source", "nse"),
           "set": kind, "pages_total": cutmeta["pages_total"], "blocks": [], "questions": [], "checks": {}}

    # The auditor
    matters = []
    for e in main["emphasis"]:
        twin = next((x for x in (other or {}).get("emphasis", []) if x["term"] and e["term"] and x["term"]["abbr"] == e["term"]["abbr"]), None)
        matters.append({"e": e, "set": kind, "twin": twin and {"set": other["set"], "note": twin["note"], "page": twin["page"]}})
    for e in (other or {}).get("emphasis", []):
        if not any(m["twin"] and m["twin"]["page"] == e["page"] and m["twin"]["note"] == e["note"] for m in matters):
            matters.append({"e": e, "set": other["set"], "twin": None})
    modified = any(r["modified"] for r in reports.values())
    going = [r for r in reports.values() if r["going_concern"]]
    both = " and ".join(sorted(reports)) + (" reports" if len(reports) > 1 else " report")
    items = []
    for m in matters:
        e, t = m["e"], m["e"]["term"]
        name = f": {t['expansion']} ({t['abbr']})" if t and m["set"] == kind else ""
        also = f" The {m['twin']['set']} report has it too, as note {m['twin']['note']}." if m["twin"] else \
            f" Only in the {m['set']} report." if len(reports) > 1 else ""
        item = {"text": f"Note {e['note']} of the {m['set']} accounts{name}.{also}",
                "quote": e["quote"], "src": _src(m["set"], e["page"])}
        if t and m["set"] == kind:
            found = search_calls(t, company, call_pages)
            line = calls_line(found)
            m["found"], m["line"] = found, line
            if line:
                item["calls"] = line
        items.append(item)
    if modified:
        lead = "The auditor modified the opinion."
    else:
        lead = f"Opinion not modified (a clean opinion), in the {both}." if not matters else \
            f"Opinion not modified (a clean opinion). The auditor drew attention to {'one matter' if len(matters) == 1 else f'{WORDS[len(matters)]} matters'}:"
    trail = [r for r in reports.values() if r["trail"] and r["trail"]["exception"]]
    block = {"title": "The auditor", "text": lead, "items": items, "src": [_src(r["set"], r["page"]) for r in reports.values()]}
    if going:
        block["going_concern"] = [_src(r["set"], r["going_concern"]) for r in going]
    if trail:
        block["trail"] = {"text": "The auditor lists exceptions to the audit trail, the software’s edit log.",
                          "src": [{**_src(r["set"], r["trail"]["page"]), "quote": r["trail"]["quote"]} for r in trail]}
    out["blocks"].append(block)

    # Contingent liabilities
    note = cutmeta["notes"].get(kind)
    claims = read_claims(pages, note) if note else None
    total = None
    cblock = {"title": "Contingent liabilities"}
    if not note:
        cblock["text"] = "FINN’s rules didn’t find the contingent-liability note."
    else:
        name = note["note"] if note["note"] == "Schedule 12" else f"Note {note['note']}" if note["note"] else "The note"
        where = f"{name}, {kind} accounts, page {note['page']}"
        cblock["src"] = [{"label": where, "page": note["page"]}]
        if claims.get("none"):
            cblock["text"] = "The note says there are none."
            cblock["quote"] = claims["none"]
        elif len(claims["rows"]) == 1:
            r = claims["rows"][0]
            total = r
            ratio = r["fy26_cr"] / pat if pat else None
            # A share that rounds to nothing is said as under 1%, never as 0%
            size = "" if ratio is None else f" That is {_years(ratio)} years of FY26 profit." if ratio >= 1 else \
                " That is under 1% of FY26 profit." if ratio < 0.01 else f" That is {ratio * 100:.0f}% of FY26 profit."
            cblock["text"] = f"Claims not acknowledged as debt: ₹{crore_text(r['fy26_cr'])} crore at 31 March 2026, ₹{crore_text(r['fy25_cr'])} crore a year earlier.{size}{CLAIMS_PLAIN}"
            cblock["printed"] = f"Printed as {r['fy26']} and {r['fy25']}, in ₹ {claims['unit']}."
            total = {**r, "ratio": ratio}
        elif claims["rows"]:
            parts = []
            for r in claims["rows"]:
                kind_of = re.sub(r"^[\s\-–:]+", "", CLAIMS.split(r["label"], maxsplit=1)[-1]).strip(" .*") or "claims"
                parts.append(f"{kind_of} ₹{crore_text(r['fy26_cr'])} crore (₹{crore_text(r['fy25_cr'])} crore a year earlier)")
            cblock["text"] = "Claims not acknowledged as debts, at 31 March 2026: " + "; ".join(parts) + "." + CLAIMS_PLAIN
            cblock["printed"] = "Printed as " + "; ".join(f"{r['fy26']} and {r['fy25']}" for r in claims["rows"]) + f", in ₹ {claims['unit']}."
            if company.get("snapshot", {}).get("financial"):
                cblock["text"] += " A lender’s other contingent lines, such as guarantees given for customers, are its business, so they aren’t shown."
        else:
            cblock["text"] = "The note lists claims by head without printing their total, so no figure is shown." \
                if claims["why"] == "claims listed by head, no total printed" else "FINN’s rules couldn’t read a total from this note, so no figure is shown."
    out["blocks"].append(cblock)

    # The verdict on the closed row, by a fixed order
    lead_matter = next((m for m in matters if m["set"] == kind), matters[0] if matters else None)
    if modified:
        out["verdict"] = "The auditor modified the opinion"
    elif going:
        out["verdict"] = "The auditor reported a going-concern uncertainty"
    elif lead_matter:
        out["verdict"] = f"The auditor drew attention to note {lead_matter['e']['note']}"
    elif total and total["ratio"] and total["ratio"] >= 1:
        out["verdict"] = f"Claims ₹{crore_text(total['fy26_cr'])} crore, {_years(total['ratio'])} years of profit"
    else:
        out["verdict"] = "Opinion not modified"

    # Questions, from one table of templates, at most two
    qs = []
    for m in matters:
        if m["set"] != kind or not m["e"]["term"]:
            continue
        t, e = m["e"]["term"], m["e"]
        head = f"The auditor drew attention to note {e['note']} of the {kind} accounts ({t['expansion']}, {t['abbr']})."
        line, found = m.get("line"), m.get("found")
        n = len(found["calls"]) if found else 0
        if line and line["negative"] and n >= 3:
            qs.append(f"{head} Neither term is in the transcripts of the last {WORDS.get(n, n)} calls. What would settle it, and by when?")
        else:
            qs.append(f"{head} What would settle it, and by when?")
    if total and total["ratio"] is not None and total["ratio"] >= 1:
        qs.append(f"Claims not acknowledged as debt are ₹{crore_text(total['fy26_cr'])} crore, about {_years(total['ratio'])} years of profit. Which of them is closest to a ruling?")
    if total and pat and total["fy25_cr"] > 0 and total["fy26_cr"] >= 1.25 * total["fy25_cr"] and total["fy26_cr"] - total["fy25_cr"] >= 0.1 * pat:
        qs.append(f"Claims not acknowledged as debt rose from ₹{crore_text(total['fy25_cr'])} crore to ₹{crore_text(total['fy26_cr'])} crore in the year. What was added?")
    out["questions"] = qs[:2]

    filed = meta["filed_text"]
    out["foot"] = (f"Read by FINN’s rules from the FY26 annual report filed on NSE on {filed}. "
                   "Each line is quoted from its page; no model read it. The related-party note isn’t read yet.")
    # What run_annual.py checks: the fields behind each sentence
    out["checks"] = {"reports": {k: {"page": r["page"], "modified": r["modified"], "going_concern": r["going_concern"],
                                     "emphasis": [x["note"] for x in r["emphasis"]],
                                     "trail": r["trail"] and r["trail"]["exception"], "trail_page": r["trail"] and r["trail"]["page"]}
                                 for k, r in reports.items()},
                     "claims": claims and {"page": claims["page"], "unit": claims["unit"], "why": claims["why"], "none": bool(claims.get("none")),
                                           "rows": [{"fy26": r["fy26"], "fy25": r["fy25"]} for r in claims["rows"]]},
                     "pat": pat, "ratio": total and total["ratio"],
                     "calls": [{"note": m["e"]["note"], "names": m["found"]["names"], "read": m["found"]["calls"],
                                "hits": [(h["period"], h["page"]) for h in m["found"]["hits"]], "negative": bool(m.get("line") and m["line"]["negative"])}
                               for m in matters if m.get("found")]}
    return out


def not_read(sym, meta, why):
    """A company whose report FINN couldn't read: the page says why, and nothing else."""
    return {"symbol": sym, "read": False, "url": meta.get("url"), "filed": meta.get("filed"), "verdict": "Not read",
            "why": why, "blocks": [], "questions": [], "foot": ""}
