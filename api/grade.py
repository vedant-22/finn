"""POST {src, calls} -> the assembled ledger: grades, questions, for and against.

The server trusts only what it fetched itself. It reads the company's sources again, keeps a call from the
phone only if the server's own list of transcripts holds its URL, and takes the call's period from that list.
Promise text from the phone is shape-checked only: a forged list misleads only its sender, and evidence quotes
are still checked against the page the server fetches. The model key is checked before anything is fetched.
"""
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler, BadRequest, Limiter, Unavailable, KB, symbol
from finn import llm, research

MAX_CALLS, MAX_PROMISES, MAX_FIELD = 6, 40, 600


def _field(v):
    """A promise field as grading may use it: short text, a whole number or a yes/no."""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, int):
        return max(-1, min(v, 10_000))
    return str(v)[:MAX_FIELD]


def _call(c, listed):
    """The phone's call, kept only if the server listed its URL, with the server's period."""
    if not isinstance(c, dict) or not isinstance(c.get("url"), str) or c["url"] not in listed:
        return None
    t = listed[c["url"]]
    ps = c.get("promises") if isinstance(c.get("promises"), list) else []
    promises = [{**{k: _field(v) for k, v in p.items() if isinstance(k, str) and len(k) <= 40},
                 "period": t["period"], "url": c["url"]} for p in ps[:MAX_PROMISES] if isinstance(p, dict)]
    out = {"period": t["period"], "url": c["url"], "pages": _field(c.get("pages")), "promises": promises,
           "dropped_unverified": _field(c.get("dropped_unverified", 0)), "soft_count": _field(c.get("soft_count", 0))}
    if c.get("error"):
        out["error"] = str(c["error"])[:40]
    return out


def server_sources(sym):
    src = research.sources(sym, every_call=True)
    if not src.get("nse_ok"):
        src = research.sources(sym, every_call=True)   # NSE fails now and then; one more try before grading without it
    return src


def run(body):
    llm.require_key()
    sent, calls = body.get("src"), body.get("calls")
    if not isinstance(sent, dict) or not isinstance(calls, list) or len(calls) > MAX_CALLS:
        raise BadRequest("src and at most 6 calls")
    sym = symbol(sent.get("symbol"))
    if not sym:
        raise BadRequest("symbol required")
    src = server_sources(sym)
    listed = {u: t for t in src["transcripts"] for u in t.get("urls", [t["url"]])}
    if not listed:
        raise Unavailable("no transcripts listed")
    calls = [k for c in calls if (k := _call(c, listed))]
    llm.METER[:] = []
    good = [c for c in calls if not c.get("error")]
    calls = good[:research.N_CALLS] if len(good) >= 2 else calls[:research.N_CALLS]
    graded = research.grade(src, calls)
    return research.assemble(src, calls, graded)


class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
    max_body = 68 * KB         # twice the largest six-call body measured end to end: 10 promises a call, the most any real call has (34 KB)
    limit = Limiter(6, 600)    # one grade per company read
