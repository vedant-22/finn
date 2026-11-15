"""POST {symbol, period} -> promises from one earnings call, each quote checked against its page.

The client names the call; the server looks up the document URLs itself, so this endpoint
can't be pointed at arbitrary URLs. The model key is checked before anything is fetched.
"""
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler, BadRequest, NotFound, Limiter, symbol
from finn import llm, research

def run(body):
    llm.require_key()
    sym = symbol(body.get("symbol"))
    if not sym:
        raise BadRequest("symbol required")
    src = research.sources(sym)
    match = [t for t in src["transcripts"] if t["period"] == body.get("period")]
    if not match:
        raise NotFound("no such call")
    llm.METER[:] = []
    out = research.promises_for(match[0])
    out["usage"] = research._usage()
    return out

class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
    limit = Limiter(30, 600)   # one company is six calls; this allows five companies in ten minutes
