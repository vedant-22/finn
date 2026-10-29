# The 1200x630 link-preview card (web/public/og.png): the mark, a serif line, one plain sentence,
# and a live company page on the right, opened on a promise's before-and-after. Run: python3 web/scripts/og.py [base url]
import asyncio, base64, sys, pathlib
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger.vercel.app'
OUT = pathlib.Path(__file__).resolve().parents[1] / 'public' / 'og.png'
FONTS = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'fonts'

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        phone = await b.new_page(viewport={'width': 390, 'height': 600}, device_scale_factor=2, reduced_motion='reduce')
        await phone.goto(BASE + '/#/c/LT/0'); await phone.wait_for_timeout(2500)
        await phone.add_style_tag(content='nav.tabs, .tabs, .co-bar { display: none !important }')
        await phone.evaluate("document.activeElement && document.activeElement.blur()")
        await phone.evaluate("window.scrollBy(0, document.querySelector('[data-pid=\"0\"]').getBoundingClientRect().top - 8)"); await phone.wait_for_timeout(600)
        shot = base64.b64encode(await phone.screenshot()).decode()
        card = await b.new_page(viewport={'width': 1200, 'height': 630})
        await card.goto(BASE + '/#/look'); await card.wait_for_timeout(1500)  # the app's own fonts are loaded on this origin
        await card.evaluate('''shot => {
          document.body.innerHTML = `
          <div style="position:fixed;inset:0;background:#fff;display:flex;font-family:Inter,sans-serif;color:#333">
            <div style="flex:1;padding:64px 0 0 80px;display:flex;flex-direction:column">
              <div style="display:flex;align-items:baseline;gap:9px"><span style="width:18px;height:18px;border-radius:4.5px;background:#005DA3"></span><span style="font:600 38px/1 Newsreader,serif;letter-spacing:-0.02em">finn</span></div>
              <div style="margin-top:96px;font:400 70px/104% Newsreader,serif;letter-spacing:-0.025em;max-width:620px">Keeps management <em style="font-style:italic">to its word</em>.</div>
              <div style="margin-top:28px;font:400 25px/145% 'Inter Variable',Inter,sans-serif;letter-spacing:-0.01em;color:#6A6970;max-width:560px">Every promise from the earnings calls, checked against what the company later reported.</div>
              <div style="margin-top:auto;margin-bottom:56px;font-size:20px;color:#6A6970">finn-ledger.vercel.app</div>
            </div>
            <div style="width:380px;margin:56px 80px 0 0;background:#fff;border:1px solid #D9D9D9;border-bottom:0;border-radius:28px 28px 0 0;overflow:hidden">
              <img src="data:image/png;base64,${shot}" style="width:380px;display:block">
            </div>
          </div>`
        }''', shot)
        await card.wait_for_timeout(500)
        await card.screenshot(path=str(OUT))
        await b.close()

asyncio.run(main())
