# Section 9 colour trial: the same five moments in each look at 390x844. usage: python3 looks.py [base] [looks, e.g. 0,a,b,c] [width]
# writes shots/looks/{look}-{1..5}.png (shots/ is git-ignored)
import asyncio, sys, pathlib
from playwright.async_api import async_playwright
OUT = pathlib.Path(__file__).resolve().parents[3] / 'shots' / 'looks'; OUT.mkdir(parents=True, exist_ok=True)
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
LOOKS = sys.argv[2].split(',') if len(sys.argv) > 2 else ['0', 'a', 'b', 'c']
W = int(sys.argv[3]) if len(sys.argv) > 3 else 390

async def fresh(pg, url):
    await pg.goto(url); await pg.evaluate('localStorage.clear()'); await pg.reload(); await pg.wait_for_timeout(1800)

async def run(pg, look, shot):
    q = '' if look == '0' else f'?look={look}'
    await fresh(pg, f'{BASE}/{q}#/'); await shot(1)
    await pg.get_by_role('button', name='Read the brief').click(); await pg.wait_for_timeout(900)
    for _ in range(6):
        if 'Larsen' in await pg.locator('.reader h1').first.inner_text(): break
        await pg.get_by_role('button', name='Keep for later').click(); await pg.wait_for_timeout(600)
    await shot(2)
    await pg.locator('.r-sec[aria-label="Against their word"]').evaluate('e => e.scrollIntoView({block: "start"})'); await pg.wait_for_timeout(600); await shot(3)
    await fresh(pg, f'{BASE}/{q}#/book'); await shot(4)
    await fresh(pg, f'{BASE}/{q}#/c/LT'); await shot(5)
    await fresh(pg, f'{BASE}/{q}#/'); await pg.get_by_role('button', name='Read the brief').click(); await pg.wait_for_timeout(800)
    for _ in range(8):
        if await pg.locator('.done-t').count(): break
        last = pg.get_by_role('button', name='Mark all read')
        await (last if await last.count() else pg.get_by_role('button', name='Done', exact=True)).click(); await pg.wait_for_timeout(700)
    await pg.wait_for_timeout(700); await shot(6)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for look in LOOKS:
            pg = await b.new_page(viewport={'width': W, 'height': 844}, device_scale_factor=1)
            async def shot(n, look=look, pg=pg): await pg.screenshot(path=str(OUT / f'{look}-{W}-{n}.png'))
            try: await run(pg, look, shot); print(look, 'ok')
            except Exception as e: print(look, 'stopped:', str(e).splitlines()[0])
            await pg.close()
        await b.close()
asyncio.run(main())
