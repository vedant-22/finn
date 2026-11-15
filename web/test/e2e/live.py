# The architecture task's live checks, run right after a deploy. Then run flows.py against the same base.
# usage: python3 web/test/e2e/live.py [base] [--presend [--no-key]]   (default: finn-network). Exits 1 if one fails.
# The network answers must equal what the committed code gives locally, so the live link runs this commit.
# --presend is the gate before the email (docs/NEEDS_FROM_USER.md): also this commit's build and share tags, a
# company outside the 22 read live, the public repo on `submission`, and no unfiled profile field on the link.
# --presend asks the link whether it has a model key (/api/sources {"op": "status"}). With none, it runs the no-key
# checks (the link says reading is off, and the note and README use claims.py's fallback sentences) in place of the
# key's; with one, the note must no longer say reading is off. --no-key forces the no-key checks. It also fetches
# every URL in send/email.txt (python3 evals/ship.py --kit), so the body the grader reads first has no dead link,
# downloads the bundle link signed out and compares it with the bundle the kit made, and compares every file under
# web/public/data with what the link serves (a data-only commit leaves the JS file's name as it was).
import hashlib, json, os, re, subprocess, sys, time, urllib.error, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, ROOT)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
PRESEND, NOKEY = '--presend' in sys.argv, '--no-key' in sys.argv
base = (args[0] if args else 'https://finn-network.vercel.app').rstrip('/')
OLD_BUILD, LEDGER, LEDGER_BUILD = 'index-B42OWfM3.js', 'https://finn-ledger.vercel.app', 'index-o-FI1f7s.js'
fails = []
def check(name, ok, got=''):
    print(('ok   ' if ok else 'FAIL ') + name + (f'  [{got}]' if got != '' else ''))
    if not ok: fails.append(name)
def warn(name):
    print('WARN ' + name)
def strings(o):
    if isinstance(o, dict): o = list(o.values())
    return [s for v in o for s in strings(v)] if isinstance(o, list) else [] if o is None else [str(o)]

def get(url, body=None):
    r = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                               {'Content-Type': 'application/json'} if body is not None else {})
    try:
        with urllib.request.urlopen(r, timeout=60) as f:
            return f.status, {k.lower(): v for k, v in f.headers.items()}, f.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode()

def fetch(url):
    """(status, the URL it ended at after redirects, the body as bytes)"""
    try:
        with urllib.request.urlopen(url, timeout=120) as f:
            return f.status, f.geturl(), f.read()
    except urllib.error.HTTPError as e:
        return e.code, e.geturl(), b''
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, url, b''

def direct(url):
    """A Drive share link as the file's own download, as a signed-out reader gets it; any other link as it is."""
    m = re.search(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:[^#]*&)?id=)([\w-]+)', url)
    return f'https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t' if m else url

def build(url):
    m = re.search(r'assets/(index-[^"]+\.js)', get(url + '/')[2])
    return m.group(1) if m else ''

# 1. the new build is live
live = build(base)
local = next((f for f in os.listdir(os.path.join(ROOT, 'web/dist/assets')) if re.match(r'index-.*\.js$', f)), '?')
check('a new build is live', live and live != OLD_BUILD, f'live {live}, local {local}')
if PRESEND:
    check("the live build is this commit's (npm run build, then deploy)", live == local, f'live {live}, local {local}')
    check('share tags point at finn-network', 'og:url" content="https://finn-network.vercel.app/' in get(base + '/')[2])
    data = subprocess.run(['git', 'ls-files', 'web/public/data'], cwd=ROOT, capture_output=True, text=True).stdout.split()
    stale = [p[len('web/public/data/'):] for p in data
             if fetch(base + '/' + p[len('web/public/'):])[2] != subprocess.run(['git', 'show', f'HEAD:{p}'], cwd=ROOT, capture_output=True).stdout]
    check(f"the link serves this commit's {len(data)} data files", data and not stale, f'{len(stale)} differ: {", ".join(stale[:4])}' if stale else '')

# 2. headers, from vercel.json
cfg = json.load(open(os.path.join(ROOT, 'vercel.json')))['headers']
want = {h['key'].lower(): h['value'] for h in cfg[0]['headers']}
_, hd, _ = get(base + '/')
for k, v in want.items():
    check(f'header {k}', hd.get(k) == v, hd.get(k, 'missing')[:60])
_, hd, _ = get(base + '/data/network.json')
check('X-Robots-Tag noindex on /data/', hd.get('x-robots-tag') == 'noindex', hd.get('x-robots-tag', 'missing'))
s, _, txt = get(base + '/robots.txt')
check('/robots.txt keeps /data/ and /api/ out', s == 200 and 'Disallow: /data/' in txt and 'Disallow: /api/' in txt, s)

# 3. a grade naming URLs the server never listed keeps none of them (no key: refused before any fetch)
foreign = [{'url': f'https://example.com/{i}.pdf', 'period': 'Jan 2020', 'promises': [{'text': 'x'}]} for i in (1, 2)]
s, _, txt = get(base + '/api/grade', {'src': {'symbol': 'LT'}, 'calls': foreign})
no_key = s == 503 and json.loads(txt or '{}').get('error') == 'no_key'
check('grade with foreign URLs keeps none', no_key or (s in (200, 503) and 'example.com' not in txt), f'{s} {txt[:80]}')

# 4. the network answers equal the committed code's
from api.network import run
tsx = open(os.path.join(ROOT, 'web/src/Network.tsx')).read()
STARTERS = re.findall(r"'([^']+)'", re.search(r'NET_STARTERS = \[(.*?)\]', tsx).group(1))
check('the four starter questions read', len(STARTERS) == 4, STARTERS)
said = []
for body in [{'op': 'ask', 'q': q} for q in STARTERS] + [{'op': 'notices'}]:
    s, _, txt = get(base + '/api/network', body)
    check(f"network {body.get('q', 'notices')}", s == 200 and json.loads(txt) == run(body), s)
    said += strings(json.loads(txt)) if s == 200 else []

# 5. a company outside the built ones: read live, or, with no key, says so at once
s, _, txt = get(base + '/api/sources', {'op': 'status'})
KEYED = s == 200 and json.loads(txt or '{}').get('live') is True
if PRESEND and not KEYED and not NOKEY:
    print('the link has no model key: the no-key checks run in place of the key\'s (docs/NEEDS_FROM_USER.md, step 1)')
    NOKEY = True
if PRESEND and not NOKEY:
    s, _, txt = get(base + '/api/sources', {'symbol': 'MARICO'})
    d = json.loads(txt or '{}') if s == 200 else {}
    check('a company outside the 22 gets its calls listed (needs the key)', d.get('live') and len(d.get('transcripts') or []) > 0,
          f"{s} live={d.get('live')} calls={len(d.get('transcripts') or [])}")
elif no_key:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
        pg.goto(base + '/#/c/MARICO', wait_until='domcontentloaded'); t0 = time.time()
        try:
            pg.get_by_text('Reading new companies is off for now.').first.wait_for(timeout=2000); dt = time.time() - t0
            line = pg.get_by_text('Reading new companies is off for now.').first.inner_text()
            check('MARICO with no key says so within 2 s', 'already in FINN still open' in line, f'{dt:.2f} s: {line[:90]}')
        except Exception as e:
            check('MARICO with no key says so within 2 s', False, str(e).splitlines()[0][:90])
        b.close()
else:
    print('skip MARICO no-key check: the live link has a model key')

if PRESEND:             # every number holds, and both no-key claims are read below
    cl = subprocess.run([sys.executable, os.path.join(ROOT, 'evals/claims.py')], capture_output=True, text=True)
    check('claims.py holds (python3 evals/claims.py)', cl.returncode == 0, cl.stdout.strip().splitlines()[-1:] if cl.stdout.strip() else cl.stderr[-200:])
    check('claims.py lists both no-key claims', len(re.findall(r'(?m)^needs-key ', cl.stdout)) == 2)
if PRESEND and NOKEY:   # the note must not promise live reading
    out = cl.stdout
    docs = ' '.join(' '.join(open(os.path.join(ROOT, f)).read().split()) for f in ('docs/COVERING_NOTE.md', 'README.md'))
    for fb in re.findall(r'(?m)^needs-key .*\[else: (.*)\]$', out):
        check(f'the note or README carries the no-key sentence: {fb[:50]}', ' '.join(fb.split()) in docs)
elif PRESEND:           # the link reads live, so the note must not say it doesn't
    out = cl.stdout
    docs = ' '.join(' '.join(open(os.path.join(ROOT, f)).read().split()) for f in ('docs/COVERING_NOTE.md', 'README.md'))
    for ph, fb in re.findall(r'(?m)^needs-key\s+(.*?)\s{3}\[.*\[else: (.*)\]$', out):
        check(f'the note and README no longer say reading is off: {fb[:50]}', ' '.join(fb.split()) not in docs)
        check(f'the note or README says it reads live: {ph}', ' '.join(ph.split()) in docs)

# 6. before sending: the repo, and real people carry only what their filings say
if PRESEND:
    s, _, txt = get('https://api.github.com/repos/vedant-22/finn')
    g = json.loads(txt or '{}') if s == 200 else {}
    check('the repo is public, default branch submission', g.get('private') is False and g.get('default_branch') == 'submission',
          f"{s} private={g.get('private')} default={g.get('default_branch')}")
    # Filed fields only: no earlier job or school of a person in a filing carries a year on the link
    FL = json.load(open(os.path.join(ROOT, 'data/network/filings.json')))['filings']
    names = sorted({q['name'] for f in FL for q in f.get('people', []) if q.get('verified')})[:12]
    dated = []
    for nm in names:
        s, _, txt = get(base + '/api/network', {'op': 'ask', 'q': f'Brief me on {nm}'})
        a = json.loads(txt or '{}') if s == 200 else {}
        co = a.get('title', '').split(', ', 1)[-1]          # the new seat is dated by its filing; someone you know, by your record
        if a.get('intent') == 'diligence' and not any(n.startswith('This is the ') for n in a.get('notes', [])):
            dated += [(nm, r['name'], r['sub']) for r in a.get('rows', []) if r.get('sub') and r['name'] != co] + [(nm, e['school'], e['years']) for e in a.get('edu', []) if e.get('years')]
    check('no year on a filing person\'s earlier job or school, on the link', not dated, dated[:3])

    # What is pushed is what ship.py checked, and the email is the note as committed now
    import importlib.util
    spec = importlib.util.spec_from_file_location('ship', os.path.join(ROOT, 'evals', 'ship.py'))
    ship = importlib.util.module_from_spec(spec); spec.loader.exec_module(ship)
    _, tree = ship.build_tree()
    s, _, txt = get('https://api.github.com/repos/vedant-22/finn/branches/submission')
    pushed = (json.loads(txt or '{}').get('commit') or {}).get('commit', {}).get('tree', {}).get('sha') if s == 200 else None
    check('submission on GitHub holds this commit\'s checked snapshot', pushed == tree, f'{s} pushed={str(pushed)[:7]} snapshot={tree[:7]}')
    mail, made = os.path.join(ROOT, 'send', 'email.txt'), os.path.join(ROOT, 'send', 'kit.json')
    kit = json.load(open(made)) if os.path.exists(made) else None
    note = open(os.path.join(ROOT, 'docs', 'COVERING_NOTE.md')).read()
    if not os.path.exists(mail) or kit is None:
        check('send/ holds the kit (python3 evals/ship.py --kit)', False)
    elif kit['head'] != subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        check('the kit was made from this commit (rerun python3 evals/ship.py --kit)', False, kit['head'][:7])
    elif kit['fails']:
        check('the kit passed its own checks', False, '; '.join(kit['fails'])[:300])
    elif ship.BUNDLE in note and not kit['bundle_url']:
        check('the email links the bundle it promises (ship.py --kit --bundle-url <link>)', False)
    elif open(mail).read() != ship.email(note, kit['bundle_url'])[1]:
        check('send/email.txt is the note as it stands (rerun python3 evals/ship.py --kit)', False)
    else:
        if kit['bundle_url'] and ship.BUNDLE in note:     # a link kept from before the bundle was dropped isn't checked
            st, end, body = fetch(direct(kit['bundle_url']))
            check('the bundle link gives a signed-out reader the bundle this kit made (share it as anyone with the link; '
                  'after a new commit and kit, upload the new one)',
                  st == 200 and 'accounts.google.com' not in end and hashlib.sha256(body).hexdigest() == kit.get('bundle_sha256'),
                  f'{st}, {len(body)} bytes, ended at {end[:60]}')
        for u in sorted(set(re.findall(r'https?://[^\s)<>"]+[^\s)<>".,]', open(mail).read()))):
            s = get(u)[0]
            check(f'the email\'s link answers: {u.replace("https://", "")}', s == 200, s)

# 7. the other project is untouched
check('finn-ledger unchanged', build(LEDGER) == LEDGER_BUILD, build(LEDGER))
print(f'\n{len(fails)} failed' if fails else '\nall passed; now: python3 web/test/e2e/flows.py ' + base)
sys.exit(1 if fails else 0)
