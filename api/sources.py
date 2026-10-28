"""POST {symbol} -> financial tables, snapshot and the list of transcripts. No model calls."""
import re
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler
from finn import research

def run(body):
    sym = re.sub(r"[^A-Z0-9&-]", "", str(body.get("symbol", "")).upper())[:20]
    if not sym:
        raise ValueError("symbol required")
    return research.sources(sym)

class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
