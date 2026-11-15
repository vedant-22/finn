# The 1200x630 link-preview card (web/public/og.png): the app's wordmark, the app's sentence in two parts,
# and Today on the right, as it opens on the 28 Oct replay. Run: python3 web/scripts/og.py [base url]
import asyncio, base64, sys, pathlib
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-network.vercel.app'
OUT = pathlib.Path(__file__).resolve().parents[1] / 'public' / 'og.png'
FONTS = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'fonts'

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        phone = await b.new_page(viewport={'width': 390, 'height': 600}, device_scale_factor=2, reduced_motion='reduce', bypass_csp=True)  # the app's CSP forbids inline styles
        await phone.goto(BASE + '/'); await phone.wait_for_timeout(2500)
        await phone.add_style_tag(content='nav.tabs, .tabs { display: none !important }')
        await phone.evaluate("document.activeElement && document.activeElement.blur()"); await phone.wait_for_timeout(600)
        shot = base64.b64encode(await phone.screenshot()).decode()
        card = await b.new_page(viewport={'width': 1200, 'height': 630}, bypass_csp=True)
        await card.goto(BASE + '/#/look'); await card.wait_for_timeout(1500)  # the app's own fonts are loaded on this origin
        await card.evaluate('''shot => {
          document.body.innerHTML = `
          <div style="position:fixed;inset:0;background:#fff;display:flex;font-family:Inter,sans-serif;color:#333">
            <div style="flex:1;padding:64px 0 0 80px;display:flex;flex-direction:column">
              <div style="font:600 34px/1 'Inter Variable',Inter,sans-serif;letter-spacing:0.08em;color:#005DA3">FINN</div>
              <div style="margin-top:80px;font:400 60px/108% 'Inter Variable',Inter,sans-serif;letter-spacing:-0.03em;max-width:640px">The few things that need you today, and then it ends.</div>
              <div style="margin-top:28px;font:400 25px/145% 'Inter Variable',Inter,sans-serif;letter-spacing:-0.01em;color:#6A6970;max-width:600px">Each held against what management promised, with the person you know who can explain it.</div>
              <div style="margin-top:auto;margin-bottom:56px;font-size:20px;color:#6A6970">finn-network.vercel.app · a replay of 28 Oct 2026</div>
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
