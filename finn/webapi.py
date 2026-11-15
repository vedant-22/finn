"""Shared bits for the serverless endpoints: JSON in, JSON out, errors as fixed codes.

What leaves the server is a code, {"error": "quota"}, never upstream text. Upstream detail goes to the
server log; any other failure is logged as its type and stack frames, never its message, because a
message can carry what the investor typed.
"""
import json, re, sys, time, traceback
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler
import requests
from . import netguard

netguard.install()   # every connection the endpoints open must go to a public address

KB = 1024
STATUS = {"no_key": 503, "quota": 503, "unavailable": 502, "bad_response": 502, "unreachable": 502,
          "not_pdf": 502, "too_large": 502, "not_found": 404, "bad_request": 400, "busy": 429, "server": 500}


class BadRequest(ValueError):
    pass


class NotFound(Exception):
    pass


class Unavailable(Exception):
    code = "unavailable"


class Limiter:
    """At most n requests per IP in any `per` seconds. Each serverless instance counts on its own,
    so this slows one client down; it does not stop a determined one. An address is the one personal
    fact the server holds, so it is held in memory only, and forgotten at the first request (from
    anyone) a minute or more after its own window closed (Your data says so)."""
    def __init__(self, n, per):
        self.n, self.per, self.hits, self.swept = n, per, defaultdict(deque), float("-inf")

    def allow(self, ip, now=None):
        now = time.monotonic() if now is None else now
        if now - self.swept >= 60 or len(self.hits) > 5000:
            for k in [k for k, q in self.hits.items() if not q or now - q[-1] > self.per]:
                del self.hits[k]
            self.swept = now
            if len(self.hits) > 5000:
                self.hits.clear()
        q = self.hits[ip]
        while q and now - q[0] > self.per:
            q.popleft()
        if len(q) >= self.n:
            return False
        q.append(now)
        return True


def symbol(v):
    """An NSE symbol as the endpoints accept it: capitals, digits, & and -, at most 20."""
    return re.sub(r"[^A-Z0-9&-]", "", str(v or "").upper())[:20]


def code_for(e):
    """The fixed code a failure is reported as."""
    name = type(e).__name__
    if name in ("LLMError", "FetchError", "Unavailable"):
        return e.code
    if name == "NotFound":
        return "not_found"
    if isinstance(e, BadRequest):
        return "bad_request"
    if isinstance(e, requests.RequestException):
        return "unavailable"
    return "server"


def log_failure(e):
    if type(e).__name__ in ("LLMError", "FetchError"):
        print(f"{type(e).__name__} {e}", file=sys.stderr)        # a code and upstream detail (a model, a filing URL)
    else:
        print(type(e).__name__ + "\n" + "".join(traceback.format_tb(e.__traceback__)), file=sys.stderr)


class JSONHandler(BaseHTTPRequestHandler):
    run = None          # each endpoint sets this to a function body -> dict
    max_body = 2 * KB   # bytes; larger bodies are refused unread
    limit = None        # a Limiter, on the endpoints that spend model quota

    def do_POST(self):
        try:
            n = int(self.headers.get("content-length") or 0)
        except ValueError:
            n = -1
        if not 0 <= n <= self.max_body:
            return self._send(413 if n > 0 else 400, {"error": "bad_request"})
        if self.limit and not self.limit.allow(self._ip()):
            return self._send(429, {"error": "busy"})
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self._send(400, {"error": "bad_request"})
        try:
            out = self.run(body)
        except Exception as e:
            code = code_for(e)
            log_failure(e)
            return self._send(STATUS.get(code, 500), {"error": code})
        self._send(200, out)

    def do_OPTIONS(self):
        self._send(204, {})

    def _ip(self):
        # Vercel sets both from the connection and overwrites what the client sent.
        h = self.headers
        return h.get("x-real-ip") or (h.get("x-forwarded-for") or "").split(",")[0].strip() or self.client_address[0]

    def _send(self, code, obj):
        data = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
