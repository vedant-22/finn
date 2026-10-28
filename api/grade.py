"""POST {src, calls} -> the assembled ledger: grades, questions, for and against."""
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler
from finn import llm, research

def run(body):
    src, calls = body["src"], body["calls"]
    llm.METER[:] = []
    good = [c for c in calls if not c.get("error")]
    calls = good[:research.N_CALLS] if len(good) >= 2 else calls[:research.N_CALLS]
    graded = research.grade(src, calls)
    return research.assemble(src, calls, graded)

class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
