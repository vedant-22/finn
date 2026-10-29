# The home-screen icons (web/public/icon-192.png, icon-512.png): Folio's mark in white on ENAM blue, the small square
# standing on the baseline before 'finn' in the book serif. Drawn in the app's own fonts. Run: python3 web/scripts/icons.py [base url]
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger.vercel.app'
PUB = pathlib.Path(__file__).resolve().parents[1] / 'public'

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 512, 'height': 512})
        await pg.goto(BASE + '/#/look'); await pg.wait_for_timeout(1500)  # the app's fonts are loaded on this origin
        await pg.evaluate('''() => {
          document.body.innerHTML = `
          <div style="position:fixed;inset:0;background:#005DA3;display:flex;align-items:center;justify-content:center">
            <div style="display:flex;align-items:baseline;gap:16px;color:#fff;margin-top:-14px">
              <span style="width:64px;height:64px;border-radius:15px;background:#fff;flex:none"></span>
              <span style="font:600 140px/1 Newsreader,Georgia,serif;letter-spacing:-0.02em">finn</span>
            </div>
          </div>`
        }''')
        await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(400)
        await pg.screenshot(path=str(PUB / 'icon-512.png'))
        small = await b.new_page(viewport={'width': 192, 'height': 192})
        await small.set_content(f'<img src="data:image/png;base64,{__import__("base64").b64encode((PUB / "icon-512.png").read_bytes()).decode()}" style="width:192px;height:192px;display:block;margin:0">')
        await small.add_style_tag(content='body{margin:0}')
        await small.screenshot(path=str(PUB / 'icon-192.png'))
        await b.close()

asyncio.run(main())
