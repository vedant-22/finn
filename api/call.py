"""POST {symbol, period} -> promises from one earnings call, each quote checked against its page.

The client names the call; the server looks up the document URLs itself, so this endpoint
can't be pointed at arbitrary URLs.
"""
import re
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler
from finn import research

def run(body):
    sym = re.sub(r"[^A-Z0-9&-]", "", str(body.get("symbol", "")).upper())[:20]
    src = research.sources(sym)
    match = [t for t in src["transcripts"] if t["period"] == body.get("period")]
    if not match:
        raise ValueError(f"no call for {body.get('period')}")
    return research.promises_for(match[0])

class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
