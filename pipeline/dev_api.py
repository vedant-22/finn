"""Run the /api endpoints locally on :3001 (Vite proxies /api there). python3 pipeline/dev_api.py"""
import importlib.util, pathlib, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

API = pathlib.Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(API.parent))
handlers = {}
for name in ("sources", "call", "grade"):
    spec = importlib.util.spec_from_file_location(name, API / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    handlers[f"/api/{name}"] = mod.handler

class Router(BaseHTTPRequestHandler):
    def do_POST(self):
        h = handlers.get(self.path.split("?")[0])
        if not h:
            self.send_response(404); self.end_headers(); return
        self.run = h.run
        h.do_POST(self)

Router._send = next(iter(handlers.values()))._send

if __name__ == "__main__":
    print("api on http://localhost:3001")
    ThreadingHTTPServer(("", 3001), Router).serve_forever()
