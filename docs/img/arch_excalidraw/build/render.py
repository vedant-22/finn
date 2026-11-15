"""Render the Excalidraw scene headlessly: python3 render.py N  ->  ../vN.png and ../../architecture.excalidraw"""
import json, sys, subprocess, pathlib, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
N = sys.argv[1]
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--bind", "127.0.0.1"], cwd=HERE,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(device_scale_factor=2, viewport={"width": 1200, "height": 1000})
        pg.on("pageerror", lambda e: print("pageerror:", e))
        pg.goto("http://127.0.0.1:8766/scene.html")
        pg.wait_for_function("window.ready===true", timeout=120000)
        r = pg.evaluate("window.build({})")
        for line in r["problems"]:
            print("PROBLEM", line)
        print("size", r["w"], r["h"])
        (HERE.parent.parent / "architecture.excalidraw").write_text(json.dumps(r["scene"], indent=2) + "\n")
        pg.evaluate("document.fonts.ready")
        pg.set_viewport_size({"width": int(float(r["w"])) + 1, "height": int(float(r["h"])) + 1})
        pg.locator("#out svg").screenshot(path=str(HERE.parent / f"v{N}.png"))
        b.close()
finally:
    srv.terminate()
