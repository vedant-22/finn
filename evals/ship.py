"""The public snapshot, checked, and the kit to send.

  python3 evals/ship.py           builds the tree of `network`'s HEAD without the interview prep, through a temporary
                                  index (no checkout), and checks that tree's own blobs: no secret by its shape, no home
                                  path, no private address, no base-design name, every relative link resolving inside
                                  the tree, the synthetic label in the note, README and network label
  python3 evals/ship.py --write   then points the local branch `submission` at one commit of that tree, with no parent
                                  (never a push); an existing `submission` is moved only if this script made it
  python3 evals/ship.py --kit     then writes send/ (gitignored): the email body as text and HTML, the diagram, the build
                                  history exported from every session folder, the git bundle, and REPORT.txt
Refuses a dirty working tree, so what it checks is what is committed. Exits 1 if a check fails.
"""
import gzip, hashlib, html, importlib.util, json, os, pathlib, re, shutil, subprocess, sys, tempfile
R = pathlib.Path(__file__).resolve().parent.parent
HOME = pathlib.Path.home()
LEAVE_OUT = ['docs/INTERVIEW_DEFENSE.md']          # the user's preparation (ROADMAP, "Decided"); the bundle still has it
REPO = 'https://github.com/vedant-22/finn'
EXPORTER = HOME / 'ENAM-FINN/export_history.py'   # its redaction holds the base-design name, so the name never sits here
SESSIONS = [('October app', '-Users-vedantiwari-ENAM-FINN-app'), ('motion', '-Users-vedantiwari-ENAM-FINN-motion'),
            ('network', '-Users-vedantiwari-ENAM-FINN-network')]
MADE_BY = 'Made-by: evals/ship.py'
MAIL_LIMIT = 25 * 1024 * 1024

# Shapes, built from pieces so this file doesn't match itself.
KEYS = [re.compile('AIza' + r'[0-9A-Za-z_\-]{35}'), re.compile('gh' + r'p_[0-9A-Za-z]{36}'),
        re.compile('github' + r'_pat_[0-9A-Za-z_]{22,}'), re.compile('-' * 5 + 'BEGIN' + r' [A-Z ]*PRIVATE KEY')]
# The person's own phone and enrolment numbers, found by their labels in a private transcript outside the repo and
# read at run time, so the numbers are never written here; the export is then scanned for those exact values
PERSONAL = re.compile(r'(?i)(?:phone|mobile|whatsapp|enrol+ment|roll n(?:o|umber))\b[^\n\d]{0,40}(?:\+91[\s-]?)?\d{5,10}\b'
                      r'|\b(?:\+91[\s-]?)?[6-9]\d{9}\b[^\n\d]{0,20}(?:is my|my) (?:phone|mobile|number)')
def own_numbers():
    src = sorted((HOME / 'ENAM-FINN').glob('2026-10-28-*desktop-app.txt'))
    return {max(re.findall(r'\d{5,10}', m), key=len) for f in src for m in PERSONAL.findall(f.read_text(errors='ignore'))} if src else None

KEY_VAR = re.compile('GEMINI_API' + r'_KEY=["\']?([^\s"\'`]*)')   # a value right after the '='; a space after it is prose
PLACEHOLDER = {'', '...', 'your-key-here'}
HOME_PATH = re.compile('/' + 'Users/[a-z]')
fails, warns = [], []
def unzip(body):
    """A gzip blob as the text it holds (the fixtures are .json.gz and .csv.gz), so a scan sees inside it."""
    if body[:2] == b'\x1f\x8b':
        try:
            return gzip.decompress(body)
        except (OSError, EOFError):
            pass
    return body

def check(ok, what, detail=''):
    print(('ok   ' if ok else 'FAIL ') + what + (f'  [{detail}]' if detail and not ok else ''))
    ok or fails.append(what)

def git(*a, env=None, inp=None, raw=False):
    out = subprocess.run(['git', *a], cwd=R, env=env, input=inp, capture_output=True, check=True)
    return out.stdout if raw else out.stdout.decode().strip()

def exporter():
    if not EXPORTER.exists():
        return None
    spec = importlib.util.spec_from_file_location('export_history', EXPORTER)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)   # main() is guarded; nothing runs
    return mod

def design_rx(mod):
    return next((rx for rx, rep in getattr(mod, 'REDACT', []) if rep == '[reference design]'), None) if mod else None

def masker():
    """Every organisation and school the registry knows, blanked before the design-name scan: a real place name
    inside a real institution's name is not the design name."""
    reg = json.loads((R / 'data/network/registry.json').read_text())
    names = sorted({n for o in reg['orgs'] + reg['schools'] for n in [o['name'], *o.get('aka', [])]}, key=len, reverse=True)
    rx = re.compile('|'.join(map(re.escape, names)), re.I)
    return lambda t: rx.sub(lambda m: ' ' * len(m.group(0)), t)

def build_tree():
    head = git('rev-parse', 'HEAD')
    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, 'GIT_INDEX_FILE': os.path.join(td, 'index')}
        git('read-tree', head, env=env)
        for f in LEAVE_OUT:
            git('rm', '--cached', '-q', '--ignore-unmatch', f, env=env)
        return head, git('write-tree', env=env)

def blobs(tree):
    """{path: text} for every text blob in the tree, read from git, not from the working copy."""
    ents = [l.split('\t', 1) for l in git('ls-tree', '-r', '-z', tree, raw=True).decode().split('\0') if l]
    ents = [(meta.split()[2], path) for meta, path in ents if meta.split()[1] == 'blob']
    out = git('cat-file', '--batch', inp=''.join(s + '\n' for s, _ in ents).encode(), raw=True)
    texts, i = {}, 0
    for sha, path in ents:
        nl = out.index(b'\n', i); size = int(out[i:nl].split()[2]); body = unzip(out[nl + 1:nl + 1 + size]); i = nl + 2 + size
        if b'\0' not in body[:8000]:
            texts[path] = body.decode('utf-8', 'replace')
    return [p for _, p in ents], texts

def where(t, pos):
    return t[:pos].count('\n') + 1

def scan(texts, signature_file='docs/COVERING_NOTE.md'):
    """The checks every snapshot must pass. Returns nothing; records fails."""
    hits = [f'{p}:{where(t, m.start())}' for p, t in texts.items() for rx in KEYS for m in rx.finditer(t)]
    check(not hits, 'no key-shaped string (Google, GitHub, private key)', ', '.join(hits[:5]))
    hits = [f'{p}:{where(t, m.start())}' for p, t in texts.items() for m in KEY_VAR.finditer(t) if m.group(1) not in PLACEHOLDER]
    check(not hits, 'GEMINI_API_KEY= only ever empty or a placeholder', ', '.join(hits[:5]))
    hits = [f'{p}:{where(t, m.start())}' for p, t in texts.items() if not p.startswith('docs/plans/') for m in HOME_PATH.finditer(t)]
    check(not hits, 'no home path outside docs/plans/', ', '.join(hits[:5]))
    mine = {a.lower() for a in (git('config', 'user.email'), git('log', '-1', '--format=%ae')) if a}
    sig = texts.get(signature_file, '').rstrip().splitlines()[-1:]           # the note's last line is its signature
    hits = [p for p, t in texts.items() for a in mine
            if a in (t.replace(sig[0], '') if p == signature_file and sig else t).lower()]
    check(not hits, "the git author's address appears nowhere but the note's signature", ', '.join(hits[:5]))
    mod = exporter(); rx = design_rx(mod)
    if rx is None:     # fails closed: without the pattern nothing can say the name is absent
        check(False, f'the base-design name check runs (needs {EXPORTER} and its "[reference design]" pattern)')
    else:
        mask = masker()
        hits = [f'{p}:{where(t, m.start())}' for p, t in texts.items() for mt in [mask(t)]
                for m in rx.finditer(mt) if not FILED.match(mt, m.end())]
        check(not hits, 'no base-design name (matched by the exporter\'s pattern, the name not printed)', ', '.join(hits[:5]))

def links(paths, texts):
    files = set(paths); dirs = {str(pathlib.PurePosixPath(p).parent) for p in paths}
    bad, prep = [], []
    for p, t in texts.items():
        if not p.endswith('.md'):
            continue
        for m in re.finditer(r'\]\(([^)\s]+)\)', t):
            u = m.group(1).split('#')[0].split('?')[0]
            if not u or re.match(r'[a-z]+:', u):
                continue
            if any(u.endswith(x.split('/')[-1]) for x in LEAVE_OUT):
                prep.append(f'{p}:{where(t, m.start())}')
            q = os.path.normpath(os.path.join(os.path.dirname(p), u.lstrip('/') if u.startswith('/') else u))
            if q not in files and q not in dirs:
                bad.append(f'{p}:{where(t, m.start())} -> {u}')
    check(not prep, 'no link to the interview prep, which the snapshot leaves out', ', '.join(prep[:5]))
    check(not bad, 'every relative markdown link resolves inside the snapshot', '; '.join(bad[:6]))

def snapshot():
    if git('status', '--porcelain', '--untracked-files=no'):
        sys.exit('the working tree has uncommitted changes: commit them first, so the snapshot is what is checked')
    if git('rev-parse', 'HEAD') != git('rev-parse', 'network'):
        sys.exit('HEAD is not the branch network')
    head, tree = build_tree()
    paths, texts = blobs(tree)
    print(f'snapshot of network {head[:7]}: tree {tree[:7]}, {len(paths)} files, {", ".join(LEAVE_OUT)} left out')
    check(not any(p in paths for p in LEAVE_OUT), 'the interview prep is not in the tree')
    env = [p for p in paths if re.search(r'(^|/)\.env(\.|$)', p) and not p.endswith('.env.example')]
    check(not env, 'no .env file in the tree', ', '.join(env))
    scan(texts)
    links(paths, texts)
    label = json.loads(texts['web/public/data/network.json']).get('label', '')
    for name, t in [('the note', texts.get('docs/COVERING_NOTE.md', '')), ('README', texts.get('README.md', '')), ('the network label', label)]:
        check(re.search(r'\b(synthetic|invented)\b', t, re.I), f'{name} says synthetic or invented')
    names = real_people()
    look = {}
    for p, t in texts.items():
        for n in names:
            for m in re.finditer(re.escape(n), t):
                if re.search(r'\b(?:19|20)\d\d\b', t[max(0, m.start() - 60):m.end() + 60]):
                    look[p] = look.get(p, 0) + 1
    sub_ = subprocess.run(['git', 'rev-parse', '--verify', '-q', 'submission^{tree}'], cwd=R, capture_output=True, text=True).stdout.strip()
    if sub_ and sub_ != tree and '--write' not in sys.argv:
        warns.append(f'WARN: the local branch submission holds an older tree ({sub_[:7]}): run python3 evals/ship.py --write')
    print(f'look a year within 60 characters of {len(names)} real executives once given invented profiles, by file (a filed date is allowed):')
    for p, n in sorted(look.items(), key=lambda x: -x[1])[:8]:
        print(f'       {n:4}  {p}')
    return head, tree, texts

# Filed annual-report pages (evals/fixtures) print three real institutions whose names begin with the same
# place name: a stock exchange and two companies in related-party and freight tables. Filed text, not ours.
FILED = re.compile(r'\s+(?:Stock Exchange|Rayon Fashions|Tubes and Poles)\b')
named = lambda rx, t: any(not FILED.match(t, m.end()) for m in rx.finditer(t))

def past(ref):
    """Every text blob and commit message ever reachable from ref, as a clone or a bundle of it carries them, scanned
    for the base-design name (registry names masked) and key shapes. Returns (blob paths, introducing commits, messages, any key)."""
    rx, mask = design_rx(exporter()), masker()
    if rx is None:
        return None
    objs = [l.split(' ', 1) for l in git('rev-list', '--objects', ref).splitlines()]
    path = {o[0]: o[1] for o in objs if len(o) == 2}
    info = git('cat-file', '--batch-check=%(objectname) %(objecttype)', inp=('\n'.join(o[0] for o in objs) + '\n').encode()).splitlines()
    shas = [l.split()[0] for l in info if l.endswith(' blob')]
    out = git('cat-file', '--batch', inp=('\n'.join(shas) + '\n').encode(), raw=True)
    hit, keyed, i = [], False, 0
    while i < len(out):
        nl = out.index(b'\n', i); sha, _, size = out[i:nl].decode().split(); size = int(size)
        body = unzip(out[nl + 1:nl + 1 + size]); i = nl + 2 + size
        if b'\0' in body[:8000]:
            continue                      # binary: a match in compressed bytes is noise
        t = body.decode('utf-8', 'replace')
        k = any(k.search(t) for k in KEYS)
        if k or named(rx, mask(t)):
            hit.append(sha); keyed = keyed or k
    first = sorted({git('log', '--format=%h', '--reverse', '--find-object=' + s, ref).split('\n')[0] for s in hit} - {''})
    msgs = [m.split('\0')[0][:7] for m in git('log', '--format=%H%x00%B%x01', ref).split('\x01')
            if '\0' in m and (named(rx, mask(m.split('\0', 1)[1])) or any(k.search(m) for k in KEYS))]
    keyed = keyed or any(k.search(git('log', '--format=%B', ref)) for k in KEYS)
    # the 4th item is not a hit list: True when any hit is a key, which --accept-history never covers
    return sorted({rx.sub('[name]', path.get(s, s)) for s in hit}), first, msgs, keyed

def real_people():
    """The names on the profiles `network-loop` deleted, read from the commit before the deletion."""
    try:
        gone = git('log', '--diff-filter=D', '--format=%H', '-1', '--', 'data/network/profiles.json')
        d = json.loads(git('show', f'{gone}^:data/network/profiles.json'))
        return sorted({p['name'] for p in d['profiles']})
    except (subprocess.CalledProcessError, KeyError, ValueError):
        return []

def write(head, tree):
    old = subprocess.run(['git', 'rev-parse', '--verify', '-q', 'refs/heads/submission'], cwd=R, capture_output=True, text=True).stdout.strip()
    if old:
        if MADE_BY not in git('log', '-1', '--format=%B', old):
            sys.exit(f'submission ({old[:7]}) was not made by evals/ship.py: look at it first; nothing moved')
        if git('rev-parse', f'{old}^{{tree}}') == tree:
            print(f'submission {old[:7]} already holds this tree; nothing to do'); return old
    msg = f'FINN, for the Founding AI Engineer brief\n\nOne commit of the network branch\'s tree, without {", ".join(LEAVE_OUT)}.\n\nSource: network {head}\n{MADE_BY}\n'
    new = git('commit-tree', tree, inp=msg.encode())
    git('update-ref', 'refs/heads/submission', new, *([old] if old else []))
    n = git('rev-list', '--count', 'submission')
    check(n == '1' and git('rev-parse', 'submission^{tree}') == tree, f'submission {new[:7]}: one commit, the checked tree', f'{n} commits')
    return new

# ---- the kit --------------------------------------------------------------------------------------------------------
BUNDLE = 'The full history is in the git bundle sent with this email.'   # the note's sentence; the kit puts the link in

def email(note, bundle=None):
    """The note as the email body: no To or Subject lines, links absolute on `submission`, the image attached, and the
    bundle's link in the sentence that promises it (the bundle is too large to attach)."""
    if bundle:
        note = note.replace(BUNDLE, f'The full history is in a git bundle: {bundle}')
    lines = note.rstrip().splitlines()
    head = dict(m.groups() for l in lines if (m := re.match(r'\*\*(To|Subject):\*\* (.*)', l)))
    body = '\n'.join(l for l in lines if not re.match(r'\*\*(To|Subject):\*\*', l)).strip()
    body = re.sub(r'(?m)^!\[([^\]]*)\]\([^)]*\)$', r'(Diagram attached, architecture.png: \1)', body)
    body = re.sub(r'\]\((?![a-z]+:)([^)]+)\)', lambda m: f']({REPO}/blob/submission/' + os.path.normpath(os.path.join('docs', m.group(1))) + ')', body)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', body)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text); text = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'\1', text).replace('`', '')
    def inline(s):
        s = html.escape(s, quote=False)
        s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
        s = re.sub(r'(?<!href=")(https?://[^\s<,)]+[^\s<,.)])', r'<a href="\1">\1</a>', s)
        s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s); s = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<i>\1</i>', s)
        return re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    parts = []
    for block in body.split('\n\n'):
        rows = block.splitlines()
        if all(r.startswith('- ') for r in rows):
            parts.append('<ul>' + ''.join(f'<li>{inline(r[2:])}</li>' for r in rows) + '</ul>')
        else:
            parts.append('<p>' + '<br>'.join(inline(r) for r in rows) + '</p>')
    page = ('<!doctype html><meta charset="utf-8"><title>' + html.escape(head.get('Subject', '')) + '</title>\n'
            '<div style="font: 15px/1.5 Georgia, serif; max-width: 640px">\n' + '\n'.join(parts) + '\n</div>\n')
    return head, text + '\n', page, re.findall(r'https?://[^\s)<>"]+[^\s)<>".,]', text)

def history(mod, out):
    """Every session from the three folders, in time order, through the exporter's own render and redaction."""
    rows = []
    for part, folder in SESSIONS:
        for p in sorted((HOME / '.claude-enam/projects' / folder).glob('*.jsonl')):
            start, first, body = mod.render(str(p))
            if body:
                rows.append((start, part, first, body))
    rows.sort(key=lambda r: r[0])
    (out / 'sessions').mkdir(parents=True)
    index = []
    for n, (start, part, first, body) in enumerate(rows, 1):
        name = f'{n:03d}_{start[:10]}_{part.split()[0].lower()}.md'
        (out / 'sessions' / name).write_text(mod.red(f'# Session {n} ({part}): {start[:16].replace("T", " ")} UTC\n\n' + '\n\n'.join(body) + '\n'))
        index.append(f'| {n} | {start[:16].replace("T", " ")} | {part} | [{name}](sessions/{name}) | {mod.red(re.sub(r"[|\s]+", " ", first or "")[:90])} |')
    (out / 'SESSIONS.md').write_text(
        '# Build sessions, in order\n\nEvery Claude Code session used to build FINN, from three folders: the October app, motion, '
        'and the network. Exported from the session logs; tool outputs are cut short to keep it readable; keys, one '
        'confidential name and account details are redacted, and output that read a private chat is left out. Sessions '
        '001 to 038 are the first submission (October); the rest are this one. Start with BUILD_HISTORY.md.\n\n| # | Started (UTC) | Part | File | Opening prompt |\n|---|---|---|---|---|\n'
        + '\n'.join(index) + '\n')
    orch = out / 'orchestration'; orch.mkdir()
    fc, top = HOME / 'ENAM-FINN/for_claude', HOME / 'ENAM-FINN'
    # The written product/design specs only: the "how I broke the problem down" material ENAM asks for.
    # Not the run scripts, the account/limit plan, or the 28 Oct desktop transcript: that is build machinery and
    # personal detail, not what they asked for (NEEDS step 5).
    files = [fc / x for x in ('KICKOFF.txt', '0_BUILD_GUIDELINES.md', 'DESIGN_SPEC.md', 'UX_SPEC.md', 'STAGE4_SPEC.md', 'slop_scan.py')]
    files += [top / 'MOTION_SPEC.md'] + sorted(top.glob('NETWORK_SPEC*.md'))
    for f in files:
        if f.exists():
            (orch / f.name).write_text(mod.red(f.read_text(errors='ignore')))
    (out / 'BUILD_HISTORY.md').write_text(mod.red((R / 'docs/BUILD_HISTORY.md').read_text()))
    oct_guide = top / 'FINN_AI_build_history/HOW_I_WORKED.md'                  # October's guide, which BUILD_HISTORY names
    if oct_guide.exists():
        (out / 'HOW_I_WORKED.md').write_text(mod.red(oct_guide.read_text()))
    return len(rows), {p: sum(1 for r in rows if r[1] == p) for p, _ in SESSIONS}

def kit(head, texts):
    mod = exporter()
    if mod is None:
        sys.exit(f'{EXPORTER} is missing: the build history cannot be exported or redacted')
    out = R / 'send'
    was = json.loads((out / 'kit.json').read_text()) if (out / 'kit.json').exists() else {}
    arg = sys.argv[sys.argv.index('--bundle-url') + 1] if '--bundle-url' in sys.argv[:-1] else None
    url = arg or was.get('bundle_url')                  # kept from the last run, so running the kit again keeps the link
    accept = '--accept-history' in sys.argv or was.get('accepted_history', False)
    kept = None                         # git bundle isn't byte-stable: keep one that holds this very commit, so an uploaded copy still matches
    if (out / 'finn-network.bundle').exists():
        heads = subprocess.run(['git', 'bundle', 'list-heads', str(out / 'finn-network.bundle')], cwd=R, capture_output=True, text=True).stdout.split()
        if heads == [head, 'refs/heads/network']:
            kept = pathlib.Path(tempfile.mkdtemp()) / 'finn-network.bundle'; shutil.move(str(out / 'finn-network.bundle'), kept)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    if kept:                             # back at once, so a run that stops early still leaves it
        shutil.move(str(kept), out / 'finn-network.bundle')
    note = texts['docs/COVERING_NOTE.md']
    if BUNDLE not in note:               # the note no longer sends the bundle: nothing else may promise it
        for f in ('docs/COVERING_NOTE.md', 'README.md', 'docs/BUILD_HISTORY.md', 'docs/BRIEF_TRACE.md'):
            check('bundle' not in texts.get(f, '').lower(), f'{f} promises no bundle, since the note sends none')
    if url and not re.fullmatch(r'https://\S+', url):
        check(False, 'the bundle link is an https URL', url)
    if BUNDLE in note and not url:
        warns.append('WARN: the email promises the bundle but has no link to it yet: upload send/finn-network.bundle, '
                     'then python3 evals/ship.py --kit --bundle-url <link> (live.py --presend fails until then)')
    head_lines, text, page, urls = email(note, url)
    (out / 'email.txt').write_text(text); (out / 'email.html').write_text(page)
    shutil.copy(R / 'docs/img/architecture.png', out / 'architecture.png')
    n, by = history(mod, out / 'build-history')
    shutil.make_archive(str(out / 'build-history'), 'zip', out, 'build-history')
    if kept:
        print('ok   the bundle already made from this commit is kept, so an uploaded copy still matches')
    else:
        git('bundle', 'create', str(out / 'finn-network.bundle'), 'network')
    check(subprocess.run(['git', 'bundle', 'verify', '-q', str(out / 'finn-network.bundle')], cwd=R, capture_output=True).returncode == 0,
          'the bundle verifies')
    exp = {str(f.relative_to(out)): f.read_text(errors='ignore') for f in (out / 'build-history').rglob('*') if f.is_file()}
    rx, own = design_rx(mod), own_numbers()
    if own is None:
        warns.append("WARN: the private transcript isn't there, so the export was not checked for the person's phone or enrolment number")
    found = {
        'key-shaped strings': sum(len(k.findall(t)) for t in exp.values() for k in KEYS),
        'GEMINI_API_KEY= with a value': sum(1 for t in exp.values() for m in KEY_VAR.finditer(t) if m.group(1) not in PLACEHOLDER and 'redacted' not in m.group(1)),
        'base-design name': sum(len(rx.findall(t)) for t in exp.values()) if rx else -1,
        'their phone or enrolment number': -1 if own is None else sum(len(re.findall(rf'(?<!\d){n}(?!\d)', t)) for t in exp.values() for n in own),
        'the interview prep, named': sum(len(re.findall(r'(?i)interview.?defen', t)) for t in exp.values()),
        'base-design trace, any form': sum(mod.leaks(t) for t in exp.values()) if hasattr(mod, 'leaks') else -1,
        "the git author's address": sum(t.lower().count(a.lower()) for t in exp.values() for a in {git('config', 'user.email')} if a),
    }
    check(found['key-shaped strings'] == 0 and found['GEMINI_API_KEY= with a value'] == 0, 'the history export holds no key')
    check(found['base-design name'] == 0 and found['base-design trace, any form'] == 0, 'the history export never names the base design')
    check(found['the interview prep, named'] == 0, 'the history export never names the interview prep')
    check(found['their phone or enrolment number'] <= 0, 'the history export holds no phone or enrolment number of theirs')
    gone = past('network')                 # the bundle carries every version of every file, not just the tip
    if gone and any(gone[:3]) and BUNDLE not in note and not gone[3]:
        warns.append(f"WARN: the bundle's history names the base design in {len(gone[0])} paths; the note no longer promises "
                     "the bundle, so don't send send/finn-network.bundle")
    elif gone and any(gone[:3]) and accept and not gone[3]:
        warns.append(f"WARN: the bundle's history names the base design in {len(gone[0])} paths ({', '.join(gone[0][:4])}), "
                     f"in versions from {len(gone[1])} commits; sent as you decided (--accept-history)")
    else:
        check(gone is not None and not any(gone[:3]), "the bundle's history never names the base design and holds no key",
              gone and f'{len(gone[0])} paths ({", ".join(gone[0][:4])}), in versions from {len(gone[1])} commits; {len(gone[2])} commit messages'
              '. Decide first (docs/NEEDS_FROM_USER.md, step 5); --accept-history sends it as is')
    pub = past('origin/main') if subprocess.run(['git', 'rev-parse', '-q', '--verify', 'origin/main'], cwd=R, capture_output=True).returncode == 0 else None
    if pub and any(pub[:3]):
        warns.append(f"WARN: main on GitHub (public now; as origin/main last fetched) carries it in its history too: {len(pub[0])} paths ({', '.join(pub[0][:4])}), in versions from {len(pub[1])} commits")
    att = ['architecture.png', 'build-history.zip', 'finn-network.bundle']
    size = {a: (out / a).stat().st_size for a in att}
    enc = sum(-(-s // 3) * 4 for s in size.values())          # mail sends attachments base64-encoded: a third larger
    fit = (f'fit in one email: {enc / 2**20:.1f} MB once encoded, of 25' if enc <= MAIL_LIMIT else
           f'are {enc / 2**20:.1f} MB once encoded for mail, over a 25 MB limit such as Gmail\'s: attach the diagram and the '
           f'history, and share finn-network.bundle as a link: --bundle-url puts it in the email')
    print(('ok   ' if enc <= MAIL_LIMIT else 'WARN ') + 'the attachments ' + fit)
    rep = [f'The send kit, made by evals/ship.py --kit from network {head[:7]}.', '',
           f'To:       {head_lines.get("To", "")}', f'Subject:  {head_lines.get("Subject", "")}',
           'Body:     email.html (paste into the mail, or send as HTML); email.txt is the same as plain text.', '',
           'Attach:'] + [f'  {a:22} {size[a] / 2**20:7.2f} MB' for a in att] + [
           f'  {"total":22} {sum(size.values()) / 2**20:7.2f} MB on disk; the attachments {fit}.', '',
           f'Build history: {n} sessions ({", ".join(f"{v} {k}" for k, v in by.items())}), BUILD_HISTORY.md at the top.',
           'Scans over the export (each should be 0, except the last, which is for you to decide):'] + [
           f'  {k:32} {v}' for k, v in found.items()] + ['',
           f'The body links to {REPO}/blob/submission/...; they answer 404 until you push `submission` (docs/NEEDS_FROM_USER.md).',
           'python3 web/test/e2e/live.py --presend fetches every URL in email.txt.', '',
           "The bundle's history, every version of every file and every commit message:" + (
               ' clean.' if gone and not any(gone[:3]) else f' names the base design or holds a key in {len(gone[0])} paths, '
               f'in versions written by {len(gone[1])} commits ({", ".join(gone[1])}); {len(gone[2])} commit messages. Do not send the bundle until you decide '
               '(docs/NEEDS_FROM_USER.md, step 5).' if gone else ' NOT checked (the exporter or its pattern is missing).')] + (
           [w[6:] for w in warns if 'GitHub' in w])
    sha = hashlib.sha256((out / 'finn-network.bundle').read_bytes()).hexdigest()
    rep += ['', 'Bundle link in the email: ' + (url or 'NONE YET (upload the bundle, then --kit --bundle-url <link>)'),
            f'The bundle this kit made: sha256 {sha}. live.py --presend downloads the link signed out and compares. The kit keeps',
            'this bundle while network is at this commit; after a new commit, upload the new one as a new version of the same file (Drive: Manage versions).',
            "The bundle's history sent as is: " + ('yes, you chose it (--accept-history)' if accept else 'not chosen')]
    m = re.search(r'(?ms)^## Handoff.*?(?=^## )', texts.get('docs/NEEDS_FROM_USER.md', ''))   # one source: NEEDS' top, as committed
    check(bool(m), 'the handoff heads docs/NEEDS_FROM_USER.md and the kit')
    if m:
        (out / 'HANDOFF.txt').write_text(m.group(0).strip() + '\n')
        rep = [m.group(0).strip(), '', '-' * 72, ''] + rep
    (out / 'REPORT.txt').write_text('\n'.join(rep) + '\n')
    # the gate (live.py --presend) reads this: the commit the kit was made from, what failed, and the link
    (out / 'kit.json').write_text(json.dumps({'head': head, 'fails': list(fails), 'bundle_url': url, 'accepted_history': accept,
                                              'bundle_sha256': sha}))
    print('\n'.join('     ' + l for l in rep))

if __name__ == '__main__':
    head, tree, texts = snapshot()
    if not fails and '--write' in sys.argv:
        write(head, tree)
    if not fails and '--kit' in sys.argv:
        kit(head, texts)
    for w in warns:
        print(w)
    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    sys.exit(1 if fails else 0)
