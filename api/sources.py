"""POST {symbol} -> financial tables, snapshot and the list of transcripts. No model calls.

Without a model key, answers {live: false} at once and fetches nothing: reading a new company would
stop at the first call, so the app says so before it starts.

POST {op: "status"} -> {live}: whether reading a new company can work on this deployment, and nothing
else. No fetch, no model, no symbol. The phone asks once a session so it can say reading is off before
the tap, and so the Your data sheet can say what doesn't work here."""
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler, BadRequest, symbol
from finn import llm, research

def run(body):
    if body.get("op") == "status":
        return {"live": llm.has_key()}
    sym = symbol(body.get("symbol"))
    if not sym:
        raise BadRequest("symbol required")
    if not llm.has_key():
        return {"symbol": sym, "live": False}
    return dict(research.sources(sym), live=True)

class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
