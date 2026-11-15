"""Organisations, schools and themes: turning the words in a filing or a profile into known things.

"Compliance Head - Credit, HDFC Bank Limited" is HDFC Bank, not HDFC Ltd. "L&T Finance" is not L&T.
"Indian Institute of Management, Bangalore" is IIM Bangalore. The longest known name in the text wins,
and whole words only, so "Citi" never matches inside "Citibank".
"""
import json, pathlib, re
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SUFFIX = {"ltd", "limited", "pvt", "private", "inc", "llp", "plc", "m/s"}


# words that may follow or lead a company's name without making it another company (words() has dropped Ltd and the like)
TRAILS = set("india company co the corporation corp group and of".split())


def words(text):
    text = text.lower().replace("&", " and ").replace("’", "'")
    text = re.sub(r"indian institute of management,?", "iim", text)
    text = re.sub(r"indian institute of technology,?", "iit", text)
    return [w for w in re.sub(r"[^a-z0-9/ ]", " ", text).split() if w not in SUFFIX]


@dataclass(eq=False)
class Org:
    id: str
    name: str
    scale: str = ""                 # tiny, small, mid, large, giant, or "" when not known
    themes: list = field(default_factory=list)
    also: list = field(default_factory=list)
    group: str = ""
    symbol: str = ""
    known: bool = True
    is_group: bool = False


class Registry:
    def __init__(self, path=None):
        d = json.loads(pathlib.Path(path or ROOT / "data" / "network" / "registry.json").read_text())
        self.orgs, self._org_names = {}, []
        for o in d["orgs"]:
            org = Org(o["id"], o["name"], o.get("scale", ""), o.get("themes", []), o.get("also", []),
                      o.get("group", ""), o.get("symbol", ""), True, o.get("is_group", False))
            self.orgs[org.id] = org
            for n in [o["name"], *o.get("aka", [])]:
                self._org_names.append((words(n), org))
        self.by_symbol = {o.symbol: o for o in self.orgs.values() if o.symbol}
        self.schools, self._school_names = {}, []
        for s in d["schools"]:
            self.schools[s["id"]] = s["name"]
            for n in [s["name"], *s.get("aka", [])]:
                self._school_names.append((words(n), s["id"]))
        self.themes = d["themes"]
        self._theme_names = [(words(n), t) for t, v in self.themes.items() for n in [t, *v["aka"]]]
        self.supplies = [(self.orgs[s["from"]], self.orgs[s["to"]], s["what"]) for s in d["supplies"]]

    # -- finding known names in text -------------------------------------------------------------
    @staticmethod
    def _find(names, text_words):
        """Every known name that appears as whole words, longest first, none overlapping a longer one."""
        hits, taken = [], set()
        for name, thing in sorted(names, key=lambda n: -len(n[0])):
            n = len(name)
            for i in range(len(text_words) - n + 1):
                if text_words[i:i + n] == name and not taken & set(range(i, i + n)):
                    taken |= set(range(i, i + n))
                    hits.append((i, i + n, thing))
        return sorted(hits, key=lambda h: h[0])

    def org(self, text):
        """The organisation a piece of text names. An unknown one still gets an Org, so two people
        at the same unlisted firm can be linked, but it carries no themes and no size."""
        tail = text.split(",")[-1]
        for part in (tail, text):
            hits = self._find(self._org_names, words(part))
            if hits:
                return max(hits, key=lambda h: h[1] - h[0])[2]
        name = re.sub(r"^M/s\.?\s*", "", tail.strip())
        key = "raw:" + " ".join(words(name))
        if key not in self.orgs:
            self.orgs[key] = Org(key, name, known=False)
        return self.orgs[key]

    def orgs_in(self, text):
        return [h[2] for h in self._find(self._org_names, words(text))]

    def schools_in(self, text):
        seen = []
        for h in self._find(self._school_names, words(text)):
            if h[2] not in seen:
                seen.append(h[2])
        return seen

    def themes_in(self, text):
        seen = []
        for h in self._find(self._theme_names, words(text)):
            if h[2] not in seen:
                seen.append(h[2])
        return seen

    def named(self, text):
        """As org(), for a filing's own words about a real person: a known name must be the whole of what
        the text names, give or take a company's suffix or a division. 'HDFC Life Insurance Company Limited'
        is not HDFC, and 'IDFC FIRST Bank' is not IDFC Limited: each stays as the filing wrote it, unknown."""
        org = self.org(text)
        if not org.known:
            return org
        for part in reversed(text.split(",")):
            ws = words(part)
            hits = self._find(self._org_names, ws)
            if hits:
                a, b, _ = max(hits, key=lambda h: h[1] - h[0])
                rest = ws[:a] + ws[b:]
                if all(w in TRAILS for w in rest) or (rest and rest[-1] in ("division", "business", "vertical") and a == 0):
                    return org
                name = re.sub(r"^M/s\.?\s*", "", part.strip())
                key = "raw:" + " ".join(ws)
                if key not in self.orgs:
                    self.orgs[key] = Org(key, name, known=False)
                return self.orgs[key]
        return org

    def stint_parts(self, text, exact=False):
        """'Officer, TCI Freight division' -> (TCI, 'Officer', 'Freight'). With exact, the name must be the whole of it."""
        org = self.named(text) if exact else self.org(text)
        role, division = "", ""
        if "," in text:
            role = text.rsplit(",", 1)[0].strip()
        m = re.search(r"(\w[\w &-]*?)\s+(?:division|business|vertical)\b", text.split(",")[-1], re.I)
        if m and org.known:
            left = [w for w in words(m.group(1)) if [w] not in [n for n, o in self._org_names if o is org]]
            division = " ".join(left).title()
        return org, role, division

    # -- themes ----------------------------------------------------------------------------------
    def within(self, theme, broader):
        """True when `theme` is `broader` or sits under it."""
        while theme:
            if theme == broader:
                return True
            theme = self.themes[theme]["in"]
        return False

    def stint_themes(self, org, role="", division=""):
        """The themes a job at this organisation speaks to. If the role names one of the organisation's
        lines of business ("Head of Motors Business" at CG Power), only that one counts; a side business
        counts only when the role names it."""
        named = self.themes_in(f"{role} {division}")
        own = org.themes + org.also
        cued = [t for t in own if any(self.within(t, n) or self.within(n, t) for n in named)]
        return cued or list(org.themes)

    # -- how two organisations stand to each other -----------------------------------------------
    def relation(self, a, b):
        """How organisation `a` stands to `b`: same, group, supplier (a sells to b), customer (a buys
        from b), competitor (they share a theme), or None. Returns (kind, detail)."""
        if a is b:
            return "same", ""
        for s, t, what in self.supplies:
            if s is a and t is b:
                return "supplier", what
            if s is b and t is a:
                return "customer", what
        if a.group and a.group == b.group:
            return "group", a.group
        shared = [t for t in a.themes if t in b.themes]
        if shared:
            return "competitor", shared[0]
        return None, ""
