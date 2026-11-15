"""Every number the grader reads, with where it comes from.

A claim is a phrase as written, the documents it must appear in, its value (computed from the built data or
an eval's output, else pinned to the file and line that states it), and when it is true on the link: repo,
live, needs-deploy or needs-key; needs-* claims carry the sentence to use instead. Fails if (a) a phrase is
missing, (b) a document states another number in it, or (c) the note, README, walkthrough or build history
holds a number no claim covers. Free: dates, times, years, quarter names, 390x844, list markers, code, links,
and quotes found in the brief or inside the walkthrough's on-screen strings ("one" isn't counted). For
ARCHITECTURE and the brief trace it lists the unclaimed numbers, to clear by hand.   usage: python3 evals/claims.py
"""
import datetime as dt, glob, json, pathlib, re, subprocess, sys
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
J = lambda p: json.loads((R / p).read_text())
T = lambda p: (R / p).read_text()
DOC = {'N': 'docs/COVERING_NOTE.md', 'R': 'README.md', 'W': 'docs/WALKTHROUGH_SCRIPT.md', 'H': 'docs/BUILD_HISTORY.md',
       'A': 'docs/ARCHITECTURE.md', 'T': 'docs/BRIEF_TRACE.md', 'P': 'docs/PRICE_REACTION.md'}
STRICT = 'NRWH'
WORDS = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty'.split()
w = lambda n, cap=False: WORDS[int(n)].capitalize() if cap else WORDS[int(n)]
ev = lambda f, rx: re.search(rx, T('evals/' + f)).groups()
WHERE = []
def pin(f, rx):
    """A value stated in a file; its file and line are printed with the claim."""
    t = T(f); m = re.search(rx, t); WHERE.append(f"{f}:{t[:m.start()].count(chr(10)) + 1}")
    return m.groups()

PUSH, NET = J('web/public/data/push.json'), J('web/public/data/network.json')
CO = [J(f) for f in sorted(glob.glob(str(R / 'web/public/data/companies/*.json')))]
UNREAD = {c['symbol']: c['calls'] for c in CO}
PAID = [c['usage'] for c in CO if (c.get('usage') or {}).get('usd_if_billed')]
AVG = sum(u['usd_if_billed'] for u in PAID) / len(PAID)
TOK = sum(u['tokens_in'] + u['tokens_out'] for u in PAID) / len(PAID)
F = PUSH['filings']; RULE = sum(f['how'] == 'rule' for f in F); ACT = sum(f['tier'] == 'act' for f in F)
DAYS = (dt.date.fromisoformat(max(f['at'] for f in F)[:10]) - dt.date.fromisoformat(min(f['at'] for f in F)[:10])).days
HOLD, FNS = len(PUSH['portfolio']), w(len(glob.glob(str(R / 'api/[a-z]*.py'))))
GRADES = ev('grades_review.md', r'(\d+) of (\d+) hold')
# What the Network notices by joining (docs/plans/notice.md): the path, control seats, one call
PATH = next(x['prep'] for b in NET['filings'].values() for x in b.get('people', []) if x['person']['id'] == 'rinkoo-somani@HOMEFIRST' and x.get('prep'))
SEATS = NET['companies']['CROMPTON']['patterns'][0]
MD = next(x['prep'] for b in NET['filings'].values() for x in b.get('people', []) if x['person']['id'] == 'anup-bagchi@HDFCBANK' and x.get('prep'))
ONECALL = re.search(r'One call, (\w+) answers', json.dumps(NET['notices'])).group(1)
def namesakes():
    from finn.network import Network
    return (str(len(Network.load().filed) * 2),)

AR = {f.stem: J(f'web/public/data/annual/{f.name}') for f in sorted((R / 'web/public/data/annual').glob('*.json'))}
AR_READ = [a for a in AR.values() if a['read']]
AR_NOW = lambda rx: re.search(rx, T('evals/annual_result.txt').split('---- this run ----')[-1]).groups()   # not the recorded passes above it
AR_UT = next(c for c in AR['ULTRACEMCO']['checks']['calls'] if c['note'] == '37(b)')
AR_SY = next(b for b in AR['SYNGENE']['blocks'] if b['title'] == 'Contingent liabilities')

# (documents, phrase with {} for each value, values[, condition, the sentence to use instead])
CLAIMS = [
    # annual-report: the readers' results (evals/annual_result.txt) and the served files they made
    ('N', 'penalties that its {} calls never mention', lambda: (w(len(AR_UT['read'])),)),
    ('R', 'appears in its last {} calls', lambda: (w(len(AR_UT['read'])),)),
    ('R', 'labels read by hand from {} reports, half held out', lambda: (str(len(J('evals/annual_truth.json')['companies'])),)),
    ('R', "Syngene's ₹{} crore is {} years of profit", lambda: re.search(r'₹(\d+) crore at 31 March 2026.*? That is ([\d.]+) years', AR_SY['text']).groups()),
    ('R', '| {}/{}. Opinion and every emphasis right on {} of {} audit reports', lambda: AR_NOW(r'TOTAL (\d+)/(\d+)') + AR_NOW(r'\((\d+)/(\d+) emphasis')),
    ('NR', 'where the note prints a total, {} of {} reports', lambda: (str(sum(1 for a in AR_READ if a['checks']['claims'] and a['checks']['claims']['rows'])), str(len(AR_READ)))),
    ('NR', 'about ${} to read a company', lambda: (f"{AVG:.2f}",)),
    # trust: the Your data sheet, accessibility and speed (docs/plans/trust.md)
    ('R', 'open one sheet that says, in {} short blocks', lambda: (w(T('web/src/Trust.tsx').count('<section className="yd-sec">')),)),
    ('R', "axe-core's WCAG {} A and AA rules at 390×844 on {} views", lambda: ('2.2' if 'wcag22aa' in ev('a11y_result.txt', r'tags ([\w ]+)')[0] else '?',
                                                                         w(ev('a11y_result.txt', r'views (\d+):')[0]))),
    ('R', 'every control at least {} px; the keyboard', lambda: (str(-int(-float(re.search(r'r\.width < ([\d.]+)', T('web/test/e2e/a11y.py')).group(1)) // 1)),)),   # 23.5 allows for subpixels: 24
    ('R', '| {} serious or critical on {} of {} views |', lambda: ev('a11y_result.txt', r'(\d+) serious or critical on (\d+) of (\d+) views')),
    ('R', '| {} cold loads of a local preview on a throttled phone ({} ms round trip, {} Mbps, CPU {}×), medians | First paint {} ms (was {} before the outline moved into the HTML), largest paint {} ms, the count settled {} ms; {} KB of script gzipped |',
     lambda: (w(ev('speed_result.txt', r'; (\d+) cold loads')[0], cap=True), *ev('speed_result.txt', r'(\d+) ms RTT, ([\d.]+) Mbps down, \d+ kbps up, CPU (\d+)x'),
              ev('speed_result.txt', r'FCP (\d+) ms')[0], pin('docs/plans/trust.md', r'Baseline medians: FCP (\d+) ms')[0],
              ev('speed_result.txt', r'LCP (\d+) ms')[0], ev('speed_result.txt', r'count settled (\d+) ms')[0], ev('speed_result.txt', r'JS (\d+)')[0])),
    ('A', 'About ${} reads a company', lambda: (f"{AVG:.2f}",)),
    ('A', '${} over {} built', lambda: (f"{AVG:.3f}", len(PAID))),
    ('R', 'average of {} built) | {}k | ${}', lambda: (len(PAID), round(TOK / 1000), f"{AVG:.3f}")),
    ('R', '{} holdings, {} days, {} filings | {}k | ${}', lambda: (HOLD, DAYS, len(F), round(
        (PUSH['usage']['tokens_in'] + PUSH['usage']['tokens_out']) / 1000), f"{PUSH['usage']['usd_if_billed']:.2f}")),
    ('A', '${} for {} filings', lambda: (f"{PUSH['usage']['usd_if_billed']:.2f}", len(F))),
    ('N', 'In the {} days to 28 Oct the {} holdings filed {} times, and FINN would have interrupted you for {}', lambda: (DAYS, HOLD, len(F), ACT)),
    ('R', '({} of {} filings, free)', lambda: (RULE, len(F))),
    ('R', '({} of {} in the 28 Oct snapshot)', lambda: (RULE, len(F))),
    ('A', 'rules settle {} of {} |', lambda: (RULE, len(F))),
    ('H', 'rules settle {}% of filings', lambda: (round(100 * RULE / len(F)),)),
    ('H', 'plans each took {} rounds', lambda: ((lambda n: w(n[0]) if len(set(n)) == 1 else n)(
        [len(re.findall(r'(?m)^## Round \d critiques', T(f'docs/plans/{k}.md'))) for k in ('architecture', 'writeup')]),)),
    ('R', '{} sessions of close and volume', lambda: (len(next(iter(PUSH['eod'].values()))),)),
    ('R', '{} quarters, {} years', lambda: (len(CO[0]['quarters']), len(CO[0]['snapshot']['years']))),
    ('R', '/api/call ×{} in parallel', lambda: pin('finn/research.py', r'(?m)^N_CALLS = (\d+)')),
    ('R', 'reads its last {} earnings calls', lambda: (w(pin('finn/research.py', r'(?m)^N_CALLS = (\d+)')[0]),), 'needs-key',
        'Any other NSE symbol would be read live from its last five earnings calls; on this link that is off for now, and it says so.'),
    ('N', 'from its last {} calls', lambda: (w(pin('finn/research.py', r'(?m)^N_CALLS = (\d+)')[0]),), 'needs-key',
        'The Look up tab answers questions from the ledgers with no model call. Reading any other NSE symbol live is off on this link, and it says so.'),
    ('R', '{} Vercel Python functions: {} for live lookups', lambda: (FNS, w(len(glob.glob(str(R / 'api/[a-z]*.py'))) - 1))), ('R', 'and {} small functions on Vercel', lambda: (FNS,)),
    ('N', 'A static app and {} Python functions', lambda: (FNS,)),
    ('R', 'your internet address for about {} minutes', lambda: (w(int(pin('api/call.py', r'Limiter\(\d+, (\d+)\)')[0]) // 60),)),
    ('N', '{} companies outside the holdings', lambda: (w(len({c['symbol'] for c in CO} - {p['symbol'] for p in PUSH['portfolio']}), True),)),
    ('R', '1 per {} filings', lambda: pin('finn/classify.py', r'vague\[k:k \+ (\d+)\]')),
    ('NR', 'under {}% of a year', lambda: pin('finn/triage.py', r'pct < (\d+\.\d+)')),
    ('R', 'an {}-stock portfolio', lambda: (HOLD,)),
    ('R', 'about ${} a month in model calls', lambda: (int(pin('docs/adr/0005-production-on-gcp.md', r'Reading filings .*?\| \$\d+–(\d+) \|')[0])
        + int(pin('docs/adr/0005-production-on-gcp.md', r'Calls read and graded .*?\| about \$(\d+) \|')[0]),)),
    ('R', 'tier of {} hand-labelled filings', lambda: ev('classify_result.txt', r'category: \d+/(\d+)')),
    ('N', 'I tried {} ways to interact', lambda: (w(len(re.findall(r'(?m)^## \d+\.', T('design/STAGE4_EXPLORE.md')))),)),
    ('R', 'I tried {} ways of interacting', lambda: (w(len(re.findall(r'(?m)^## \d+\.', T('design/STAGE4_EXPLORE.md')))),)),
    ('R', 'Category {}/{} ({}%), tier {}/{} ({}%)', lambda: ev('classify_result.txt', r'category: (\d+)/(\d+) = (\d+)%') +
        ev('classify_result.txt', r'tier: +(\d+)/(\d+) = (\d+)%')),
    ('R', '{} filing that should have interrupted', lambda: (w(ev('classify_result.txt', r"interrupted but didn't: (\d+)")[0], 1),)),
    ('R', '{}/{} numbers agree within 1%', lambda: ev('results_result.txt', r'within 1%: (\d+)/(\d+)')),
    ('N', 'within 1% of screener on {} of {} numbers', lambda: ev('results_result.txt', r'within 1%: (\d+)/(\d+)')),
    ('R', 'The {} that don', lambda: (int(ev('results_result.txt', r'/(\d+) =')[0]) - int(ev('results_result.txt', r': (\d+)/')[0]),)),
    ('R', 'compiled table, {} companies', lambda: (len(re.findall(r'(?m)^[A-Z&]+ +Q\d FY\d\d', T('evals/results_result.txt'))),)),
    ('R', 'Real {}/{} pass, small slips {}/{} pass. Changed numbers {}/{}, added "not" {}/{} and stitched sentences {}/{}',
        lambda: sum((ev('quotes_result.txt', rf'{k} +(\d+)/(\d+)') for k in ('real', 'slip', 'number changed', 'negation added', 'stitched')), ())),
    ('NR', '{} of {} grades', lambda: GRADES), ('R', '{}/{} hold', lambda: GRADES),
    ('R', '{} graded promises', lambda: (w(GRADES[1], 1),)), ('R', '{} is a small sample', lambda: (w(GRADES[1], 1),)),
    ('R', '{} companies were graded by flash-lite', lambda: (w(sum('gemini-3.5-flash' not in u['by_model'] for u in PAID), 1),)),
    ('R', 'and {} interrupted that shouldn', lambda: (w(ev('classify_result.txt', r"interrupted when it shouldn't have: (\d+)")[0]),)),
    ('R', 'Of {} real quotes with several words swapped for synonyms, only {} pass', lambda: ev('quotes_result.txt', r'synonym swap +(\d+)/(\d+)')[::-1]),
    ('R', "All {} of Eris Lifesciences' calls", lambda: (lambda c: (w(len(c)),) if all(x.get('error') for x in c) else ('?',))(UNREAD['ERIS'])),
    ('R', '{} of {} did at Maruti Suzuki and at SRF', lambda: (lambda n: (w(n[0][0]), w(n[0][1])) if len(set(n)) == 1 else ('?', '?'))(
        [(sum(bool(x.get('error')) for x in UNREAD[s]), len(UNREAD[s])) for s in ('MARUTI', 'SRF')])),
    ('R', 'A clone prints {}/{}', lambda: (lambda n: (n - 1, n - 1))(int(re.findall(r'TOTAL (\d+)/', T('evals/annual_result.txt'))[-1]))),
    ('N', '(flash-lite graded {})', lambda: (w(sum('gemini-3.5-flash' not in u['by_model'] for u in PAID)),)),
    ('NRA', '{} invented namesakes', namesakes),
    ('R', '| {}/{}; 0 false matches', lambda: ev('network_result.txt', r'TOTAL (\d+)/(\d+)')),
    ('N', '{} of {} checks pass, with no false match', lambda: ev('network_result.txt', r'TOTAL (\d+)/(\d+)')),
    ('R', 'fetching nothing | {}/{}', lambda: ev('security_result.txt', r'TOTAL (\d+)/(\d+)')),
    ('R', '(`evals/run_answer.py`, {}/{}; the right page in the top {} for {} of {} questions', lambda: ev('answer_result.txt', r'TOTAL (\d+)/(\d+)') + (lambda k, a, n: (w(k), a, n))(*ev('answer_result.txt', r'recall at (\d+): (\d+)/(\d+) exact page'))),
    ('R', 'then the {} committed ledgers | {}/{}; a second pass', lambda: (str(len(CO)), *ev('recheck_result.txt', r'TOTAL (\d+)/(\d+)'))),
    ('N', 'with {} people you know on it', lambda: (w(PATH['on_path']),)),      # on the filed path, as the app's own line counts
    ('R', '{} people you know on it', lambda: (w(PATH['on_path']),)),
    ('N', 'names the {} people you know who were at ICICI Bank and ICICI Securities', lambda: (w(MD['on_path']),)),
    ('N', '`{}` reads and `{}` grades once per company', lambda: pin('finn/config.py', r'(?m)^FAST = "([\w.-]+)"[\s\S]*?^SMART = "([\w.-]+)"')),
    ('R', 'The {} people you know who were at ICICI Bank and ICICI Securities', lambda: (w(MD['pins']),)),
    ('N', "{} exits from Crompton's audit and compliance seats", lambda: (w(len(SEATS['people'])),)),
    ('R', '{} small changes that are a pattern together', lambda: (w(len(SEATS['people'])),)),
    ('R', '(within {} days Crompton', lambda: (w(SEATS['span']),)),
    ('R', 'folded one of the {})', lambda: (w(len(SEATS['people'])),)),
    ('R', 'one contact who answers {} of the month', lambda: (ONECALL,)),
    ('A', 'Today there are {} invented contacts.', lambda: (NET['contacts'],)),
    ('N', 'the investor, {} contacts and every tie.', lambda: (NET['contacts'],)),
    ('N', 'kept {} months after last use', lambda: pin('docs/ARCHITECTURE.md', r'\| (\d+) months after last use')),
    ('W', 'About 3:15, {} beats', lambda: (w(len(re.findall(r'(?m)^### \d[a-z]?\. ', T(DOC['W'])))),)),
    ('NH', 'critiqued by {} model reviewers', lambda: (w(len(re.search(r'## Round 1 critiques of v1 \(11 Nov\): (.*)', T('docs/plans/writeup.md')).group(1).split(','))),)),
    ('H', 'each pass reviewed by {} subagents looking at the rendered image', lambda: (lambda a, b: a if a == b else ('?',))(   # the two diagram tasks of 15 Nov, as CONTEXT logs them
        pin('docs/CONTEXT.md', r'(\w+) reviewers on the rendered v1'), pin('docs/CONTEXT.md', r'(\w+) reviewers on the rendered v3'))),
    ('N', 'Its default branch is one commit', lambda: (), 'needs-deploy',
        'Code: in the git bundle sent with this email. The GitHub repo opens once it holds only filed facts about real people.'),
    ('RH', 'default branch, submission, is one commit', lambda: (), 'needs-deploy',
        'Code: in the attached bundle. The GitHub repo opens once it holds only filed facts about real people.'),

    # What leads ARCHITECTURE: the live market day and the year's price study (docs/plans/architecture-x.md, amendment 15).
    ('A', 'it took {} filings from {} companies', lambda: ev('ingest_day.txt', r'filings (\d+), companies (\d+)')),
    ('A', 'Rules settled {}.', lambda: ev('ingest_day.txt', r'settled by rules (\d+)')),
    ('A', 'Rules settled {}. The other {} wait for a key', lambda: (lambda m: (m[0], int(m[1]) - int(m[0])))(ev('ingest_day.txt', r'settled by rules (\d+) of (\d+)'))),
    ('A', 'a day of {} filings', lambda: ev('ingest_day.txt', r'filings (\d+),')),
    ('A', 'the parked model work comes to {}–{} calls, ${}–{}', lambda: ev('ingest_day.txt', r'estimate\): (\d+)-(\d+) model calls .*? = \$([\d.]+)-([\d.]+)')),
    ('AP', 'the stock moved {}× as often as on days they fold (95% CI {}–{})',
     lambda: ev('reaction_result.txt', r'lead: act moved ([\d.]+)x as often as fold \(95% CI ([\d.]+)-([\d.]+)\)')),
    ('AP', '{}× (95% CI {}–{}), on {} company-days',
     lambda: ev('reaction_result.txt', r'lead without results: ([\d.]+)x \(95% CI ([\d.]+)-([\d.]+)\); act without results (\d+)')),
    ('A', 'Stocks moved {}× as often after filings FINN acts on', lambda: ev('reaction_result.txt', r'lead: act moved ([\d.]+)x as often as fold')),
    ('A', '{} interrupts a week from rules alone, up to {}', lambda: ev('reaction_result.txt', r'interrupts a week, 20-stock book: median ([\d.]+) .*?up to ([\d.]+)')),
    ('AP', '{} rule-settled act days a week (90th percentile {})', lambda: ev('reaction_result.txt', r'median ([\d.]+) \(90th percentile ([\d.]+)\)')),
    ('AP', '{} survive Benjamini', lambda: ev('reaction_result.txt', r'named misses: (\d+ of \d+) subjects')),
    ('P', 'Investor presentations (note, {}×) come closest, at p = {} alone', lambda: (lambda m: (m[0], f"{float(m[1]):.3f}"))(   # the first exploratory line is the closest
        ev('reaction_result.txt', r'exploratory, post hoc: [^\n]*\nexploratory \[note\] Investor Presentation: lift ([\d.]+) [^\n]*?p ([\d.]+) against 2.0'))),
    ('AP', 'PR-AUC of {}', lambda: ev('c2_result.txt', r'text model: PR-AUC ([\d.]+)')),
    ('AP', 'on {} vague filings', lambda: (f"{int(ev('c2_result.txt', r'population: (\d+)')[0]):,}",)),
    ('AP', 'every NSE filing ({}, ', lambda: (f"{J('evals/reaction_meta.json')['filings']:,}",)),
    ('A', 'a year of {} filings and their prices', lambda: (f"{J('evals/reaction_meta.json')['filings']:,}",)),
    ('P', 'act {}% of {} moved, note {}% of {}, fold {}% of {}', lambda: (lambda m: (m[0], m[1], m[4], m[5], m[2], m[3]))(
        ev('reaction_result.txt', r'shipped tiers, small n\): act (\d+)% of (\d+), fold (\d+)% of (\d+), note (\d+)% of (\d+)'))),
    ('P', '{} such company-days get no verdict', lambda: (f"{int(ev('reaction_result.txt', r'rate needs the reading: .*? n (\d+)')[0]):,}",)),
    ('P', 'reads the {} waiting company-days', lambda: (f"{int(ev('reaction_result.txt', r'rate needs the reading: .*? n (\d+)')[0]):,}",)),
]

fails, covered = [], {d: [] for d in DOC}
text = lambda d: T(DOC[d]) if (R / DOC[d]).exists() else None
for docs, phrase, val, *rest in CLAIMS:
    cond, fb = (rest + ['repo', None])[:2]
    WHERE.clear(); v = list(val()); want = re.sub(r'\{\}', lambda m: str(v.pop(0)), phrase)
    for d in docs:
        t = text(d)
        if t is None:
            continue
        said = re.search(r'\s+'.join(map(re.escape, fb.split())), t) if fb else None
        if said:                                   # the document says what the link does today instead
            covered[d].append(said.span()); continue
        spans = [m.span() for m in re.finditer(re.escape(want), t, re.I)]
        if spans:
            covered[d] += spans; continue
        m = re.search(re.escape(phrase).replace(r'\{\}', r'([\w.,$−+]+)'), t, re.I)
        fails.append(f"{DOC[d]}: says '{m.group(0)}', data says '{want}'" if m else f"{DOC[d]}: missing '{want}'")
    print(f"{cond:12} {want}" + (f"   [{WHERE[0]}]" if WHERE else '') + (f"   [else: {fb}]" if fb else ''))

pdfs = sorted(glob.glob(str(pathlib.Path.home() / 'ENAM-FINN/network_brief/*.pdf')))
BRIEF = re.sub(r'\s+', ' ', ' '.join(subprocess.run(['pdftotext', p, '-'], capture_output=True, text=True).stdout for p in pdfs)).lower()
flat = lambda s: re.sub(r'\s+', '', s)
SCREEN = [flat(s) for s in re.findall(r'`([^`]+)`', text('W') or '')]
MONTH = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
ALLOW = [r'```sh.*?```', r'`[^`\n]+`', r'https?://\S+', r'\]\([^)]*\)', r'<[^>]+>', r'(?m)^\s*\d+\.\s', r'(?m)^#+ (?:\d+[a-z]?\.)?', r'(?m)^\| \d+ \|',
         rf'\b\d{{1,2}} {MONTH}(?: \d{{4}})?', rf'{MONTH} [’\']?\d{{2,4}}', r'\b\d{1,2}:\d{2}(?: ?[ap]m)?', r'\b(?:19|20)\d\d\b',
         r'\b(?:Q[1-4]|H[12]|FY ?\d\d|CY ?\d\d)\b', r'390×844', r'[’\']\d\d\b', r'gemini-[\w.-]+', r'\b(?:Fable|Opus|Sonnet|Haiku) \d\.\d\b']
NUM = re.compile(r'(?<![\w.])[−+-]?[₹$]?\d[\d,]*(?:\.\d+)?|\b(?:' + '|'.join(WORDS[2:]) + r'|thirty|forty|fifty|hundred|thousand|million)\b', re.I)
for d in DOC:
    t = text(d)
    if t is None:
        continue
    keep = [True] * len(t)
    for a, b in covered[d] + [m.span() for rx in ALLOW for m in re.finditer(rx, t, re.S)]:
        keep[a:b] = [False] * (b - a)
    for m in re.finditer(r'[“"]([^”"\n]+)[”"]', t):      # quoted from the brief, or part of an on-screen string
        q = m.group(1)
        if re.sub(r'\s+', ' ', q).lower() in BRIEF or any(flat(q) in s for s in SCREEN):
            keep[m.start():m.end()] = [False] * (m.end() - m.start())
    for m in NUM.finditer(t):
        if all(keep[m.start():m.end()]):
            (fails.append if d in STRICT else print)(f"{DOC[d]}: unclaimed {m.group(0)!r} in '…{t[max(0, m.start() - 30):m.end() + 20]}…'".replace('\n', ' '))

# Every eval count a document states, against that eval's own result file: "`run_x.py` 20/20", "Last run: 20/20 (`x_result.txt`)".
def total(name):
    f = R / 'evals' / f'{name}_result.txt'
    m = re.findall(r'TOTAL (\d+)/(\d+)', f.read_text()) if f.exists() else []
    return '/'.join(m[-1]) if m else None
COUNTED = list(DOC.values()) + ['evals/README.md', 'docs/INTERVIEW_DEFENSE.md'] + sorted(str(pathlib.Path(f).relative_to(R)) for f in glob.glob(str(R / 'docs/adr/*.md')))
n_counts = 0
for f in COUNTED:
    if not (R / f).exists():
        continue
    for m in re.finditer(r'run_(\w+)\.py`?\)?,? (\d+/\d+)|Last run: (\d+/\d+) \(`(\w+)_result\.txt`\)', T(f)):
        name, said = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        got = total(name); n_counts += got is not None
        if got and got != said:
            fails.append(f"{f}: says {name} {said}, evals/{name}_result.txt says {got}")
print(f"counts       {n_counts} eval counts in the documents checked against their result files")

# Every ADR keeps the template: five headings, at least two rejected options with a reason, a number to revisit at.
for f in sorted(glob.glob(str(R / 'docs/adr/*.md'))):
    t, name = pathlib.Path(f).read_text(), pathlib.Path(f).name
    heads = re.findall(r'(?m)^## (.+)$', t)
    for h in ('Context', 'Options', 'Decision', 'Trade-offs', 'Revisit when'):
        if h not in heads:
            fails.append(f"docs/adr/{name}: no '## {h}'")
    opts = re.search(r'(?ms)^## Options\n(.*?)^## ', t)
    if not opts or len(re.findall(r'Rejected\b[^.]*?[:,.]\s*\S', opts.group(1))) < 2:
        fails.append(f"docs/adr/{name}: fewer than two rejected options with a reason")
    rev = re.search(r'(?ms)^## Revisit when\n(.*?)(?=^## |\Z)', t)
    if not rev or not re.search(r'\d', rev.group(1)):
        fails.append(f"docs/adr/{name}: 'Revisit when' has no number")
print(f"adr          {len(glob.glob(str(R / 'docs/adr/*.md')))} ADRs checked against the template")

# Sentences that were true and then weren't. RETIRED fails anywhere a grader reads it, and in the served label;
# the build history may tell the past in the past tense, so only phrases marked 'H' fail there too.
# PENDING is true now and fails once ROADMAP marks the named task done, so the task that builds it fixes the note.
RETIRED = {'names a person and stops': '', 'names the person and why, and stops': '', "can't raise a card": '',
           'synthetic profile': '', 'now hidden': '', 'years that overlap': '', 'the public repo is one commit': 'H',
           'two departures at crompton': '', 'two small departures': '',
           'demo · 28 oct': '', 'opening the ledger': ''}
PENDING = {'annual-report': ["annual reports aren't read yet", 'no annual reports yet', 'annual reports are listed but not yet read']}
SUBMIT = {f: T(f) for f in [DOC[d] for d in 'NRWTA'] + ['docs/FINAL_CHECKLIST.md'] + sorted(
    str(pathlib.Path(f).relative_to(R)) for f in glob.glob(str(R / 'docs/adr/*.md'))) if (R / f).exists()}
SUBMIT['label in network.json'] = NET.get('label', '')
SUBMIT['label in investor.json'] = J('data/network/investor.json').get('label', '')
norm = lambda s: s.replace('’', "'").lower()
for phrase, also in RETIRED.items():
    for f, t in list(SUBMIT.items()) + ([(DOC['H'], T(DOC['H']))] if 'H' in also else []):
        if phrase in norm(t):
            fails.append(f"{f}: retired phrase '{phrase}' (true once, false now)")
row = lambda task: next((l.split('|')[-2].strip() for l in T('docs/ROADMAP.md').splitlines() if f'| `{task}` |' in l), '')
for task, phrases in PENDING.items():
    if row(task).startswith('done'):
        for phrase in phrases:
            for f, t in SUBMIT.items():
                if phrase in norm(t):
                    fails.append(f"{f}: '{phrase}' is false now that `{task}` is done")
print(f"retired      {len(RETIRED)} retired and {sum(map(len, PENDING.values()))} pending phrases over {len(SUBMIT)} texts")

# The note's body (after the subject, before the two signature lines), as the email reads it: no image, no link targets.
lines = T(DOC['N']).splitlines()
sub = next(i for i, l in enumerate(lines) if l.startswith('**Subject:**'))
sig = [i for i, l in enumerate(lines) if l.strip()][-2]
body = re.sub(r'\]\([^)]*\)', ']', re.sub(r'(?m)^!\[.*$', '', '\n'.join(lines[sub + 1:sig])))
n_words = len([x for x in body.split() if re.search(r'\w', x)])
print(f"note         {n_words} words in the body, cap 950")
if n_words > 950:
    fails.append(f"{DOC['N']}: {n_words} words in the body, over the cap of 950")

print('\n'.join(['', *fails, f"{len(fails)} failed" if fails else 'all claims hold']))
sys.exit(1 if fails else 0)
