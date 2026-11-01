# Matching 390x844 shots of the main moments from the stage 4 build and the two backups it has to beat.
# usage: python3 compare.py [next-base] [versions, e.g. next or next,v4,v5]   writes shots/s7-{ver}-{1..6}.png (shots/ is git-ignored)
import asyncio, sys, pathlib
from playwright.async_api import async_playwright
OUT = pathlib.Path(__file__).resolve().parents[3] / 'shots'
NEXT = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger-next.vercel.app'
BACKUPS = {'v4': 'https://finn-ledger-v4.vercel.app', 'v5': 'https://finn-ledger-v5.vercel.app', 'live': 'https://finn-ledger.vercel.app'}
VERSIONS = sys.argv[2].split(',') if len(sys.argv) > 2 else ['next', 'v4', 'v5']
MOMENTS = ['today', 'alert', 'results', 'people', 'company', 'look up', 'book', 'end']

async def top(pg, sel):
    # Put the element at the top of the screen, under any sticky header
    await pg.locator(sel).first.evaluate('''e => { const bar = document.querySelector('.co-bar, .fo-bar, header'); const h = bar && getComputedStyle(bar).position.match(/sticky|fixed/) ? bar.offsetHeight : 0
      scrollTo(0, e.getBoundingClientRect().top + scrollY - h - 16) }'''); await pg.wait_for_timeout(900)

async def reader_to(pg, name, kind):
    # Step through the reader (Keep, so nothing is lost) until the item for this company and kind is up
    for _ in range(8):
        if name in await pg.locator('.reader h1').first.inner_text() and (await pg.locator('.reader .kicker').first.inner_text()).startswith(kind): return
        await pg.get_by_role('button', name='Keep for later').click(); await pg.wait_for_timeout(700)

async def fresh(pg, url):
    # A returning investor, as one opens it every morning: last here before the 28 Oct session, so what came after is New
    # (the first load stamps its own visit once its data is in, so wait for that before setting the earlier one)
    await pg.goto(url); await pg.wait_for_timeout(2500)
    await pg.evaluate('localStorage.clear(); localStorage.setItem("finn.seen", "2026-10-28T09:00:00+05:30")'); await pg.reload(); await pg.wait_for_timeout(2500)

async def next_build(pg, shot, base=None):
    base = base or NEXT
    await fresh(pg, base + '/#/'); await shot(1)
    # 2: an alert, its card in the week; 3 and 4: a card opened into its full view (L&T's results, Syngene's CFO)
    await pg.get_by_role('radio', name='Week', exact=True).click(); await pg.wait_for_timeout(900)
    await top(pg, '.card'); await shot(2)
    await pg.get_by_role('radio', name='24h', exact=True).click(); await pg.wait_for_timeout(700)
    await pg.locator('.card', has_text='Larsen').locator('.read-more').click(); await pg.wait_for_timeout(1200)
    # the company's word arrives with its file; shoot once it's in, as an investor would see it a moment after opening
    await pg.locator('.item-view section[aria-label="Against their word"]').wait_for(timeout=8000)
    await pg.locator('.item-view .figs').evaluate('e => e.scrollIntoView({block: "center"})'); await pg.wait_for_timeout(600); await shot(3)
    await pg.locator('.item-view').get_by_role('button', name='Back').click(); await pg.wait_for_timeout(900)
    await pg.locator('.card', has_text='Syngene').locator('.read-more').click(); await pg.wait_for_timeout(1200)
    await pg.locator('.item-view section[aria-label="Management change"]').evaluate('e => e.scrollIntoView({block: "start"})'); await pg.wait_for_timeout(600); await shot(4)
    await fresh(pg, base + '/#/c/LT'); await pg.locator('.p-item .og-btn').first.click(); await pg.wait_for_timeout(700)
    await top(pg, '.p-item.open'); await shot(5)
    await fresh(pg, base + '/#/look'); await shot(6)
    await fresh(pg, base + '/#/book'); await shot(7)
    await fresh(pg, base + '/#/'); await pg.evaluate('scrollTo(0, document.body.scrollHeight)'); await pg.wait_for_timeout(1500); await shot(8)

async def backup(pg, base, shot, row):
    await fresh(pg, base + '/#/'); await shot(1)
    await pg.locator('.window button', has_text='Week').first.click(); await pg.wait_for_timeout(900)
    await top(pg, '.card.move' if await pg.locator('.card.move').count() else '.card'); await shot(2)
    await top(pg, '.card.cat-results:has-text("Larsen")'); await shot(3)
    await top(pg, '.card.cat-management_change:has-text("Home First")'); await shot(4)
    await fresh(pg, base + '/#/c/LT'); await pg.locator(row).first.click(); await pg.wait_for_timeout(600)
    await top(pg, row); await shot(5)
    await fresh(pg, base + '/#/look'); await shot(6)
    await fresh(pg, base + '/#/book'); await shot(7)
    await fresh(pg, base + '/#/'); await pg.evaluate('scrollTo(0, document.body.scrollHeight)'); await pg.wait_for_timeout(1500); await shot(8)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for ver in VERSIONS:
            pg = await b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
            async def shot(n, ver=ver, pg=pg):
                await pg.screenshot(path=str(OUT / f's7-{ver}-{n}.png')); print(ver, n, MOMENTS[n - 1])
            try:
                if ver == 'next': await next_build(pg, shot)
                else: await backup(pg, BACKUPS[ver], shot, '.pgrid .og-btn' if ver == 'v4' else '.fo-prow-head')
            except Exception as e: print(ver, 'stopped:', str(e).splitlines()[0])
            await pg.close()
        await b.close()
asyncio.run(main())
