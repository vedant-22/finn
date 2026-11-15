# Frame strips of the key motions at 390x844 for the critics: the app opening, a card growing into its view, Back,
# a fold, and a company page. Animations are slowed tenfold (CDP) so each frame lands mid-motion.
# usage: python3 motion.py [base] [label]   writes shots/s11/{label}-motion-{load,open,close,fold,company}.png
import asyncio, sys, pathlib
from playwright.async_api import async_playwright
from PIL import Image
OUT = pathlib.Path(__file__).resolve().parents[3] / 'shots' / 's11'
BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger-next.vercel.app'
LABEL = sys.argv[2] if len(sys.argv) > 2 else 'next'
RATE = 0.1
TIMES = [0, 40, 100, 170, 260, 600]  # real ms after the action, before slowing

async def frames(pg, act, name):
    shots = []
    await act()
    t = 0
    for ms in TIMES:
        await pg.wait_for_timeout(int((ms - t) / RATE)); t = ms
        p = OUT / f'_f{len(shots)}.png'; await pg.screenshot(path=str(p)); shots.append(p)
    ims = [Image.open(p) for p in shots]; w, h = ims[0].size
    strip = Image.new('RGB', (w * len(ims) + 8 * (len(ims) - 1), h), 'white')
    for k, im in enumerate(ims): strip.paste(im, (k * (w + 8), 0))
    strip.save(OUT / f'{LABEL}-motion-{name}.png'); [p.unlink() for p in shots]; print(name, [f'{m} ms' for m in TIMES])

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844})
        cdp = await pg.context.new_cdp_session(pg)
        slow = lambda: cdp.send('Animation.setPlaybackRate', {'playbackRate': RATE})
        await cdp.send('Animation.enable')
        # Opening the app: the count, the sentence and the first card settling
        await pg.goto(BASE + '/#/', wait_until='domcontentloaded'); await pg.evaluate('localStorage.clear()')
        async def load():
            await pg.reload(wait_until='domcontentloaded'); await cdp.send('Animation.enable'); await slow()
            await pg.locator('.card').first.wait_for()
        await frames(pg, load, 'load')
        await cdp.send('Animation.setPlaybackRate', {'playbackRate': 1}); await pg.wait_for_timeout(1500)
        # A card grows into its full view, and Back shrinks it home
        await pg.locator('.card').first.evaluate('e => scrollTo(0, e.getBoundingClientRect().top + scrollY - 40)'); await pg.wait_for_timeout(800)
        await slow()
        await frames(pg, lambda: pg.locator('.card .read-more').first.click(), 'open')
        await frames(pg, lambda: pg.locator('.item-view').get_by_role('button', name='Back').click(), 'close')
        # A fold: its rows fade up in place
        await cdp.send('Animation.setPlaybackRate', {'playbackRate': 1})
        await pg.locator('.fold').first.evaluate('e => scrollTo(0, e.getBoundingClientRect().top + scrollY - 120)'); await pg.wait_for_timeout(1200)
        await slow()
        await frames(pg, lambda: pg.locator('.fold summary, .fold button').first.click(), 'fold')
        # A company page arriving from Book
        await cdp.send('Animation.setPlaybackRate', {'playbackRate': 1})
        await pg.goto(BASE + '/#/book', wait_until='domcontentloaded'); await pg.wait_for_timeout(2500)
        await slow()
        await frames(pg, lambda: pg.locator('.book-card').first.click(), 'company')
        await b.close()
asyncio.run(main())
