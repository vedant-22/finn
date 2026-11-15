"""Run the /api endpoints locally on :3001 (Vite proxies /api there). python3 pipeline/dev_api.py"""
import importlib.util, os, pathlib, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

API = pathlib.Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(API.parent))
handlers = {}
for name in ("sources", "call", "grade", "network"):
    spec = importlib.util.spec_from_file_location(name, API / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    handlers[f"/api/{name}"] = mod.handler

class Router(BaseHTTPRequestHandler):
    def do_POST(self):
        h = handlers.get(self.path.split("?")[0])
        if not h:
            self.send_response(404); self.end_headers(); return
        self.run, self.max_body, self.limit = h.run, h.max_body, h.limit
        h.do_POST(self)

Router._send = next(iter(handlers.values()))._send
Router._ip = next(iter(handlers.values()))._ip

if __name__ == "__main__":
    port = int(os.environ.get("FINN_API_PORT", 3001))   # the preview reads the same variable
    print(f"api on http://localhost:{port}")
    ThreadingHTTPServer(("", port), Router).serve_forever()
