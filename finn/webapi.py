"""Shared bits for the serverless endpoints: JSON in, JSON out, errors as JSON."""
import json, traceback
from http.server import BaseHTTPRequestHandler

class JSONHandler(BaseHTTPRequestHandler):
    run = None  # each endpoint sets this to a function body -> dict

    def do_POST(self):
        try:
            n = int(self.headers.get("content-length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            self._send(200, self.run(body))
        except Exception as e:
            name = type(e).__name__
            code = 404 if name == "NotFound" else 502 if name in ("LLMError", "FetchError", "HTTPError") else 500
            traceback.print_exc()
            self._send(code, {"error": f"{name}: {str(e)[:200]}"})
    def do_OPTIONS(self):
        self._send(204, {})
    def _send(self, code, obj):
        data = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
