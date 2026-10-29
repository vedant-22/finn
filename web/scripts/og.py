# The 1200x630 link-preview card (web/public/og.png): wordmark, one line, one serif sentence,
# and the top of a live company page on the right. Run: python3 web/scripts/og.py [base url]
import asyncio, base64, sys, pathlib
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger.vercel.app'
OUT = pathlib.Path(__file__).resolve().parents[1] / 'public' / 'og.png'
FONTS = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'fonts'

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        phone = await b.new_page(viewport={'width': 390, 'height': 600}, device_scale_factor=2, reduced_motion='reduce')
        await phone.goto(BASE + '/#/c/LT'); await phone.wait_for_timeout(2500)
        await phone.add_style_tag(content='nav.tabs, .tabs { display: none !important }')
        shot = base64.b64encode(await phone.screenshot()).decode()
        card = await b.new_page(viewport={'width': 1200, 'height': 630})
        await card.goto(BASE + '/#/look'); await card.wait_for_timeout(1500)  # the app's own fonts are loaded on this origin
        await card.evaluate('''shot => {
          document.body.innerHTML = `
          <div style="position:fixed;inset:0;background:#fff;display:flex;font-family:Inter,sans-serif;color:#333">
            <div style="flex:1;padding:64px 0 0 80px;display:flex;flex-direction:column">
              <div style="font-weight:600;letter-spacing:.08em;color:#005DA3;font-size:26px">FINN</div>
              <div style="margin-top:112px;font-size:64px;line-height:112%;letter-spacing:-2.2px;font-weight:450;max-width:600px">Keeps management to its word.</div>
              <div style="margin-top:28px;font:400 26px/140% 'PT Serif',serif;color:#6A6970;max-width:560px">Every promise from the earnings calls, checked against what the company later reported.</div>
              <div style="margin-top:auto;margin-bottom:56px;font-size:20px;color:#6A6970">finn-ledger.vercel.app</div>
            </div>
            <div style="width:380px;margin:56px 80px 0 0;background:#fff;border:1px solid #D9D9D9;border-bottom:0;overflow:hidden">
              <img src="data:image/png;base64,${shot}" style="width:380px;display:block">
            </div>
          </div>`
        }''', shot)
        await card.wait_for_timeout(500)
        await card.screenshot(path=str(OUT))
        await b.close()

asyncio.run(main())
