"""A quote is shown only if it is on its cited page, or the page either side, word for word after normalising.
No fuzzy match and no other pages: a changed number, a swapped word or a stitched sentence fails, and so does a cut
inside a word or a number ("17%" can't be shown as "7%", "15.6%" as "6%", "-3.2%" or "(3.2)" as "3.2", "don't" as
"t"): the span starts and ends where a word or number does, and is at least 4 words.
What the screen shows is the page's own text, never the model's, and always whole sentences: the span is widened to the
sentences it sits in, so a quote that leaves out "not", "crore" or "bps" is shown with them. A sentence too long to
show whole (over 1,000 characters, usually a table read as text) isn't shown. Nor is one the page shows only part of:
a page break or a blank line can cut a sentence, so what is shown must end in a full stop, question mark or exclamation
mark, must not start with a lower-case word, and must not follow text left unfinished ("we do not think that" at the
foot of one page, "India will grow." at the head of the next). Page headers and footers between the two are stepped over.
A quote from a turn the moderator introduced as a question isn't shown: the company didn't say what an analyst said in
asking. Quotes carry no speaker's name yet (see asked).
(The ledger's pdf.verify_quote is more forgiving, on purpose: evals/run_quotes.py and docs/adr/0004.)
"""
import re, unicodedata

DASHES = "‐‑‒–—−－"   # hyphens, en and em dash, minus sign, full-width hyphen-minus
SUBS = {"‘": "'", "’": "'", "“": '"', "”": '"', "­": "", **{d: "-" for d in DASHES}}

def normalise(raw):
    """Lower case, one space for any run of white space, plain quotes and dashes; and for every character of the
    result, the offset in raw it came from."""
    out, where, gap = [], [], True
    for i, ch in enumerate(raw):
        for c in unicodedata.normalize("NFKC", SUBS.get(ch, ch)).lower():
            if c.isspace():
                if gap:
                    continue
                c, gap = " ", True
            else:
                gap = False
            out.append(c); where.append(i)
    return "".join(out), where

MIN_WORDS = 4
MAX_SHOWN = 1000
# A full stop after these doesn't end a sentence ("Rs. 12 crore", "Mr. Rao", "No. 3"); nor after a single letter (R. K. Rao)
# or dotted initials (the U.S., the U.K.); and nothing ends one before a lower-case word. Each errs towards showing more.
ABBREV = {"rs", "mr", "mrs", "ms", "dr", "no", "nos", "vs", "viz", "approx", "appx", "ltd", "pvt", "co", "inc", "corp",
          "cr", "mn", "bn", "st", "sr", "jr", "fig", "ref", "sec", "govt", "dept", "avg", "est", "e.g", "i.e", "sq", "ft", "hon"}
END = re.compile(r"[.?!][\"')\]]*\s+|\n\s*\n")

def _sentence_ends(raw):
    """Offsets in raw where a sentence ends (just after its punctuation and the space that follows)."""
    ends = []
    for m in END.finditer(raw):
        if raw[m.start()] in ".?!" and raw[m.end():m.end() + 1].islower():
            continue
        if raw[m.start()] == ".":
            word = re.search(r"([A-Za-z.]+)$", raw[:m.start()])
            w = word.group(1).strip(".") if word else ""
            if word and (w.lower() in ABBREV or len(w) == 1 or "." in w):
                continue
        ends.append(m.end())
    return ends

DONE = re.compile(r"[.?!][\"')\]]*$")

def _spans(raw):
    """The page cut where sentences end, and where a speaker's turn starts ("Name:" at a line's start), so an
    unpunctuated question never runs on into the answer: [(start, stop)], covering it all."""
    cuts = sorted({0, len(raw), *_sentence_ends(raw), *(m.start() for m in TURN.finditer(raw))})
    return [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]

def _prose(s):
    """Running text, not page furniture ("Page 9 of 20", a company's name, a speaker's label): four words or more,
    most of them lower-case."""
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", s)
    return len(s.split()) >= 4 and sum(w[0].islower() for w in words) * 2 > len(words)

def _before(pages, p, spans, i):
    """The running text just before span i of page p, stepping over furniture and into the page before; None at the start."""
    for a, b in reversed(spans[:i]):
        if _prose(pages[p - 1][a:b]):
            return pages[p - 1][a:b].strip()
    if p > 1:
        raw = pages[p - 2]
        return next((raw[a:b].strip() for a, b in reversed(_spans(raw)) if _prose(raw[a:b])), None)
    return None

def _whole(pages, p, a, b):
    """Offsets a to b of page p widened to the sentences they sit in; None if the page holds only part of one."""
    raw = pages[p - 1]
    spans = _spans(raw)
    first = next(i for i, (x, y) in enumerate(spans) if y > a)
    last = next(i for i, (x, y) in enumerate(spans) if y >= b)
    span = raw[spans[first][0]:spans[last][1]].strip()
    letter = re.search(r"[^\W\d_]", span)
    if not DONE.search(span) or (letter and letter.group().islower() and not span[:letter.start()].strip("\"'([ ")):
        return None   # no full stop at its end, or a lower-case start: a piece of a sentence
    if any(m.start() > 0 for m in TURN.finditer(span)):
        return None   # two speakers' words in one span: never shown as one
    prev = _before(pages, p, spans, first)
    if prev is not None and not DONE.search(prev) and not prev.endswith(":") and not TURN.match(span):
        return None   # what came before was left unfinished (a lead-in ending in a colon isn't), so this may be its tail
    return span

def _edge(text, i, step):
    """True if the match may stop beside position i, just outside it (step -1 at its start, +1 at its end): i is outside
    the text, or ends the word or number the match touches. "15.6%" can't be cut to "6%", "14,859" to "859",
    "-3.2%" to "3.2%", "(45.2)" to "45.2)", or "don't" to "t"."""
    if not 0 <= i < len(text):
        return True
    c, inner, beyond = text[i], text[i - step], text[i + step] if 0 <= i + step < len(text) else ""
    if c.isalnum():
        return False
    if inner.isdigit() and c in ".," and beyond.isdigit():
        return False   # inside a number: 15.6, 14,859
    if c == "'" and inner.isalpha() and beyond.isalpha():
        return False   # inside a word: don't, company's
    return not (step < 0 and inner.isdigit() and c in "-+(")   # a sign the quote would drop, or an accounting minus

NAME = r"[A-Z][A-Za-z.'\-]*(?:[ \n]+[A-Z][A-Za-z.'\-]*){0,4}"
TURN = re.compile(rf"(?m)^[ \t]*({NAME})[ \t]*:[ \t]*(?:\n|\S)")   # "Atul Lall:" at a line's start
ASKS = re.compile(rf"(?:line\s+of|question\s+(?:is\s+|comes\s+|will\s+be\s+)?from)\s+(?:the\s+line\s+of\s+)?(?:(?:Mr|Ms|Mrs|Dr)\.?\s+)?"
                  rf"({NAME}?)(?:\s+(?:from|of|with|at)\b|[.,])")   # "The next question is from the line of Siddhartha Bera from Nomura."

def asked(pages, page, at):
    """True if offset `at` of page `page` sits in a questioner's turn: the nearest "Name:" at a line's start before it,
    on that page or the two before, is a name the moderator gave a question to somewhere in the call.
    It can miss and can't accuse: page furniture ("ISIN:", a footer) also looks like a turn's start and hides the
    questioner behind it, and a call whose moderator introduces nobody this way is never refused here. That furniture
    is why no speaker's name is shown yet: a wrong name is worse than none."""
    one = lambda s: " ".join(s.split())
    names = {one(m.group(1)) for pg in pages for m in ASKS.finditer(pg)}
    for p in range(page, max(page - 3, 0), -1):
        marks = [m for m in TURN.finditer(pages[p - 1]) if p < page or m.start() < at]
        if marks:
            return one(marks[-1].group(1)) in names
    return False

def verify(quote, pages, page):
    """{"page", "span"} with the raw text of the page, widened to whole sentences, or None."""
    q = normalise(quote or "")[0].strip()
    if len(q.split()) < MIN_WORDS or not isinstance(page, int):
        return None
    for p in (page, page - 1, page + 1):
        if 1 <= p <= len(pages):
            raw = pages[p - 1]
            text, where = normalise(raw)
            k = text.find(q)
            while k >= 0:
                if _edge(text, k - 1, -1) and _edge(text, k + len(q), 1):
                    span = _whole(pages, p, where[k], where[k + len(q) - 1] + 1)
                    return {"page": p, "span": span} if span and len(span) <= MAX_SHOWN and not asked(pages, p, where[k]) else None
                k = text.find(q, k + 1)
    return None
