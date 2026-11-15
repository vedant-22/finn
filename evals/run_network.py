"""Checks for the Network core. No model calls, no network access.  python3 evals/run_network.py

Seven groups, and an eighth for what the Network notices by joining: the path, patterns and one call. The one that matters most is identity: a wrong person match is worse than no match, so it is
tested from both sides. Every person in the filings is given an invented namesake who is somebody else
(must never be matched), and an invented true record under a differently written name (should be matched).
"""
import copy, datetime as dt, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finn.network import Network, ask, identity, links, names, people
from finn.network.engine import ASK, CAPTION, GOOD, PINS
from finn.network.registry import Registry

D = ROOT / "data" / "network"
read = lambda n: json.loads((D / n).read_text())
SLIM, INVESTOR = read("filings.json"), read("investor.json")
TODAY = dt.date.fromisoformat(SLIM["asof"][:10])
SYMS = list(SLIM["companies"])
results, lines = [], []


def build(investor=INVESTOR, decisions=None):
    return Network(SLIM["filings"], investor, Registry(D / "registry.json"), decisions, SLIM["companies"], TODAY)


def group(name, cases):
    """cases: (label, got, want). Records the score and lists every miss."""
    bad = [(l, g, w) for l, g, w in cases if g != w]
    results.append((name, len(cases) - len(bad), len(cases)))
    lines.append(f"{name}: {len(cases) - len(bad)}/{len(cases)}")
    lines.extend(f"   MISS {l}: got {g!r}, want {w!r}" for l, g, w in bad)


net = build()
reg = net.reg
S, C, X = names.SAME, names.COMPATIBLE, names.DIFFERENT

# 1. Names: can these two strings be one person?
NAMES = [
    ("Mr. S Ramkumar", "Ramkumar S", S), ("Sameer Anjaria", "Samir Kirit Anjaria", C), ("K. K. Maheshwari", "Kailash Kumar Maheshwari", C),
    ("Dr. C Jayakumar", "Jayakumar C", S), ("Vineet Taneja", "Mr. Vineet Taneja", S), ("Anup Bagchi", "Anup Kumar Bagchi", C),
    ("Rajat Shah", "Jigar Shah", X), ("Ajay Jain", "Deepak Jain", X), ("Ajay Jain", "Ajay Tandon", X), ("Suresh Kumar Narang", "Sumeet Narang", X),
    ("Sriraman T", "Sriraman V", X), ("V. N. Srivatsan", "Srivatsan V N", S), ("Venkateswaran L", "L Venkateswaran", S),
    ("Krishnamurthy R", "R Krishnamurthi", S), ("Vikram Sood", "Vikram Sud", S), ("Pooja Nanda", "Puja Nanda", S), ("Rohan D'Souza", "Rohan Dsouza", S),
    ("Kumar", "Subhendu Kumar", X), ("Subhendu Kumar", "Sanjay Kumar Chowdhary", X), ("Rahul Menon", "Rahul Mehta", X),
    ("A Jain", "Ajay Jain", C), ("A Jain", "Deepak Jain", X), ("Shweta Bansal", "Sweta Bansal", X), ("Meera Krishnan", "Mira Krishnan", S), ("Meera Krishnan", "Meena Krishnan", X),
    ("Sashidhar Jagdishan", "Sashidhar Jagdishan", S), ("Rabindra Purohit", "Rabinarayan Mishra", X), ("Priya Venkataraman", "Priya V", C),
    ("Smt. Sunita Raghunathan", "Sunita R.", C), ("Gautam Doshi", "Gautam Joshi", X), ("Nitin Agarwal", "Pankaj Agarwal", X),
]
group("names", [(f"{a} / {b}", names.compare(a, b), w) for a, b, w in NAMES])

# 2. Organisations and schools: the words in a filing, resolved
ORGS = [
    ("Compliance Head - Credit, Asset Product & Regulatory Reporting, HDFC Bank Limited", "hdfcbank"), ("Regional Credit Head, HDFC Ltd", "hdfc"),
    ("HDFC Asset Management Company", "hdfcamc"), ("Head of Treasury, L&T Finance", "ltfinance"), ("Graduate Engineer Trainee, L&T", "lt"),
    ("L&T Technology Services", "ltts"), ("Crompton Greaves Consumer Electricals Ltd", "crompton"), ("Crompton Greaves", "cgpower"),
    ("CG Power and Industrial Solutions Limited", "cgpower"), ("Various functions, Citigroup India", "citi"), ("ICICI Prudential Life Insurance", "icicipru"),
    ("Executive Director, ICICI Bank", "icicibank"), ("CEO & MD, ICICI Securities", "icicisec"), ("ICICI Lombard", "icicilombard"),
    ("Vice President of Sales and Marketing for the Foods and Beverages, Unilever", "unilever"), ("Brand Manager, Hindustan Unilever", "hul"),
    ("Sr. Vice President & Head HR, Avaada Manufacturing", "avaada"), ("Retail Head, North, Tanishq", "titan"), ("Officer, TCI Freight division", "tci"),
    ("Deepak Fertilisers and Petrochemicals Corporation Ltd", "deepakfert"), ("Kotak Institutional Equities", "kie"), ("Kotak Mahindra Bank", "kotakbank"),
    ("M/s. A.B.Ankhad & Associates", "raw:a b ankhad and associates"), ("Head - Legal, Compliance & Company Secretary, NIVEA India", "nivea"),
]
group("organisations", [(t, reg.org(t).id, w) for t, w in ORGS])
SCHOOLS = [("Management degree from Indian Institute of Management, Bangalore and Engineering degree from Indian Institute of Technology, Kanpur", ["iimb", "iitk"]),
           ("MBA from Harvard Business School, Masters in management from IIM Lucknow, Bachelors from IIT Roorkee", ["hbs", "iiml", "iitr"]),
           ("PGDBA in Marketing from NMIMS Mumbai", ["nmims"]), ("Chartered Accountant", []), ("Post Graduate degree in Business Administration from PSG College of Technology", ["psg"])]
group("schools", [(t[:50], reg.schools_in(t), w) for t, w in SCHOOLS])

# 3. Identity, on the demo's own traps
verdict = lambda pid, cid: next((v.status for c, v in net.verdicts.get(pid, []) if c.id == cid), None)
TRAPS = [("rajat-shah@CGPOWER", "rajat-shah", "same"), ("ajay-jain@CGPOWER", "ajay-jain", "different"), ("deepak-jain@SYNGENE", "deepak-jain", "different"),
         ("ramkumar-s@LT", "ramkumar-s", "different"), ("jigar-shah@HDFCBANK", "jigar-shah", "possible"), ("ajay-tandon@SYNGENE", "ajay-jain", None),
         ("suresh-kumar-narang@LT", "suresh-babu", None)]
cases = [(f"{p} vs {c}", verdict(p, c), w) for p, c, w in TRAPS]
said = build(decisions={"jigar-shah@HDFCBANK|jigar-shah": "same", "ajay-jain@CGPOWER|ajay-jain": "same"})
cases += [("the investor can settle a 'possible'", next(v.status for c, v in said.verdicts["jigar-shah@HDFCBANK"]), "same"),
          ("the investor cannot overrule a contradiction", next(v.status for c, v in said.verdicts["ajay-jain@CGPOWER"]), "different")]
group("identity: demo traps", cases)

# 4. Identity, adversarial. Every filing person gets (a) a namesake who is someone else and (b) a true record.
STRANGER = [["Infosys BPM", "Delivery Manager", 2009, None]]
false_same, true_same, true_n, undecided = [], 0, 0, 0
for p in net.filed:
    inv = copy.deepcopy(INVESTOR)
    inv["contacts"] = [{"id": "x", "name": p.name, "how": "met", "since": 2015, "met": ["2025-01-01"], "career": STRANGER, "edu": []}]
    # ... and a namesake who shares only a very large employer with the filing person
    inv["contacts"].append({"id": "y", "name": p.name, "how": "met", "since": 2015, "met": ["2025-01-01"],
                            "career": [["Larsen & Toubro", "Engineer", 2001, 2006], ["ICICI Bank", "Manager", 2006, 2010], ["Infosys BPM", "Delivery Manager", 2010, None]], "edu": []})
    alt = build(inv)
    q = next(x for x in alt.filed if x.id == p.id)
    for c, v in alt.verdicts.get(q.id, []):
        if v.status == "same":
            false_same.append(f"{p.name} ({c.id})")
    # (b) the same life, written the way a contact list writes it: surname first, given names as initials
    past = [s for s in p.career if s.org is not p.company and s.org.known]
    if past and p.change == "joins":
        full, _ = names.tokens(p.name)
        alias = f"{full[-1].title()} {' '.join(w[0].upper() for w in full[:-1])}" if len(full) > 1 else p.name
        career = [[s.org.name, s.role or "Manager", 2005 + 3 * i, 2008 + 3 * i] for i, s in enumerate(past)]
        inv = copy.deepcopy(INVESTOR)
        inv["contacts"] = [{"id": "t", "name": alias, "how": "met", "since": 2015, "met": ["2025-01-01"], "asof": "2026-06-30", "career": career, "edu": []}]
        alt = build(inv)
        got = [v.status for c, v in alt.verdicts.get(p.id, [])]
        true_n += 1
        true_same += got == ["same"]
        undecided += got == ["possible"]
group("identity: invented namesakes are never matched", [(f"{len(net.filed) * 2} namesakes, false matches", false_same, [])])
lines.append(f"identity: invented true records matched: {true_same}/{true_n} ({undecided} left as 'possible', none refused wrongly: {true_same + undecided == true_n})")
results.append(("identity: true records are not called different", int(true_same + undecided == true_n), 1))

# 5. Links: years must overlap; groups are not employers
St = people.Stint
org = reg.orgs["crompton"]
OV = [((2010, 2015, False), (2013, 2020, False), 2), ((2010, 2015, False), (2015, 2020, False), 0.5), ((2010, 2014, False), (2016, 2020, False), 0),
      ((None, 2026, False), (2022, None, True), 1), ((None, None, False), (2012, 2019, False), None), ((2019, None, True), (2021, None, True), 5),
      ((None, 2019, False), (2021, None, True), 0)]
group("links: overlap in years", [(f"{a} & {b}", links.overlap(St(org, "", a[0], a[1], a[2]), St(org, "", b[0], b[1], b[2]), 2026), w) for a, b, w in OV])
cases = []
for p in net.filed:
    for c in net.contacts:
        link, _ = links.between(c, p, net.year)
        if link and link.kind in ("worked", "board") and link.dated:
            shared = [(s, t) for s in c.career for t in p.career if s.org is t.org and s.org.name == link.where and links.overlap(s, t, net.year)]
            cases.append((f"{c.name} - {p.name}", bool(shared), True))
by = {c.id: c for c in net.contacts}
ram, lt_new = by["ramkumar-s"], next(p for p in net.filed if p.id == "suresh-kumar-narang@LT")
cases.append(("L&T Finance and L&T are one group, two employers: no link", links.between(ram, lt_new, net.year)[0], None))
sanjay, bagchi = by["sanjay-bhatia"], next(p for p in net.filed if p.id == "anup-bagchi@HDFCBANK")
# The filing gives Anup Bagchi's earlier jobs and schools no years, so a shared employer or school is kept, undated and said so
und = lambda a: (lambda l: (l.label, l.dated, l.basis))(links.between(a, bagchi, net.year)[0])
cases.append(("Sanjay Bhatia - Anup Bagchi: a fair link, undated", und(sanjay),
              ("good", False, "were both at ICICI Securities; the filing gives no years for Anup, so whether they overlapped is not known")))
cases.append(("Meera Krishnan - Anup Bagchi at ICICI Bank: weak and undated, never a dated miss", und(by["meera-krishnan"])[:2], ("weak", False)))
cases.append(("investor and Bagchi: the same school, years not known", und(net.me), ("weak", False, "both studied at IIM Bangalore; years not known")))
group("links: every dated link rests on overlapping years", cases)

# 6. Who to call, events, and what must stay silent
top = lambda sym, **k: (net.who_to_call(reg.by_symbol[sym], **k) or [{"contact": {"id": None}}])[0]["contact"]["id"]
CALL = [("CGPOWER", "rajat-shah"), ("SYNGENE", "leena-joshi"), ("MARUTI", "ramesh-iyer"), ("HOMEFIRST", "kavita-deshmukh"), ("CYIENT", "aditya-kamat"),
        ("BLUEDART", "mohit-arora"), ("ERIS", "rohit-bhargava"), ("ULTRACEMCO", "girish-kulkarni"), ("HDFCBANK", "rahul-menon"), ("TITAN", "ritu-chawla"),
        ("DCMSHRIRAM", "harsh-singh"), ("CROMPTON", "shweta-bansal"), ("KFINTECH", "neha-saxena"), ("CEATLTD", "sneha-kapoor")]
cases = [(f"first call for {s}", top(s), w) for s, w in CALL]
ev = lambda sym, cat, word: next(f for f in SLIM["filings"] if f["symbol"] == sym and f["category"] == cat and word in f.get("line", ""))
first = lambda f: (net.for_event(f) or [{"contact": {"id": None}}])[0]["contact"]["id"]
cases += [("SRF tax notice -> the former head of taxation", first(ev("SRF", "litigation", "input tax")), "pooja-nanda"),
          ("SRF 600 crore project -> the former head of projects", first(ev("SRF", "capex", "600")), "vikram-sood"),
          ("Sun Pharma bond issue -> nobody is well placed", first(ev("SUNPHARMA", "fund_raise", "debentures")), None),
          ("Maruti tax order -> a purchasing head is not the person", first(ev("MARUTI", "litigation", "Appellate")), None),
          ("Crompton consumer-court refund (immaterial) -> nothing", first(ev("CROMPTON", "litigation", "Consumer commission")), None)]
outsiders = {"kiran-shetty", "nandini-kelkar", "vivek-rathore", "rohan-dsouza"}       # friends and family with no bearing on any holding
seen = {r["contact"]["id"] for s in SYMS for r in net.who_to_call(reg.by_symbol[s], limit=99)}
pushed = [x for b in map(net.for_filing, SLIM["filings"]) if b for pp in b.get("people", []) for x in pp["paths"]]
cases += [("friends and family never offered as a source", sorted(seen & outsiders), []),
          ("nothing weaker than a fair link is pushed", all(x["strength"] >= GOOD for x in pushed), True),
          ("every notice carries its evidence", all(n["why"] for n in net.notices(SYMS)), True),
          ("same inputs, same output", json.dumps(build().notices(SYMS), default=str) == json.dumps(net.notices(SYMS), default=str), True),
          ("rural lending: a housing-finance credit head is not an expert", "kavita-deshmukh" in {r["contact"]["id"] for r in net.expertise("rural lending")}, False),
          ("semiconductors -> the one person who has made chips", [r["contact"]["id"] for r in net.expertise("semiconductors")], ["priya-venkataraman"]),
          # Syngene filed four "ceased" in four days, but two were "Changed from SMP to Non-SMP category": still in the job
          ("Syngene: two moved off the senior list stay, and are not counted as exits", sorted(q.name for q in net.exits("SYNGENE")), ["Ajay Tandon", "Deepak Jain"]),
          ("... each stays at Syngene, with a current stint", sorted(q.name for q in net.filed if q.symbol == "SYNGENE" and q.stays
                                                                     and any(s.org is q.company and s.current for s in q.career)), ["Priyaranjan Pattanaik", "Subhendu Kumar"]),
          ("a single exit is not a pattern", any(n["kind"] == "exits" and n["symbol"] == "HAVELLS" for n in net.notices(SYMS, limit=99)), False)]
group("who to call, events, silence", cases)

# 7. Questions
QS = [("Who should I call about CEAT?", "company", "Sneha Kapoor"), ("Who knows the new MD of HDFC Bank?", "reach", "Sanjay Bhatia"),
      ("how do I reach Anup Bagchi", "reach", "Sanjay Bhatia"), ("Brief me on Rinkoo Somani", "diligence", "IDFC Limited"),
      ("Before I meet the Home First CFO", "diligence", "IDFC Limited"), ("Who are my go-to people for specialty chemicals?", "expertise", "Dr. Anjali Rao"),
      ("who knows about rural lending", "expertise", "Suresh Babu"), ("semiconductors", "expertise", "Priya Venkataraman"),
      ("I'm researching tyres", "expertise", "Sneha Kapoor"), ("Who should I reconnect with?", "warm", None), ("Where am I blind?", "gaps", "Maruti Suzuki"),
      ("Who knows Ajay Jain?", "which", None), ("Ajay Jain at CG Power", "diligence", "CG Power"), ("Ajay Jain, Deloitte", "contact", None),
      ("Jigar Shah", "which", None), ("Shah", "which", None), ("Rajat Shah", "diligence", "Siemens India"), ("what can Vikram Sood tell me", "contact", "SRF"),
      ("I'm meeting HDFC Bank management next week", "team", None), ("who do I know at Zomato", "company", None), ("what's the weather in Mumbai", "none", None),
      ("Who should I call about SRF's tax notice?", "company", "Pooja Nanda"), ("who can explain the CG Power capex plan", "company", "Rajat Shah"),
      ("who knows the old CEO of HDFC bank", "reach", "Rahul Menon"), ("Titan", "company", "Ritu Chawla"), ("what did you notice", "notices", "Rajat Shah"),
      ("Who do I know at Loadline Logistics?", "company", "Pankaj Agarwal"), ("who do I know at HDFC Bank", "company", "Rahul Menon"),
      ("tell me about Bagchi", "diligence", "ICICI Prudential Life Insurance"), ("S Ramkumar at L&T", "diligence", "Larsen & Toubro"), ("", "none", None),
      ("who knows Sumeet Narang", "reach", "Aman Khurana"), ("CEATLTD", "company", "Sneha Kapoor"), ("who covers cement for me", "expertise", "Varun Khanna")]
cases = []
for q, intent, firstrow in QS:
    a = ask.answer(net, q, SYMS)
    cases.append((f"{q!r} is a {intent} question", a["intent"], intent))
    if firstrow:
        on_path = [r["pin"]["contact"]["name"] for d in a.get("preps", []) for r in d["stations"] if r["pin"] and r["pin"]["ask"]]
        cases.append((f"{q!r} leads with", a["rows"][0]["name"] if a["rows"] else firstrow if firstrow in on_path else None, firstrow))
group("questions", cases)

# 8. The path, patterns across filings, and one call for two answers. A real person carries only what a filing says.
import inspect, re
fp = lambda n, pid: next(p for p in n.filed if p.id == pid)
flat = lambda d: [(r["kind"], r.get("line") or r["org"], r["role"], r["when"],
                   *((r["pin"]["ask"], r["pin"]["contact"]["name"], r["pin"]["tag"], r["pin"]["basis"]) if r["pin"] else ())) for r in d["stations"]]
home = net.prep(fp(net, "rinkoo-somani@HOMEFIRST"))
HOME = [("seat", "Home First Finance", "Chief Financial Officer", "filed 27 Oct",
         "Where did risk and finance pull against each other at Home First Finance?", "Kavita Deshmukh", "Worked here", "Chief Risk Officer, 2014–2020"),
        ("listed", "IDFC Limited", "Interim CFO", "",
         "Were you at IDFC Limited with Rinkoo Somani, and what did treasury need from the CFO?", "Nitin Agarwal", "Worked there", "Head of Treasury, 2012–2019"),
        ("listed", "Dani family office", "Group CFO", "",
         "What is Rinkoo Somani remembered for at the Dani family office?", "Gaurav Sinha", "Works there now", "Chief Investment Officer"),
        ("gap", "No housing finance employer in the filing", "", "",
         "What catches a new CFO out in housing finance?", "Meera Krishnan", "Same seat, a competitor", "Chief Financial Officer, Aavas Financiers")]
cases = [("Home First's new CFO: the path, station by station", flat(home), HOME),
         ("... in the room", [a["ask"] for a in home["room"]], ["What was the interim brief at IDFC Limited?"]),
         ("... the Today card's line counts the stations, not the gap", home["line"], "Three people you know have worked where Rinkoo Somani works or has worked."),
         ("... the caption says whose the path is", home["caption"], CAPTION),
         ("... the call sheet names each person and puts each question", all(x in home["sheet"] for r in HOME for x in (r[4], r[5])) and "In the room" in home["sheet"], True)]
# Every path that shows, with the exact question at its seat
shown = {p.id: d for p in net.filed if (d := net.prep(p))}
SEATS = {"rinkoo-somani@HOMEFIRST": "Where did risk and finance pull against each other at Home First Finance?",
         "vineet-taneja@HOMEFIRST": "What should a new independent director at Home First Finance ask about first?",
         "sumeet-narang@CEATLTD": "What should a new independent director at CEAT ask about first?",
         "yudhishter-shringi@HAVELLS": "What should a new SBU Head at Havells fix first?",
         "anup-bagchi@HDFCBANK": ""}
cases += [("the paths that show", sorted(shown), sorted(SEATS))]
cases += [(f"seat question: {pid}", (shown[pid]["stations"][0]["pin"] or {}).get("ask") if pid in shown else None, want) for pid, want in SEATS.items()]
bagchi_path = shown.get("anup-bagchi@HDFCBANK", {"stations": [], "room": []})
cases += [("HDFC Bank's new MD: one path, from the filing that lists employers", [r["org"] for r in bagchi_path["stations"]],
           ["HDFC Bank", "ICICI Prudential Life Insurance", "ICICI Bank", "ICICI Securities"]),
          ("... someone inside is named, with the caution, and not asked", [(r["pin"]["contact"]["name"], r["pin"]["tag"], r["pin"]["ask"], bool(r["pin"]["caution"])) for r in bagchi_path["stations"][:1]],
           [("Rahul Menon", "You know", "", True)]),
          ("... the predecessor question is for the room", [a["ask"] for a in bagchi_path["room"]], ["What is Anup expected to do differently from Sashidhar Jagdishan?"]),
          ("... a contact who was at a listed employer is asked what they can know, not for a referral", [r["pin"]["ask"] for r in bagchi_path["stations"][2:] if r["pin"]],
           ["Were you at ICICI Bank with Anup Bagchi, and what is Anup remembered for there?", "Were you at ICICI Securities with Anup Bagchi, and what is Anup remembered for there?"]),
          ("Havells: no employer in the trade and nobody in the same seat, so the room's question names what the filing lists, and claims no 'never'",
           [a["ask"] for a in shown.get("yudhishter-shringi@HAVELLS", {"room": []})["room"]], ["What carries over from Compass Group India and Britannia Industries to consumer electricals?"])]
# Result review round 2: "the same seat" is the line of work and the rank
junior = build(investor={**INVESTOR, "contacts": [c for c in INVESTOR["contacts"] if c["id"] != "meera-krishnan"] +
                         [{"id": "fx-junior", "name": "Junia Fixture", "how": "met", "since": 2015, "met": ["2026-09-01"], "career": [["Aavas Financiers", "Assistant Manager, Finance", 2020, None]], "edu": []}]})
cases += [("fixture: an assistant manager in finance at a competitor does not hold 'the same seat' as a new CFO",
           [x["contact"]["name"] for x in [r["pin"] for r in junior.prep(fp(junior, "rinkoo-somani@HOMEFIRST"), least=0)["stations"] if r["pin"]] if x["kind"] == "gap"], [])]
# Asked directly, a person with a path is answered by the path: nobody "overlapped", nobody "ruled out", on years no filing gives
direct = {pid: ask.answer(net, f"Who knows {d['person']['name']}?", SYMS) for pid, d in shown.items()}
cases += [("'Who knows …?' for a person with a path: the path, and no row beside it", [(a["intent"], len(a["rows"]), [d["person"]["id"] for d in a.get("preps", [])]) for a in direct.values()],
           [("reach", 0, [pid]) for pid in direct]),
          ("... it says the filing gives no years, and neither 'overlapped' nor 'Ruled out'",
           [("The filing gives no years" in a["lede"], bool(re.search(r"overlapped|Ruled out|different years", json.dumps(a)))) for a in direct.values()], [(True, False)] * len(direct))]
# Invariants over every person in a filing, whether or not the path is long enough to show
every = {p.id: (p, net.prep(p, least=0)) for p in net.filed}
paths = [(p, d) for p, d in every.values() if d]
pins = lambda d: [r["pin"] for r in d["stations"] if r["pin"]]
asked = lambda d: [x for x in pins(d) if x["ask"]]
said = lambda d: [x["ask"] for x in pins(d) if x["ask"]] + [a["ask"] for a in d["room"]] + [d["line"]] + [r.get("line", "") for r in d["stations"]]
TEMPLATES = [re.compile("^" + re.sub(r"\\\{\w+\\\}", ".+", re.escape(t)) + "$") for t in ASK.values()]
PRONOUN = re.compile(r"\b(he|she|him|her|his|hers|they|them|their|theirs)\b", re.I)
BANNED = re.compile(r"flag|suspicious|fled|purge|exodus|quietly", re.I)
inside_now = lambda c_id, p: any(s.org is p.company and s.current for s in net.by_id[c_id].career)
cases += [("nobody leaving has a path", [p.id for p, d in every.values() if p.change == "leaves" and d], []),
          ("a contact is never pinned on their own path (Rajat Shah)", every["rajat-shah@CGPOWER"][1], None),
          (f"at most {PINS} people are asked on a path", [p.id for p, d in paths if len(asked(d)) > PINS], []),
          ("a contact appears once on a path", [p.id for p, d in paths if len({x["contact"]["id"] for x in pins(d)}) != len(pins(d))], []),
          ("a pin carries one question, from the table", [x["ask"] for p, d in paths for x in asked(d) if x["ask"].count("?") != 1 or not any(t.match(x["ask"]) for t in TEMPLATES)], []),
          ("a question for the room is from the table or the predecessor rule", [a["ask"] for p, d in paths for a in d["room"]
                                                                              if not any(t.match(a["ask"]) for t in TEMPLATES) and "expected to do differently from" not in a["ask"]], []),
          ("someone inside the company now is never asked", [(p.id, x["contact"]["name"]) for p, d in paths for x in asked(d) if inside_now(x["contact"]["id"], p)], []),
          ("no year stands on a filing person's station", [p.id for p, d in paths for r in d["stations"] if re.search(r"\b(19|20)\d\d\b", f"{r['org']} {r['role']} {r['when']} {r.get('line', '')}")], []),
          ("no pronoun in anything the path says", [t for p, d in paths for t in said(d) if PRONOUN.search(t)], []),
          ("no word of suspicion", [t for p, d in paths for t in said(d) if BANNED.search(t)], []),
          ("an employer the registry doesn't know is a bare station", [r["pin"] for r in every["tushar-gunderia@BLUEDART"][1]["stations"] if r["org"].startswith("A.B.Ankhad")], [None]),
          ("a namesake is not pinned by the name (Jigar Shah)", "jigar-shah" in {x["contact"]["id"] for x in pins(every["jigar-shah@HDFCBANK"][1])}, False)]
# Filed fields only (network-loop): the demo's invented profiles are gone, and the code that attached them
strangers = [p for p in net.filed if not net.known(p)]
earlier = lambda p: [x for x in net.reach(p, limit=99)["paths"] if x["where"] != p.company.name]
vineet = [b for f in SLIM["filings"] if (b := net.for_filing(f)) and any(x["person"]["id"] == "vineet-taneja@HOMEFIRST" for x in b.get("people", []))]
mine = "You and Anup both studied at IIM Bangalore; years not known."
cases += [("the loader takes no profiles, and there is no profile file", ("profiles" in inspect.signature(Network).parameters, (D / "profiles.json").exists(),
                                                                         hasattr(identity, "attach_profile"), hasattr(people, "profile")), (False, False, False, False)),
          (f"no earlier job of a filing person carries a year ({len(strangers)} people)", [(p.id, s.org.name) for p in strangers for s in p.career
                                                                                        if s.org is not p.company and (s.start or s.end or s.years())], []),
          ("no link through an earlier employer is dated or says two people overlapped", [(p.id, x["line"]) for p in strangers for x in earlier(p)
                                                                                         if x["dated"] or re.search(r"overlapped at|same batch", x["line"])], []),
          ("... nor the investor's own line", [(p.id, y["line"]) for p in strangers if (y := net.reach(p)["you"]) and re.search(r"overlapped at|same batch|\b(19|20)\d\d\b", y["line"])], []),
          ("a path qualifies a person on its own: Vineet Taneja's is on both of his filings' cards", [bool(x["prep"]) for b in vineet for x in b["people"] if x["person"]["id"] == "vineet-taneja@HOMEFIRST"], [True, True]),
          ("the investor's own line is on the HDFC Bank path, under In the room", (bagchi_path.get("you"), mine in bagchi_path.get("sheet", "").split("In the room")[-1]), (mine, True)),
          ("... said once in the meeting answer: on the path, not again in the notes",
           [mine in n for n in ask.answer(net, "Brief me on Anup Bagchi at HDFC Bank", SYMS)["notes"]], [False] * len(ask.answer(net, "Brief me on Anup Bagchi at HDFC Bank", SYMS)["notes"])),
          ("a brief names the profile the company filed, and a departure says it has none",
           (net.diligence(fp(net, "rinkoo-somani@HOMEFIRST"))["sources"], net.diligence(fp(net, "deepak-jain@SYNGENE"))["sources"]),
           ("The role and earlier employers are from the brief profile the company filed with the appointment, in its order and with no years.",
            "The role is from the company's filing, which gives no years.")),
          ("... and the filing's own order of employers is what is kept", [o.name for o, _ in fp(net, "rinkoo-somani@HOMEFIRST").listed], ["IDFC Limited", "Dani family office"])]
# Where the path shows
brief, who = ask.answer(net, "Brief me before I meet Home First", SYMS), ask.answer(net, "Who is Rinkoo Somani?", SYMS)
block = net.for_filing(next(f for f in SLIM["filings"] if f["symbol"] == "HOMEFIRST" and f["tier"] == "act"))
cases += [("'Brief me before I meet Home First' answers with the path", (brief["intent"], brief.get("preps")), ("team", [home])),
          ("'Who is Rinkoo Somani?' answers with the same path", who.get("preps"), [home]),
          ("... and does not also rule out the person it asks", [n for n in who["notes"] if n.startswith("Ruled out: Nitin")], []),
          ("... nor list a second time what the path already asks", who["ask"], []),
          ("the Home First card carries the path", [x["prep"] == home for x in block["people"] if x["person"]["id"] == "rinkoo-somani@HOMEFIRST"], [True]),
          ("Pull knows who is new in a seat with a path", [x["person"]["name"] for x in net.company("HOMEFIRST")["people"] if x["prep"]], ["Rinkoo Somani", "Vineet Taneja"])]

# Control seats: two filings, each too small to show, read together. Counted over every company, not only the demo's.
def refiled(edit=None, extra=(), investor=INVESTOR):
    """The network again, from the same filings with one thing changed."""
    filings = copy.deepcopy(SLIM["filings"])
    for f in filings:
        for rec in f.get("people") or []:
            if edit:
                edit(f, rec)
    return Network(filings + list(extra), investor, Registry(D / "registry.json"), None, SLIM["companies"], TODAY)

def gandani(**change):
    return lambda f, rec: rec.update(change) if rec["name"] == "Yesha Gandani" else None

pats = {s: net.patterns(s) for s in SYMS}
fired = [s for s in SYMS if pats[s]]
crom = (pats["CROMPTON"] or [{}])[0]
LINE_OK = re.compile(r"^[A-Z][\w &'.-]+: (within \w+ days|on the same day), (the .+? (moved to another role in the company|resigned|left the seat)(, | and |\.$))+$")
MONTH = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")
GENDERED = re.compile(r"\b(he|she|him|her|his|hers)\b", re.I)
reasons = {p.id: p.event["reason"] for p in net.filed}
cases += [("control seats fires at one company of 18", fired, ["CROMPTON"]),
          ("... HDFC Bank's two are the calendar's, by their own stated reasons", (pats["HDFCBANK"], sorted(reasons[i] for i in ("rakesh-kumar-rajput@HDFCBANK", "sudhir-kumar-jha@HDFCBANK"))), ([], ["Tenure completed", "superannuation"])),
          ("... the line", crom.get("line"), "Crompton: within two days, the Head of Internal Audit, Risk & Control moved to another role in the company and the Compliance Officer resigned."),
          ("... each filed reason is in the evidence word for word, the internal move too", [r in crom.get("why", "") for r in ("Reason filed: Transitioning to a new role within the Company.", "Reason filed: personal reasons.")], [True, True]),
          ("... each name, title and date is in the evidence", [x in crom.get("why", "") for x in ("Nikhil Thakkar, Head – Internal Audit, Risk & Control, ceased on 15 Oct.", "Yesha Gandani, Compliance Officer, resigned on 16 Oct.")], [True, True]),
          ("... 'no successor' is said because none is filed", "No successor is filed for either." in crom.get("why", ""), True),
          ("... and that Push folded one of them read alone", "Read alone, the Compliance Officer's filing was folded as routine." in crom.get("why", ""), True),
          ("... one person in two filings is one seat (Yesha Gandani)", crom.get("people"), ["nikhil-thakkar@CROMPTON", "yesha-gandani@CROMPTON"]),
          ("... who to ask: a finance head at a competitor, and what only that seat sees", (crom.get("pin") or {}).get("contact", {}).get("name"), "Nitin Agarwal"),
          ("... the question tests the pattern from the contact's own seat, and says nothing of the people who left", (crom.get("pin") or {}).get("ask"), "How long does it usually take to fill audit and compliance seats in consumer electricals?"),
          ("... for the next call", crom.get("next"), "Who holds audit and compliance at Crompton now, and who do they report to?"),
          ("a pattern's line holds the company, a span of days, filed titles and what each filing says happened, and nothing else",
           [p["line"] for ps in pats.values() for p in ps if not LINE_OK.match(p["line"]) or MONTH.search(p["line"]) or GENDERED.search(p["line"]) or BANNED.search(p["line"])], []),
           ("a pattern's evidence has no results date and no word of suspicion", [p["why"] for ps in pats.values() for p in ps if re.search(r"results|profit|revenue", p["why"], re.I) or BANNED.search(p["why"])], []),
          ("nobody inside the company now is a pattern's person to ask", [p["pin"]["contact"]["name"] for s, ps in pats.items() for p in ps if p["pin"] and inside_now(p["pin"]["contact"]["id"], fp(net, p["people"][0]))], []),
          ("the Network's fold carries it, with the person and the question", [(n["contact"]["name"], "How long does it usually take to fill audit and compliance seats in consumer electricals?" in n["why"]) for n in net.notices(SYMS, limit=99) if n["kind"] == "seats"], [("Nitin Agarwal", True)]),
          ("Pull carries it on the company", [p["kind"] for p in net.company("CROMPTON")["patterns"]], ["seats"])]
# Fixtures: the same filings with one thing changed
successor = {"id": "fixture-1", "symbol": "CROMPTON", "at": "2026-10-20T10:00:00", "url": "", "category": "management_change", "tier": "note", "line": "",
             "people": [{"name": "Asha Raman", "role": "Compliance Officer", "action": "appointed", "seniority": "other", "effective": "October 20, 2026", "reason": "", "previous": [], "verified": True}]}
no_finance = {**INVESTOR, "contacts": [c for c in INVESTOR["contacts"] if c["id"] != "nitin-agarwal"]}
alone = refiled(investor=no_finance).patterns("CROMPTON")
cases += [("fixture: 30 days apart still counts", len(refiled(gandani(effective="November 14, 2026")).patterns("CROMPTON")), 1),
          ("fixture: 31 days apart is silent", refiled(gandani(effective="November 15, 2026")).patterns("CROMPTON"), []),
          ("fixture: a reason of superannuation is silent", refiled(gandani(reason="superannuation")).patterns("CROMPTON"), []),
          ("fixture: one person in two filings, and nobody else, is silent", refiled(lambda f, rec: rec.update(verified=False) if rec["name"] == "Nikhil Thakkar" else None).patterns("CROMPTON"), []),
          ("fixture: with a successor filed, 'no successor' is not said", ["No successor" in p["why"] for p in refiled(extra=[successor]).patterns("CROMPTON")], [False]),
          ("fixture: when nobody fits, it says so and names no one", [(p["pin"], bool(p["none"])) for p in alone], [(None, True)])]
# Fixtures from the result review (14 Nov): each broke the first build
def filing(i, sym, name, role, action, when, reason="", previous=()):
    return {"id": f"fixture-{i}", "symbol": sym, "at": dt.datetime.strptime(when, "%B %d, %Y").strftime("%Y-%m-%dT10:00:00"), "url": "", "category": "management_change",
            "tier": "note", "line": "", "people": [{"name": name, "role": role, "action": action, "seniority": "senior", "effective": when, "reason": reason,
                                                     "previous": list(previous), "verified": True}]}
person = lambda i, name, career: {"id": i, "name": name, "how": "met", "since": 2015, "met": ["2026-09-01"], "career": career, "edu": []}
plus = lambda *cs, drop=(): {**INVESTOR, "contacts": [c for c in INVESTOR["contacts"] if c["id"] not in drop] + list(cs)}
desk = refiled(extra=[filing(3, "HAVELLS", "Lalit Varma", "Chief Financial Officer", "appointed", "October 20, 2026", previous=["Chief Financial Officer, Pidilite Industries Limited"])],
               investor=plus(person("fx-desk", "Asha Fixture", [["Pidilite Industries", "Head of Treasury", 2010, 2018], ["Havells", "Head of Internal Audit", 2018, None]])))
desk_path = desk.prep(fp(desk, "lalit-varma@HAVELLS"), least=0)
moved = refiled(investor=plus(person("fx-moved", "Formerin Fixture", [["Orient Electric", "Chief Financial Officer", 2012, 2025], ["Crompton", "Manager", 2025, None]]), drop=("nitin-agarwal",)))
uw = refiled(extra=[filing(4, "HOMEFIRST", "Uma Fixture", "Chief Underwriting Officer", "resigned", "October 20, 2026", "personal reasons"),
                    filing(5, "HOMEFIRST", "Ved Fixture", "Head of Underwriting", "resigned", "October 22, 2026", "personal reasons")])
third = refiled(extra=[filing(6, "CROMPTON", "Tara Fixture", "Chief Financial Officer", "resigned", "December 31, 2026", "personal reasons")])
sells = refiled(extra=[filing(7, "HDFCBANK", "Vik Fixture", "Group Head – Vehicle Finance", "resigned", "October 20, 2026", "personal reasons"),
                       filing(8, "HDFCBANK", "Wim Fixture", "Head – Credit Cards", "resigned", "October 22, 2026", "personal reasons")])
former = refiled(investor=plus(person("fx-former", "Formerin Fixture", [["Crompton", "Head of Internal Audit, India", 2010, 2022]]), drop=("nitin-agarwal",)))
fpin = (former.patterns("CROMPTON")[0]["pin"] or {})
cases += [("fixture: someone with a desk at the company now is not asked at a listed employer either",
           [x["contact"]["id"] for r in desk_path["stations"] if (x := r["pin"]) and x["ask"] and x["contact"]["id"] == "fx-desk"], []),
          ("fixture: ... nor is a pattern's person to ask, even when the stronger angle is a competitor", (moved.patterns("CROMPTON")[0]["pin"] or {}).get("contact", {}).get("id") == "fx-moved", False),
          ("fixture: two underwriting seats are control seats, and are named", [p["next"] for p in uw.patterns("HOMEFIRST")], ["Who holds underwriting at Home First Finance now, and who do they report to?"]),
          ("fixture: a later departure outside the window does not erase the pattern", [p["people"] for p in third.patterns("CROMPTON")], [["nikhil-thakkar@CROMPTON", "yesha-gandani@CROMPTON"]]),
          ("fixture: heads of a lending business are not control seats", sells.patterns("HDFCBANK"), []),
          ("fixture: a tenure cut short is not the calendar's", len(refiled(gandani(action="ceased", reason="Ceased before completion of tenure, citing disagreement")).patterns("CROMPTON")), 1),
          ("fixture: a resignation for a new role elsewhere is a resignation, not a move inside (round 2)",
           [p["line"] for p in refiled(gandani(reason="Resigned to take up a new role with another organisation")).patterns("CROMPTON")],
           ["Crompton: within two days, the Head of Internal Audit, Risk & Control moved to another role in the company and the Compliance Officer resigned."]),
          ("fixture: a reason that mentions Internal Audit is no move inside", [p["line"].endswith("the Compliance Officer left the seat.") for p in
           refiled(gandani(action="ceased", reason="Ceased to be Compliance Officer; continues to report to Internal Audit")).patterns("CROMPTON")], [True]),
          ("fixture: superannuation with 'no disagreement with the management' is still the calendar's",
           refiled(gandani(action="ceased", reason="Superannuation. He has confirmed there is no disagreement with the management")).patterns("CROMPTON"), []),
          ("fixture: a death is not read as a departure", (refiled(gandani(action="died", reason="Sad demise")).patterns("CROMPTON"), refiled(gandani(action="ceased", reason="Sad demise")).patterns("CROMPTON")), ([], [])),
          ("fixture: 'long-term career interests' is not a completed term", len(refiled(gandani(reason="Resigned to pursue long-term career interests")).patterns("CROMPTON")), 1),
          ("fixture: with no date stated, the evidence gives the filing's date and says so", ["Compliance Officer, resigned (filed 16 Oct)." in p["why"] for p in refiled(gandani(effective="")).patterns("CROMPTON")], [True]),
          ("fixture: a former insider is asked about the seats in their time", (fpin.get("relation"), fpin.get("ask")), ("former", "Who did audit and compliance report to at Crompton in your time?")),
          ("fixture: ... and the one-call clause says 'was', with the role and the employer whole",
           [c for rows in former.answers().values() for s_, c, *_ in rows if s_ == "CROMPTON" and "Formerin" in c],
           ["Crompton: two control seats were left within two days; Formerin was Head of Internal Audit, India at Crompton. Ask: Who did audit and compliance report to at Crompton in your time?"])]
# Where a path exists it speaks for the person: no second line resting on a profile's years
with_path = set(shown)
cases += [("a person with a path is noticed as a path, not as 'one call from'", sorted((n["kind"], n["person"]) for n in net.notices(SYMS, limit=99) if n["person"] in with_path), sorted(("path", i) for i in with_path)),
          ("... and no 'overlapped' line is said about them on a company page", [x["person"]["name"] for s in SYMS for x in net.company(s)["people"] if x["prep"] and x["path"]], []),
          ("... nor in the meeting answer", ["overlapped" in r["line"] for r in brief["rows"]], [False])]

# One call, two answers: the rule picks; the checks assert whoever it picks
ans = net.answers()
two = sorted(net.by_id[c].name for c, rows in ans.items() if len({r[0] for r in rows}) >= 2)
one = net.one_call() or {}
day = dt.date(2026, 10, 27)
stub = lambda rows: (lambda n: (setattr(n, "answers", lambda days=30: rows), n.one_call())[1])(build())
cases += [("two contacts answer at two companies this month", two, ["Meera Krishnan", "Nitin Agarwal"]),
          ("... one notice a day: the closer tie", (one.get("contact", {}).get("name"), one.get("also")), ("Meera Krishnan", ["Nitin Agarwal"])),
          ("... its line", one.get("line"), "One call, two answers: Meera Krishnan."),
          ("... its evidence: a clause and the question a company, in each notice's own words, then when they last spoke", one.get("why"),
           "Home First Finance's new CFO lists no housing finance employer; Meera holds the same seat at Aavas Financiers. Ask: What catches a new CFO out in housing finance? "
           "HDFC Bank's new MD & CEO lists ICICI Bank, where Meera was Head of Corporate Banking, West. Ask: Were you at ICICI Bank with Anup Bagchi, and what is Anup remembered for there? You last spoke in Feb 2025."),
          ("... exactly one such notice is raised", [n["contact"]["name"] for n in net.notices(SYMS, limit=99) if n["kind"] == "onecall"], ["Meera Krishnan"]),
          ("... the other still stands at both of his places", sorted(r[0] for r in ans["nitin-agarwal"]), ["CROMPTON", "HOMEFIRST"]),
          ("... its evidence has no results date and no word of suspicion", bool(re.search(r"results|profit|revenue", one.get("why", ""), re.I) or BANNED.search(one.get("why", "")) or GENDERED.search(one.get("why", ""))), False),
          ("fixture: two questions at one company is not two answers", stub({"kavita-deshmukh": [("HOMEFIRST", "a.", day, False), ("HOMEFIRST", "b.", day, False)]}), None),
          ("fixture: inside one of the two companies now is silent", stub({"meera-krishnan": [("HOMEFIRST", "a.", day, False), ("HDFCBANK", "b.", day, True)]}), None),
          ("fixture: with one company's filings gone, nobody answers twice",
           refiled(lambda f, rec: rec.update(verified=False) if f["symbol"] in ("HDFCBANK", "CROMPTON") else None).one_call(), None)]

# The only one, and a reason to call that fits the person
only = net.only_one(SYMS) or {}
allnotes = net.notices(SYMS, limit=99)
second = {**INVESTOR, "contacts": INVESTOR["contacts"] + [{"id": "fixture-2", "name": "Lata Menon", "how": "met", "since": 2015, "met": ["2026-09-01"],
                                                             "career": [["CEAT", "Head of Quality", 2010, 2018]], "edu": []}]}
narang = next((n for n in allnotes if n["kind"] == "path" and n["person"] == "sumeet-narang@CEATLTD"), {})
no_path = refiled(lambda f, rec: rec.update(verified=False) if rec["name"] == "Sumeet Narang" else None)
lone = no_path.only_one(SYMS) or {}
cases += [("the only one: one a day, the longest silence with a reason", (only.get("contact", {}).get("name"), only.get("symbol")), ("Arvind Pillai", "CEATLTD")),
          ("... the reason is the arrival whose path already asks Arvind, and its question", (only.get("person"), only.get("ask"), only.get("at")),
           ("sumeet-narang@CEATLTD", "What should a new independent director at CEAT ask about first?", "2026-10-14")),
          ("... so it is said on that path's notice, once", narang.get("why"),
           "CEAT's new independent director, filed 14 Oct. Arvind Pillai (worked here) and Aman Khurana (used to work at Samara Capital). Arvind is the only person you know who has worked inside CEAT; you last spoke in Oct 2021."),
          ("... and not again as a notice of its own, a reason to call, or going cold",
           ([n["kind"] for n in allnotes if n["contact"] and n["contact"]["id"] == "arvind-pillai"], any("CEAT" in n["why"] for n in allnotes if n["kind"] == "gap" and "going cold" in n["line"])), ([], False)),
          ("... of eight holdings with one quiet person inside, by the longest silence", only.get("others"), 7),
          ("fixture: with no arrival at CEAT, the reason is the filing that fits what Arvind did there, dated, with one question", (lone.get("line"), lone.get("why"), lone.get("at")),
           ("Arvind Pillai is the only person you know who has worked inside CEAT.",
            "Plant Head, Halol, 2008–2017. You last spoke in Oct 2021. CEAT reported Q2 on 14 Oct: revenue up 26.2%, profit down 39.7% on a year ago. Ask: What would you look at first in CEAT's results?", "2026-10-14")),
          ("fixture: ... raised as one dated notice", [(n["kind"], n["at"]) for n in no_path.notices(SYMS, limit=99) if n["contact"] and n["contact"]["id"] == "arvind-pillai"], [("only", "2026-10-14")]),
          ("fixture: with a second person inside, nobody is 'the only one' there", (build(second).only_one(SYMS) or {}).get("symbol") == "CEATLTD", False),
          ("a tax order is no reason to call a purchasing head (Ramesh Iyer)", "ramesh-iyer" in {w["contact"]["id"] for w in net.warm(limit=99)}, False),
          ("every reason to call is dated by its reason, so a window shows it only while the reason is in it", [n["at"] for n in allnotes if n["kind"] == "warm" and not n["at"]], [])]
# Fixtures and checks from the third result review (14 Nov)
ceat = net.prep(fp(net, "sumeet-narang@CEATLTD"))
r3reg = Registry(D / "registry.json")
PARTIAL = ["Chief Financial Officer, HDFC Life Insurance Company Limited", "Larsen & Toubro Infotech", "IDFC FIRST Bank", "Sun Pharma Advanced Research Company"]
WHOLE = [("Interim CFO, IDFC Limited", "IDFC Limited"), ("Various functions, Citigroup India", "Citigroup"), ("Officer, TCI Freight division", "Transport Corporation of India"),
         ("Proprietary Investments Group, Goldman Sachs", "Goldman Sachs"), ("Chief Executive, Nabha Power Ltd", "Nabha Power")]
life = refiled(extra=[filing(9, "HAVELLS", "Lalit Varma", "Chief Financial Officer", "appointed", "October 20, 2026", previous=PARTIAL[:1])])
relabel = refiled(gandani(action="ceased", reason="Changed from SMP to Non-SMP category"))
aged = refiled(gandani(action="retired", reason="On attaining the age of 60 years"))
unsaid = refiled(gandani(action="retired", reason="not stated"))
both = refiled(gandani(role="Company Secretary & Compliance Officer"),
               extra=[filing(10, "CROMPTON", "Xan Fixture", "Company Secretary", "appointed", "October 20, 2026")])
bagchi = ask.answer(net, "Brief me on Anup Bagchi at HDFC Bank", SYMS)
cover = {x["symbol"]: x["level"] for x in net.coverage(SYMS)}
cases += [("a seat the filing's profile opens with is a station: CEAT's new director is filed as Founder & CEO of Samara Capital",
           flat(ceat)[:3], [("seat", "CEAT", "Additional Director (Non-Executive, Independent Director)", "from 14 Oct",
                             "What should a new independent director at CEAT ask about first?", "Arvind Pillai", "Worked here", "Plant Head, Halol, 2008–2017"),
                            ("listed", "Samara Capital", "Founder & CEO", "now",
                             "Did Samara Capital hold, or deal with, anything connected to CEAT in your time there?", "Aman Khurana", "Worked there", "Principal, 2011–2017"),
                            ("listed", "Goldman Sachs", "Proprietary Investments Group", "")]),
          ("... what the firm holds today is for the room, raised from the filing", [(a["ask"], a["source"]) for a in ceat["room"]],
           [("Does Samara Capital hold, or deal with, anything connected to CEAT?", "filing")]),
          ("... read for one person of 42, and 'Nominee Director of LIC' is not a seat at LIC", [(q.id, q.holds[0].name, q.holds[1]) for q in net.filed if q.holds],
           [("sumeet-narang@CEATLTD", "Samara Capital", "Founder & CEO")]),
          ("fixture: a longer name that holds a known one is not that company", [r3reg.named(t).known for t in PARTIAL], [False] * 4),
          ("fixture: ... a suffix, a country or a division still is", [r3reg.named(t).name for t, _ in WHOLE], [w for _, w in WHOLE]),
          ("fixture: ... so a path keeps the filing's own words and pins nobody there",
           [(q.listed[0][0].name, q.listed[0][0].known) for q in life.filed if q.id == "lalit-varma@HAVELLS"], [("HDFC Life Insurance Company Limited", False)]),
          ("no demo employer changed: every listed employer but one firm of accountants is still known", [o.name for q in net.filed for o, _ in q.listed if not o.known], ["A.B.Ankhad & Associates"]),
          ("fixture: a change of designation is not a departure (\"Changed from SMP to Non-SMP category\")", relabel.patterns("CROMPTON"), []),
          ("fixture: a retirement by age, or one with no reason stated, is the calendar's", (aged.patterns("CROMPTON"), unsaid.patterns("CROMPTON")), ([], [])),
          ("fixture: a company secretary filed after a company secretary and compliance officer left is a successor",
           ["No successor" in x["why"] for x in both.patterns("CROMPTON")], [False]),
          ("beside a path, nobody is 'ruled out' in the meeting answer (Anup Bagchi)", (bool(bagchi.get("preps")), [n for n in bagchi["notes"] if n.startswith("Ruled out")]), (True, [])),
          ("someone who once worked inside counts as inside, whatever they do now (L&T, UltraTech)", (cover["LT"], cover["ULTRACEMCO"]), ("inside", "inside")),
          ("... so the company's cover line and its first person agree", net.company("LT")["cover"], "1 person you know has worked inside Larsen & Toubro."),
          ("... and 'Where am I blind?' says so", ask.answer(net, "Where am I blind?", SYMS)["lede"][:48], "Someone you know has worked inside every holding")]
# The network card (network-loop): a join of filings Push reads one by one, with one person to ask, may raise a card on Today
carded = sorted((n["kind"], n["at"], n["card"]["symbols"], n["card"]["line"]) for n in allnotes if n.get("card"))
card_text = [t for n in allnotes if n.get("card") for t in [n["card"]["line"], n["card"].get("sheet", "")] + [x for r in n["card"].get("rows", []) for x in (r["line"], r["ask"])]]
_slim = copy.deepcopy(SLIM["filings"])
for f in _slim:
    if f["symbol"] == "CGPOWER" and f["category"] == "capex":
        f["at"] = "2026-10-28" + f["at"][10:]
moved_capex = Network(_slim, INVESTOR, Registry(D / "registry.json"), None, SLIM["companies"], TODAY).notices(SYMS, limit=99)
cases += [("someone you know in a filing is one row at that company: no other notice there names them, and that day's other filing joins it",
           [(x["kind"], x["symbol"]) for x in allnotes for y in allnotes if y["kind"] == "contact" and x is not y and x["contact"] and x["symbol"] == y["symbol"]
            and x["contact"]["id"] == y["contact"]["id"]], []),
          ("... a filing on another day keeps its own row and date: CG Power's capex filed on 28 Oct is not folded into 23 Oct's news",
           sorted((x["kind"], x["at"]) for x in moved_capex if x["symbol"] == "CGPOWER" and x["contact"] and x["contact"]["id"] == "rajat-shah"),
           [("contact", "2026-10-23"), ("event", "2026-10-28")]),
          ("... Rajat Shah: the capex filing is said on the news about him, before the caution",
           [x["why"] for x in allnotes if x["kind"] == "contact" and x["symbol"] == "CGPOWER"],
           ["Same name, and both records show CG Power. Filed 23 Oct. Also filed 23 Oct: Board approved capacity expansion and capex projects totaling 422.76 Crores. "
            "Works there now: keep the conversation to what is public."])]
cases += [("a notice carries a card only for control seats with a person to ask, and for one call", carded,
           [("onecall", "2026-10-27", ["HOMEFIRST", "HDFCBANK"], "A new CFO at Home First Finance and a new MD & CEO at HDFC Bank: one call to Meera Krishnan, CFO at Aavas Financiers, has a question for each."),
            ("seats", "2026-10-16", ["CROMPTON"], "Within two days, the Head of Internal Audit, Risk & Control moved to another role in the company and the Compliance Officer resigned.")]),
          ("... one call's card puts each company's own question, as its path or pattern asks it",
           [r["ask"] for n in allnotes if n["kind"] == "onecall" for r in n["card"]["rows"]],
           ["What catches a new CFO out in housing finance?", "Were you at ICICI Bank with Anup Bagchi, and what is Anup remembered for there?"]),
          ("... no pronoun and no word of suspicion on a card", [t for t in card_text if PRONOUN.search(t) or BANNED.search(t)], []),
          ("fixture: without the one person to ask, Crompton's pattern stays in the fold and raises no card",
           [(n["kind"], bool(n["contact"]), bool(n.get("card"))) for n in build(investor={**INVESTOR, "contacts": [c for c in INVESTOR["contacts"] if c["id"] != "nitin-agarwal"]}).notices(SYMS, limit=99) if n["kind"] == "seats"],
           [("seats", False, False)])]
# One choice of who fits, by the kind of question (network-loop): a departure, or the numbers
fits = {sym: net.fit(sym) for sym in SYMS}
pick = lambda sym, k: (lambda f: f and (f["contact"]["name"], f["relation"], f["ask"]))(fits[sym][k])
cases += [("Syngene's CFO left: someone who worked there, asked the seat question from where they sat", pick("SYNGENE", "leave"),
           ("Dr. Leena Joshi", "former", "Where did R&D and finance pull against each other at Syngene?")),
          ("L&T's margin: someone at a competitor today, about their own seat", pick("LT", "numbers"),
           ("Anand Raghavan", "competitor", "How does the engineering & construction market look from Tata Projects?")),
          ("Home First's guidance: not Kavita Deshmukh, who left in 2020, but a competitor's CFO, never asked Home First's figures", pick("HOMEFIRST", "numbers"),
           ("Meera Krishnan", "competitor", "How does the housing finance market look from Aavas Financiers?")),
          ("HDFC Bank: a group colleague sees the group, not the quarter, and the one insider is inside: nobody", (fits["HDFCBANK"]["leave"], fits["HDFCBANK"]["numbers"]), (None, None)),
          ("KFin: a customer, asked how it rates its supplier", pick("KFINTECH", "numbers"),
           ("Neha Saxena", "customer", "How does KFin Technologies rate as a supplier of registrar services to fund houses?")),
          ("over all 18 companies, nobody who has left is on a numbers row", [(sym, f["numbers"]["contact"]["name"]) for sym, f in fits.items() if f["numbers"]
                                                                          and not any(s.current and s.org.name in f["numbers"]["basis"] for s in net.by_id[f["numbers"]["contact"]["id"]].career)], []),
          ("... nobody inside the company now is ever asked", [(sym, k) for sym, f in fits.items() for k in ("leave", "numbers")
                                                               if f[k] and net._inside(net.by_id[f[k]["contact"]["id"]], net.reg.by_symbol[sym])], []),
          ("... a departure's person left over a year ago", [(sym, f["leave"]["basis"]) for sym, f in fits.items() if f["leave"] and not re.search(r"–(19|20)\d\d$", f["leave"]["basis"])], []),
          ("... every fit's question is from the table, with no pronoun and no word of suspicion",
           [f[k]["ask"] for f in fits.values() for k in ("leave", "numbers") if f[k] and (not any(t.match(f[k]["ask"]) for t in TEMPLATES) or PRONOUN.search(f[k]["ask"]) or BANNED.search(f[k]["ask"]))], []),
          ("the numbers question follows the question beside it: a margin asks about costs, a fall in profit about one-off items",
           [(sym, f["numbers"]["relation"]) for sym, f in fits.items() if f["numbers"] and not (re.search(r"\bcosts\b|\bcharges\b", f["numbers"]["on"]["margin"])
                                                                    and (f["numbers"]["relation"] != "competitor" or "one-off" in f["numbers"]["on"]["profit"]))], []),
          ("... L&T's margin: the cost question, from Tata Projects", fits["LT"]["numbers"]["on"]["margin"], "Which costs are moving most in engineering & construction, as Tata Projects sees it?"),
          ("... Home First's credit cost: the credit question, from Aavas Financiers", fits["HOMEFIRST"]["numbers"]["on"]["credit"], "How are credit costs moving in housing finance, as Aavas Financiers sees it?"),
          ("... every such question is from the table", [q for f in fits.values() if f["numbers"] for q in f["numbers"]["on"].values() if not any(t.match(q) for t in TEMPLATES)], []),
          ("no question in the table names a time", [k for k, t in ASK.items() if re.search(r"\b(quarter|year|years|month|FY\d*|this|today|now|recent)\b", t, re.I)], []),
          ("the fits fire: of four companies with a CEO, CFO or MD gone, three have a person; the numbers have one at 11 of 18",
           (sum(1 for f in fits.values() if f["leave"]), sum(1 for f in fits.values() if f["numbers"])), (3, 11))]
# Results are a reason to call when they say something (the brief: "their former employer just announced results"), said
# with the exchange's figures, checked against what push.json shows on that filing
PUSH = {f["id"]: f for f in json.loads((ROOT / "web/public/data/push.json").read_text())["filings"]}
reasons = net.warm(limit=99)
RX = re.compile(r"^(.+) reported (Q\d) on \d+ \w+: ([a-z ]+) (up|down) ([\d.]+)%, profit (up|down) ([\d.]+)% on a year ago\. ")
fig = lambda f, k: next((l["yoy"] for l in f["results"]["lines"] if l["key"] == k), None)
sign = lambda d, v: float(v) * (1 if d == "up" else -1)
on_results = [(w, PUSH[w["filing"]], RX.match(w["reason"])) for w in reasons if PUSH[w["filing"]]["category"] == "results"]
cases += [("every reason built on results says the quarter, the top line and profit as the results card does",
           [(w["contact"]["name"], m and (m.group(2), m.group(3), sign(m.group(4), m.group(5)), sign(m.group(6), m.group(7)))) for w, f, m in on_results],
           [(w["contact"]["name"], (f["results"]["quarter"].split()[0], next(l["label"] for l in f["results"]["lines"] if l["key"] == "revenue").lower(),
             fig(f, "revenue"), fig(f, "pat"))) for w, f, m in on_results]),
          ("... a results filing without figures is never a reason", [w["reason"] for w, f, m in on_results if not f.get("results")], []),
          ("... at most one reason a company and quarter", len({(f["symbol"], f["results"]["quarter"]) for w, f, m in on_results}), len(on_results)),
          ("... five of the eight reasons are results, each with its figures", (len(on_results), len(reasons)), (5, 8))]
# Yes or No on a name FINN can't place (network-loop): the answer rebuilds every view, and every honesty rule holds in
# every answer state: none, then each possible pair answered Same person and Someone else
from finn.network.views import views as all_views
JIGAR = "jigar-shah@HDFCBANK|jigar-shah"
def honest(n):
    """Every way a view could break a rule, over everything the network says. Empty when it holds."""
    bad, notes = [], n.notices(SYMS, limit=99)
    # every word about a person: names only. The notices' evidence may say "the disputes behind them" of a tax position
    texts = [t for x in notes for t in (x["line"], (x.get("card") or {}).get("line", ""))]
    bad += [("gendered", x["why"]) for x in notes if GENDERED.search(x["why"])] + [("suspicion", x["why"]) for x in notes if BANNED.search(x["why"])]
    for q in n.filed:
        d = n.prep(q, least=0)
        if d:
            texts += said(d)
            bad += [("asked inside", q.id, x["contact"]["name"]) for x in asked(d) if n._inside(n.by_id[x["contact"]["id"]], q.company)]
            bad += [("pins", q.id)] if len(asked(d)) > PINS else []
        if not n.known(q):
            bad += [("overlapped", q.id, x["line"]) for x in n.reach(q, limit=99)["paths"] if x["where"] != q.company.name and (x["dated"] or "overlapped at" in x["line"])]
    texts += [f[k]["ask"] for sym in SYMS for f in [n.fit(sym)] for k in ("leave", "numbers") if f[k]]
    return bad + [("pronoun", t) for t in texts if PRONOUN.search(t)] + [("suspicion", t) for t in texts if BANNED.search(t)]
states = [{}] + [{k: v} for k in sorted(net.asks) for v in ("same", "different")]
nets = {json.dumps(st): build(decisions=st) for st in states}
same, other = nets[json.dumps({JIGAR: "same"})], nets[json.dumps({JIGAR: "different"})]
jig = lambda n: [(x["kind"], x["line"]) for x in n.notices(SYMS, limit=99) if "Jigar" in x["line"]]
cases += [("the engine asks about one pair", sorted(net.asks), [JIGAR]),
          (f"every honesty rule holds in every answer state ({len(states)} states)", {st: honest(n) for st, n in nets.items()}, {st: [] for st in nets}),
          ("Same person: the question becomes the news, and can be changed", [(x["kind"], x["line"], x["key"]) for x in same.notices(SYMS, limit=99) if "Jigar" in x["line"]],
           [("contact", "Jigar Shah, who you know, has joined HDFC Bank as General Counsel.", JIGAR)]),
          ("... Jigar is never asked a question or pinned anywhere, being inside HDFC Bank now",
           [q.id for q in same.filed for d in [same.prep(q, least=0)] if d for x in asked(d) if x["contact"]["id"] == "jigar-shah"]
           + [sym for sym in SYMS for pt in same.patterns(sym) if pt["pin"] and pt["pin"]["contact"]["id"] == "jigar-shah"], []),
          ("Someone else: the question is gone; the answer stays where it was asked, with its key, so a mis-tap can be undone",
           ([(x["kind"], x["line"], x["key"]) for x in other.notices(SYMS, limit=99) if "Jigar" in x["line"]], [(i["line"], i["why"], i["said"]) for i in other.identity_notes(fp(other, "jigar-shah@HDFCBANK"))]),
           ([("different", "You said HDFC Bank's new General Counsel, Jigar Shah, is not the Jigar Shah you know.", JIGAR)], [("Not the Jigar Shah you know.", "You said this is someone else.", True)])),
          ("... and only an answer the investor gave: the engine's own 'different' verdicts raise no such row", [x["line"] for x in net.notices(SYMS, limit=99) if x["kind"] == "different"], []),
          ("on every company, in every answer state, the cover's count is the people it names, and each is a row the page can list",
           [(sym, v["cover"]) for n in nets.values() for sym in SYMS for v in [n.company(sym)]
            if (v["counted"] and not v["cover"].startswith(f"{len(v['counted'])} {'person' if len(v['counted']) == 1 else 'people'} you know"))
            or set(v["counted"]) - {r["contact"]["id"] for r in v["call"]} - {pt["pin"]["contact"]["id"] for pt in v["patterns"] if pt["pin"]}], []),
          ("... HDFC Bank after Same person: two have worked inside, Jigar Shah one of them", (same.company("HDFCBANK")["cover"], same.company("HDFCBANK")["counted"]),
           ("2 people you know have worked inside HDFC Bank.", ["jigar-shah", "rahul-menon"])),
          ("Same person: news about someone inside a company now carries the caution", [x["why"].endswith("keep the conversation to what is public.") for x in same.notices(SYMS, limit=99) if x["kind"] == "contact"], [True, True]),
          ("an answer about a pair the engine did not ask about changes nothing, byte for byte",
           json.dumps(all_views(build(decisions={"rajat-shah@CGPOWER|rajat-shah": "different", "x|y": "same"})), default=str) == json.dumps(all_views(net), default=str), True)]
group("path, patterns and one call", cases)

ok, n = sum(r[1] for r in results), sum(r[2] for r in results)
lines.append(f"TOTAL {ok}/{n}")
text = "\n".join(lines)
print(text)
(ROOT / "evals" / "network_result.txt").write_text(text + "\n")
sys.exit(0 if ok == n else 1)
