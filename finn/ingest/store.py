"""The ledger: filings as events, the runs of each step over them, and the facts they settle.

SQLite here, one file under data/cache/. For real it is Cloud SQL and also the queue (docs/adr/0002-ledger-is-the-queue.md):
a claim is a short transaction that sets a lease, no lock is held while a step works, and a completion
writes only if its lease token still holds. Leases matter once two workers can run at once (a Cloud Run job started
while the last one still runs); here they are tested with two drains in two threads.

A claim takes one batch (20 for read, 4 otherwise), so its worst case, a PDF fetch and four model tries, is about
10 minutes; the lease is 30. The attempt is counted when a run is claimed, so a worker that crashes still uses one,
and a run claimed MAX_ATTEMPTS times ends dead. A parked or not-yet outcome gives its attempt back.
Every write to a run takes the next number in `seq`, so planning reads only events whose inputs changed.
"""
import hashlib, json, sqlite3, uuid
from .. import config

PATH = config.CACHE_DIR / "ledger.sqlite"
# A revision is a change to one of these. Anything else in NSE's JSON (sort keys, file sizes) is cosmetic.
FIXED = ("symbol", "desc", "attchmntText", "attchmntFile", "an_dt", "sm_isin")
SCHEMA = """
CREATE TABLE IF NOT EXISTS events(kind TEXT, id TEXT, rev INT, hash TEXT, at TEXT, symbol TEXT, isin TEXT, payload TEXT,
    PRIMARY KEY(kind, id, rev));
CREATE TABLE IF NOT EXISTS runs(kind TEXT, id TEXT, rev INT, step TEXT, fp TEXT, status TEXT, attempts INT DEFAULT 0,
    lease TEXT, lease_until REAL, not_before REAL DEFAULT 0, model TEXT, output TEXT, error TEXT, seq INT DEFAULT 0,
    PRIMARY KEY(kind, id, rev, step));
CREATE INDEX IF NOT EXISTS runs_queue ON runs(step, status, not_before);
CREATE INDEX IF NOT EXISTS runs_seq ON runs(seq);
CREATE TABLE IF NOT EXISTS facts(key TEXT PRIMARY KEY, value TEXT, fp TEXT, event TEXT);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""

def connect(path=None):
    db = sqlite3.connect(str(path or PATH), isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=10000")
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone() and \
            "seq" not in {r[1] for r in db.execute("PRAGMA table_info(runs)")}:
        db.execute("ALTER TABLE runs ADD COLUMN seq INT DEFAULT 0")   # a ledger written before seq existed
    db.executescript(SCHEMA)
    return db

NEXT = "(SELECT COALESCE(MAX(seq), 0) + 1 FROM runs)"
MAX_ATTEMPTS, LEASE = 5, 1800

def meta(db, k, v=None):
    if v is not None:
        db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
    row = db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return row["v"] if row else None

def digest(x):
    return hashlib.sha256(json.dumps([x.get(k) for k in FIXED]).encode()).hexdigest()[:16]

def put(db, x, kind="filing"):
    """Store a filing once. Returns its new revision, or 0 if nothing changed."""
    h, key = digest(x), str(x["seq_id"])
    db.execute("BEGIN IMMEDIATE")   # the read and the write as one: two polls at once can't both write the same revision
    try:
        last = db.execute("SELECT rev, hash FROM events WHERE kind=? AND id=? ORDER BY rev DESC LIMIT 1", (kind, key)).fetchone()
        rev = 0 if last and last["hash"] == h else (last["rev"] + 1 if last else 1)
        if rev:
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)",
                       (kind, key, rev, h, x.get("an_dt"), x.get("symbol"), x.get("sm_isin"), json.dumps(x)))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return rev

def latest(db):
    """The newest revision of every event."""
    return db.execute("SELECT * FROM events e WHERE rev = (SELECT MAX(rev) FROM events WHERE kind=e.kind AND id=e.id)").fetchall()

def changed(db, step, inputs):
    """The newest revision of every event this step hasn't planned, or whose inputs were written after it was."""
    q = ",".join("?" * len(inputs)) or "''"
    return db.execute(f"""SELECT * FROM events e WHERE rev = (SELECT MAX(rev) FROM events WHERE kind=e.kind AND id=e.id)
        AND NOT EXISTS (SELECT 1 FROM runs s WHERE s.kind=e.kind AND s.id=e.id AND s.rev=e.rev AND s.step=?
            AND NOT EXISTS (SELECT 1 FROM runs i WHERE i.kind=e.kind AND i.id=e.id AND i.rev=e.rev AND i.step IN ({q}) AND i.seq > s.seq))""",
        (step, *inputs)).fetchall()

def runs_of(db, ev):
    rows = db.execute("SELECT * FROM runs WHERE kind=? AND id=? AND rev=?", (ev["kind"], ev["id"], ev["rev"])).fetchall()
    return {r["step"]: r for r in rows}

def set_run(db, ev, step, fp, status, output=None):
    """Plan a run. A run already planned with this fingerprint is left alone, so a second planner racing the first
    can't reset a run the first one's worker has leased."""
    db.execute("INSERT INTO runs(kind, id, rev, step, fp, status, attempts, lease, lease_until, not_before, model, output, error, seq)"
               f" VALUES (?,?,?,?,?,?,0,NULL,NULL,0,NULL,?,NULL,{NEXT})"
               " ON CONFLICT(kind, id, rev, step) DO UPDATE SET fp=excluded.fp, status=excluded.status, attempts=0, lease=NULL,"
               " lease_until=NULL, not_before=0, model=NULL, output=excluded.output, error=NULL, seq=excluded.seq WHERE runs.fp != excluded.fp",
               (ev["kind"], ev["id"], ev["rev"], step, fp, status, json.dumps(output)))

def touch(db, ev, step):
    """Mark a run planned now without changing it: its inputs were rewritten with the same result."""
    db.execute(f"UPDATE runs SET seq={NEXT} WHERE kind=? AND id=? AND rev=? AND step=?", (ev["kind"], ev["id"], ev["rev"], step))

NEWEST = "(SELECT MAX(rev) FROM events e WHERE e.kind=runs.kind AND e.id=runs.id)"

def claim(db, step, n, now, ttl=LEASE):
    """Lease up to n pending runs of a step and count the attempt. Short transaction; the work happens outside it.
    A run already claimed MAX_ATTEMPTS times (its workers kept dying) ends dead instead. A run of a revision that a
    newer one has replaced (a filing revised while its read was parked) is marked superseded, never worked or paid for."""
    tok = uuid.uuid4().hex
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute(f"UPDATE runs SET status='superseded', lease=NULL, lease_until=NULL WHERE step=? AND status='pending' AND rev < {NEWEST}", (step,))
        sel = ("SELECT * FROM runs WHERE step=? AND status='pending' AND not_before<=? AND (lease_until IS NULL OR lease_until<?)"
               " ORDER BY id LIMIT ?")
        rows = db.execute(sel, (step, now, now, n)).fetchall()
        spent = [r for r in rows if r["attempts"] >= MAX_ATTEMPTS]
        db.executemany(f"UPDATE runs SET status='dead', error='crashed', lease=NULL, lease_until=NULL, seq={NEXT}"
                       " WHERE kind=? AND id=? AND rev=? AND step=?", [(r["kind"], r["id"], r["rev"], step) for r in spent])
        rows = [r for r in rows if r["attempts"] < MAX_ATTEMPTS]
        db.executemany("UPDATE runs SET lease=?, lease_until=?, attempts=attempts+1 WHERE kind=? AND id=? AND rev=? AND step=?",
                       [(tok, now + ttl, r["kind"], r["id"], r["rev"], step) for r in rows])
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK"); raise
    return tok, rows

def complete(db, r, tok, status, output=None, error=None, model=None, refund=False, not_before=0):
    """Fenced by the lease token: a worker whose lease expired and was reclaimed writes nothing."""
    cur = db.execute("UPDATE runs SET status=?, output=?, error=?, model=?, attempts=attempts-?, not_before=?, lease=NULL, lease_until=NULL,"
                     f" seq={NEXT} WHERE kind=? AND id=? AND rev=? AND step=? AND lease=?",
                     (status, json.dumps(output), error, model, int(refund), not_before, r["kind"], r["id"], r["rev"], r["step"], tok))
    return cur.rowcount == 1

def release(db, r, tok, not_before):
    """Give a claimed run back unworked, its attempt too. Its place in `seq` stays, so planning still sees which of its
    inputs were written after it."""
    db.execute("UPDATE runs SET lease=NULL, lease_until=NULL, attempts=attempts-1, not_before=?"
               " WHERE kind=? AND id=? AND rev=? AND step=? AND lease=?", (not_before, r["kind"], r["id"], r["rev"], r["step"], tok))

def fact(db, key, value=None, fp="", event=""):
    """Read a fact, or write it once (first writer wins, so results in any order give one fact). Its key carries the
    version of the code that made it, so a new version makes a new fact instead of reading the old one."""
    if value is not None:
        db.execute("INSERT OR IGNORE INTO facts VALUES (?,?,?,?)", (key, json.dumps(value), fp, event))
    row = db.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else None

def status(db):
    return {(r["step"], r["status"]): r["n"] for r in db.execute("SELECT step, status, COUNT(*) n FROM runs GROUP BY step, status")}
