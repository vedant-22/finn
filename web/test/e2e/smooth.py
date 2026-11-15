# Is scrolling still smooth on a phone? At 390x844 with the CPU slowed 4x (a mid phone), scroll Today, Book and a
# company page down and back with the wheel, and time every frame. Prints, per page, the frames over 20ms and the
# longest one. Run it on the motion copy and on the submitted look to compare.
# usage: python3 smooth.py [base]
import asyncio, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
WATCH = '''() => { window.__ft = []; let t0 = performance.now();
  const f = t => { window.__ft.push(t - t0); t0 = t; if (window.__ft.length < 2000) requestAnimationFrame(f) }; requestAnimationFrame(f) }'''

async def scroll(pg):
    await pg.mouse.move(195, 420)
    for dy in [120] * 24 + [-120] * 12:
        await pg.mouse.wheel(0, dy); await pg.wait_for_timeout(16)
    await pg.wait_for_timeout(600)

async def page(pg, name):
    await pg.evaluate(WATCH); await scroll(pg)
    ft = (await pg.evaluate('window.__ft'))[1:]
    long = [t for t in ft if t > 20]
    print(f'{name:8} frames {len(ft):4}  over 20ms {len(long):3} ({100 * len(long) / max(len(ft), 1):4.1f}%)  longest {max(ft):5.1f}ms')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844})
        cdp = await pg.context.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        await pg.goto(BASE + '/#/'); await pg.wait_for_selector('.hero-fig'); await pg.wait_for_timeout(1500)
        await page(pg, 'today')
        await pg.goto(BASE + '/#/book'); await pg.wait_for_selector('.book-card'); await pg.wait_for_timeout(1500)
        await page(pg, 'book')
        await pg.locator('.book-card').first.click(); await pg.wait_for_selector('.co-top'); await pg.wait_for_timeout(1500)
        await page(pg, 'company')
        await b.close()
asyncio.run(main())
