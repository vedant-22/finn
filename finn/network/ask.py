"""Direct questions to the Network.

No model reads the question and none writes the answer. The question is resolved to things FINN
already holds (a company, a person, a theme) and a kind of question, and the engine answers. That
keeps the investor's contact list out of any prompt, makes every answer repeatable, and means a
name FINN cannot place is met with "which one?" or "I don't have that", never with a guess.

    answer(net, "Who knows the new MD of HDFC Bank?", symbols)  ->  {intent, title, lede, rows, notes, follow}
"""
import re

from . import names, roles
from .engine import FOCUS, STOP, _each, _list

TAG = {"inside": "works there", "former": "worked there", "customer": "customer", "supplier": "supplier",
       "competitor": "competitor", "watcher": "covers it", "group": "same group", "sector": "same sector"}
LINK = {"strong": "a strong link", "good": "a fair link", "weak": "a weak link"}

# The kinds of question, each with the words that give it away. Order matters: first match wins.
CUES = [
    ("warm", r"reconnect|lost touch|catch up|haven.?t spoken|not spoken|keep\w* .*warm|back in touch|been a while|gone (quiet|cold)|reason to call"),
    ("gaps", r"\bblind|\bgaps?\b|no ?one|nobody|uncovered|coverage|where am i (thin|weak)"),
    ("notices", r"notice|what.?s new|anything new|should i know|what changed|\btoday\b|this (week|month)"),
]
REACH = r"who knows|knows? (him|her|them)|\breach|introduc|get to\b|route|way in|connection|do i know (anyone|someone|somebody)|link to"
TEAM = r"\bmeet|management|\bteam\b|promoter|leadership"
THEME = r"go.?to|expert|theme|sector|industry|who (knows|understands) about|map"
ROLE = [  # words in a question that point at a role in a filing
    (r"\bmd\b|managing director|\bceo\b|chief executive", r"managing director|\bmd\b|\bceo\b|chief executive"),
    (r"\bcfo\b|finance chief|chief financial", r"\bcfo\b|chief financial"),
    (r"\bcoo\b|chief operating", r"\bcoo\b|chief operating"),
    (r"general counsel|legal head", r"general counsel|legal"),
    (r"\bchro\b|hr head|head of hr", r"\bchro\b|human resources|\bhr\b"),
    (r"compliance officer", r"compliance officer"),
    (r"company secretary", r"company secretary"),
    (r"chairman|chairperson", r"chair"),
    (r"independent director", r"independent"),
    (r"\bdirector\b", r"director"),
]
EVENT = [  # words in a question that say what kind of event it is about
    ("litigation", r"\btax|litigation|notice|dispute|lawsuit|\bcase\b|legal|penalty|regulator"),
    ("capex", r"capex|\bplant|expansion|capacity|\bproject"),
    ("M&A", r"\bdeal|acqui|merger|m&a|\bstake|buyout"),
    ("fund_raise", r"\bdebt|\bbonds?\b|\bncd|fund.?rais|borrowing|rating"),
    ("results", r"results|numbers|quarter|margins?|earnings"),
]
EXAMPLES = ["Who should I call about CEAT?", "Who knows the new MD of HDFC Bank?", "Brief me on Rinkoo Somani",
            "Who are my go-to people for specialty chemicals?", "Who should I reconnect with?", "Where am I blind?"]


# -- finding what the question is about ------------------------------------------------------------
def _entities(net, q):
    """The companies, themes and people a question names. A word claimed by a company name is not
    then read as a theme or a person: 'HDFC Bank' is not also 'banks'."""
    reg, ws = net.reg, None
    from .registry import words
    ws = words(q)
    orgs, taken = [], set()
    for i, j, org in reg._find(reg._org_names, ws):
        if not org.is_group and org not in orgs:
            orgs.append(org)
        taken |= set(range(i, j))
    for org in [o for o in reg.orgs.values() if not o.known]:       # a firm that appears only in someone's career
        name = words(org.name)
        for i in range(len(ws) - len(name) + 1):
            if name and ws[i:i + len(name)] == name and not taken & set(range(i, i + len(name))):
                orgs.append(org); taken |= set(range(i, i + len(name)))
    for tok in re.findall(r"\b[A-Z][A-Z0-9&]{2,}\b", q):            # a ticker typed as one
        if tok in reg.by_symbol and reg.by_symbol[tok] not in orgs:
            orgs.append(reg.by_symbol[tok])
    rest = [w for k, w in enumerate(ws) if k not in taken]
    themes = [h[2] for h in reg._find(reg._theme_names, rest)]
    folded = {names.fold(w) for w in rest}
    hits = []
    for p in [*net.filed, *net.contacts]:
        full = [names.fold(w) for w in names.tokens(p.name)[0]]
        n = sum(1 for w in full if w in folded)
        if n >= 2 or (n == 1 and any(w in folded and len(w) >= 4 for w in full)):
            hits.append((n, p))
    if any(n >= 2 for n, _ in hits):
        hits = [h for h in hits if h[0] >= 2]
    return orgs, list(dict.fromkeys(themes)), [p for _, p in hits]


def _by_role(net, q, orgs):
    """'the new MD of HDFC Bank' -> the people in that company's filings who hold that role."""
    ql = q.lower()
    for cue, pattern in ROLE:
        if re.search(cue, ql):
            found = [p for p in net.filed if p.company in orgs and re.search(pattern, p.event["role"].lower())]
            leaving = bool(re.search(r"\bold\b|former|outgoing|\bleft\b|leaving|previous|\bex\b", ql))
            side = [p for p in found if (p.change == "leaves") == leaving]
            return side or found
    return []


def _one_life(net, ppl):
    """Fold a contact into the filing person they are known to be, so one human is one candidate."""
    out = []
    for p in ppl:
        if p.kind == "contact" and any(net.known(f) is p for f in ppl if f.kind == "filing"):
            continue
        out.append(p)
    return out


# -- answers ---------------------------------------------------------------------------------------
def _ans(intent, title, lede, rows=(), notes=(), follow=(), **more):
    return {"intent": intent, "title": title, "lede": lede, "rows": list(rows), "notes": [n for n in notes if n],
            "follow": list(follow), **more}


def _crow(c, line, tag="", note=""):
    spoke = f"Last spoke {c['last']}." if c.get("last") else ""
    return {"name": c["name"], "sub": c["now"], "line": line, "tag": tag, "note": " ".join(x for x in (note, spoke) if x), "contact": c["id"]}


def _company(net, org, q=""):
    kind = next((k for k, cue in EVENT if re.search(cue, q.lower())), None)
    said = [w for w in re.findall(r"[a-z]{3,}", q.lower()) if w not in STOP] if kind else ()
    d = net.company(org.symbol or org.name, org.name, focus=FOCUS[kind] if kind else (), words=said)
    call = d["call"]
    rows = [_crow(r["contact"], r["line"], TAG[r["relation"]], r["caution"]) for r in call]
    notes = [d["exits"] and f"{org.name}: {d['exits']}"]
    follow = []
    for x in d["people"]:
        p = x["person"]
        if x["path"] and p["change"] != "leaves":
            notes.append(f"{p['name']}, {roles.short(p['role'])}: {x['path']['contact']['name']} knows them ({LINK[x['path']['label']]}).")
            follow.append(f"Who knows {p['name']}?")
        for i in x["identity"]:
            if i["status"] != "different":
                notes.append(f"{p['name']}, {roles.short(p['role'])}: {i['line']} {i['why']}")
    if org.themes:
        follow.append(f"Who are my go-to people for {org.themes[0]}?")
    if not call:
        return _ans("company", org.name, d["cover"], rows, notes, follow, symbol=org.symbol)
    top = call[0]
    lede = f"Start with {top['contact']['name']}. {top['line']}" + (f" {top['caution']}" if top["caution"] else "")
    return _ans("company", org.name, lede, rows, [d["cover"], *notes], follow[:3], symbol=org.symbol)


def _reach(net, p):
    r = net.reach(p, limit=5)
    title = f"{p.name}, {roles.short(p.event['role'])}, {p.company.name}"
    notes = [f"{i['line']} {i['why']}" for i in r["identity"] if i["status"] != "same"]
    notes += ["Ruled out: " + m + "." for m in r["near"]]
    rows = [_crow(x["contact"], x["line"], LINK[x["label"]]) for x in r["paths"]]
    follow = [f"Brief me on {p.name}"]
    known = net.known(p)
    if known:
        cv = net.contact_view(known)
        return _ans("reach", title, f"You know {p.name} yourself. " + (f"You last spoke in {cv['last']}." if cv["last"] else ""), [], notes, follow, person=p.id)
    prep = net.prep(p)
    if prep:
        # Where the person has a path, it is the answer: who was at the same places, and one question each.
        # Whether any of them worked alongside is not claimed, and nobody is "ruled out": the filing gives no years.
        who = prep["line"] or f"{_each(prep['pins'])} about {p.name}."
        lede = f"{who} The filing gives no years, so whether any of them worked alongside {p.name.split()[0]} is not known."
        return _ans("reach", title, lede, [], [n for n in notes if not n.startswith("Ruled out: ")], follow, person=p.id, preps=[prep])
    if r["you"]:
        return _ans("reach", title, r["you"]["line"], rows, notes, follow, person=p.id)
    if not rows:
        return _ans("reach", title, f"Nobody you know has worked or studied alongside {p.name}, as far as the records show.", [], notes, follow, person=p.id)
    best = r["paths"][0]
    lede = f"{best['contact']['name']} is your best route, {LINK[best['label']]}. {best['line']} {best['spoke']}".strip()
    if best["label"] == "weak":
        lede = f"No strong route. The nearest is {best['contact']['name']}. {best['line']}"
    return _ans("reach", title, lede, rows, notes, follow, person=p.id)


def _diligence(net, p):
    d = net.diligence(p)
    e = p.event
    verb = {"joins": "Joins", "moves": "Moves up at", "leaves": "Leaves"}[p.change]
    lede = (f"Stays at {p.company.name} as {e['role']}; off the senior management list from {e['effective']:%-d %b %Y}." if p.stays
            else f"{verb} {p.company.name} as {e['role']}, with effect from {e['effective']:%-d %b %Y}.")
    rows = [{"name": s["org"], "sub": s["years"], "line": s["role"], "tag": "now" if s["now"] else "", "note": "", "source": s["source"]} for s in d["path"]]
    notes = [f"{i['line']} {i['why']}" for i in d["identity"]]
    if d["you"] and not d["prep"]:                          # a path carries it in the room
        notes.append(d["you"]["line"])
    for x in [] if d["prep"] else d["paths"][:3]:          # where there is a path, it speaks for the person
        notes.append(f"{x['contact']['name']} ({LINK[x['label']]}): {x['line']}")
    if not d["paths"] and not d["you"] and not net.known(p) and not d["prep"]:
        notes.append("Nobody you know has worked alongside this person.")
    # Where there is a path, nobody is "ruled out" beside it: that rests on years no filing gives.
    notes += [] if d["prep"] else ["Ruled out: " + m + "." for m in d["near"]]
    notes.append(d["sources"])
    return _ans("diligence", f"{p.name}, {p.company.name}", lede, rows, notes, [f"Who knows {p.name}?", f"Who should I call about {p.company.name}?"],
                ask=[] if d["prep"] else d["ask"], edu=d["edu"], education=d["education"], person=p.id, url=e["url"], page=e["page"], quote=e["quote"],
                preps=[d["prep"]] if d["prep"] else [])


def _team(net, org):
    team = net.team(org.symbol)
    if not team:
        return _company(net, org)
    rows, asks = [], []
    for d in team:
        p = d["person"]
        route = d["paths"][0] if d["paths"] and d["paths"][0]["label"] != "weak" else None
        ident = next((i["line"] for i in d["identity"] if i["status"] != "different"), "")
        prep = d["prep"]
        line = ident or ((prep["line"] or f"{_each(prep['pins'])}.") if prep else
                         f"{route['contact']['name']} knows them: {route['line']}" if route else "Nobody you know can introduce you.")
        rows.append({"name": p["name"], "sub": p["role"], "line": line, "tag": {"joins": "new", "moves": "new role"}.get(p["change"], ""), "note": "", "person": p["id"]})
        asks += d["ask"]
    seen, uniq = set(), []
    for a in asks:
        if a["ask"] not in seen:
            seen.add(a["ask"]); uniq.append(a)
    lede = f"{len(team)} senior {'people have' if len(team) > 1 else 'person has'} a new seat at {org.name} in recent filings."
    # The path of each person across the table who has one, most senior first. What a path already puts
    # to a contact or to the room is not listed a second time.
    # Management before the board: a director's path is drawn only when no executive has one.
    rank = lambda d: {"top": 0, "senior": 1}.get(d["person"]["seniority"], 2)
    have = sorted((d for d in team if d["prep"]), key=rank)
    preps = [d["prep"] for d in have if rank(d) < 2 or rank(have[0]) == 2][:2]
    said = {a["ask"] for x in preps for a in x["room"]}
    covered = {x["person"]["id"] for x in preps}
    uniq = [a for d in team for a in d["ask"] if d["person"]["id"] not in covered and a["ask"] not in said and a in uniq]
    return _ans("team", f"Meeting {org.name}", lede, rows, [], [f"Who should I call about {org.name}?", *[f"Brief me on {r['name']}" for r in rows[:2]]],
                ask=uniq[:5], symbol=org.symbol, preps=preps)


def _expertise(net, theme):
    rows = net.expertise(theme)
    if not rows:
        return _ans("expertise", theme.capitalize(), f"Nobody you know has worked in {theme}.", follow=EXAMPLES[3:4])
    top = rows[0]
    lede = f"{top['contact']['name']} first. {top['line']}"
    return _ans("expertise", theme.capitalize(), lede,
                [_crow(r["contact"], r["line"], "there now" if r["current"] else "") for r in rows], theme=theme)


def _contact(net, c, symbols):
    b = net.contact_brief(c, symbols)
    cv = b["contact"]
    rows = [{"name": h["company"], "sub": TAG[h["relation"]], "line": h["line"], "tag": "", "note": h["caution"], "symbol": h["symbol"]} for h in b["helps"]]
    notes = [f"Knows {k['person']['name']} ({roles.short(k['person']['role'])}, {k['person']['company']}): {k['line']}" for k in b["knows"]]
    if b["themes"]:
        notes.append("Among your go-to people for " + _list(b["themes"]) + ".")
    spoke = f" You last spoke in {cv['last']}." if cv["last"] else ""
    if rows:
        lede = f"{cv['name']} can speak to {len(rows)} of your holdings.{spoke}"
    else:
        lede = f"{cv['name']} has no working link to your holdings.{spoke}"
    return _ans("contact", cv["name"], lede, rows, notes, contact=c.id, sub=cv["now"])


def _which(net, ppl):
    rows = []
    for p in ppl:
        if p.kind == "filing":
            notes = " ".join(i["line"] for i in net.identity_notes(p))
            rows.append({"name": p.name, "sub": f"{roles.short(p.event['role'])}, {p.company.name}", "line": "Named in a company filing." + (" " + notes if notes else ""),
                         "tag": "filing", "note": "", "ask": f"Brief me on {p.name} at {p.company.name}"})
        else:
            cv = net.contact_view(p)
            rows.append({"name": p.name, "sub": cv["now"], "line": "Someone you know.", "tag": "contact", "note": "", "ask": f"{p.name}, {p.career[-1].org.name}" if p.career else p.name})
    return _ans("which", "Which one?", f"{len(rows)} people fit that name. FINN won't pick for you.", rows)


def answer(net, q, symbols=()):
    """Answer one question, or say plainly that it can't be answered from the network."""
    q = (q or "").strip()[:300]
    ql = q.lower()
    orgs, themes, ppl = _entities(net, q)
    ppl = _by_role(net, q, orgs) or ppl
    if orgs and len(ppl) > 1:                 # 'Ajay Jain at CG Power' settles which Ajay Jain
        at = [p for p in ppl if (p.kind == "filing" and p.company in orgs) or (p.kind == "contact" and any(s.org in orgs for s in p.career))]
        ppl = at or ppl
    ppl = _one_life(net, ppl)
    if len(ppl) > 1:
        return _which(net, ppl)
    if ppl:
        p = ppl[0]
        if p.kind == "contact":
            return _contact(net, p, symbols)
        return _reach(net, p) if re.search(REACH, ql) else _diligence(net, p)
    for intent, cue in CUES:
        if re.search(cue, ql) and not (orgs or themes):
            if intent == "warm":
                rows = net.warm()
                return _ans("warm", "Worth a call", f"{len(rows)} people you haven't spoken to in a while, each with a fresh reason." if rows else "Nobody quiet has a fresh reason to call.",
                            [_crow(r["contact"], r["reason"], f"{r['quiet']} quiet") for r in rows])
            if intent == "gaps":
                cover = net.coverage(symbols)
                blind = [x for x in cover if x["level"] != "inside"]
                rows = [{"name": x["company"], "sub": "", "tag": "no one inside" if x["level"] == "outside" else "no one at all" if x["level"] == "none" else "going cold",
                         "line": (f"Best outside view: {x['best']['name']} ({TAG[x['best']['relation']]})." if x["level"] == "outside" else
                                  f"{x['best']['name']}, last spoken to in {x['best']['last']}." if x["best"] else "Nobody."), "note": "", "symbol": x["symbol"]}
                        for x in cover if x["level"] != "inside" or x["stale"]]
                return _ans("gaps", "Where you are blind", f"Nobody you know has worked inside {len(blind)} of your {len(cover)} holdings." if blind else
                            "Someone you know has worked inside every holding." + (f" At {len(rows)} of them, nobody inside has been spoken to in two years." if rows else ""), rows)
            rows = net.notices(symbols)
            return _ans("notices", "What the network noticed", f"{len(rows)} things from the last 30 days of filings.",
                        [{"name": n["contact"]["name"] if n["contact"] else "", "sub": n["kind"], "line": n["line"], "tag": n["symbol"], "note": n["why"]} for n in rows])
    if themes and (not orgs or re.search(THEME, ql)):
        return _expertise(net, themes[0])
    if orgs:
        return _team(net, orgs[0]) if re.search(TEAM, ql) else _company(net, orgs[0], q)
    m = re.search(r"\b(?:at|about|on|into|researching|call about)\s+((?:[A-Z][\w&.'-]*\s?)+)", q)
    if m:                                     # a company FINN has no record of: still look for it in every career
        return _company(net, net.org_for(m.group(1).strip(), m.group(1).strip()), q)
    return _ans("none", "Nothing found", "FINN couldn't place a company, a person or a theme in that question, so it has no answer rather than a guess.",
                follow=EXAMPLES)
