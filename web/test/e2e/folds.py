# Every fold opens in place, its rows fully shown, and what sits below it slides back to rest (no transform left over;
# the scroll motion's own targets, the header, card pictures and the opening's drift, hold a transform by design)
# usage: python3 folds.py [base]   exits 1 on a failed check
import asyncio, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
bad = []

async def fold(pg, where, title):
    head = pg.locator('.fold-head', has_text=title).first
    await head.scroll_into_view_if_needed(); await pg.wait_for_timeout(900)
    await head.click(); await pg.wait_for_timeout(900)
    sec = head.locator('xpath=ancestor::section[1]')
    rows = await sec.locator('.acc-in > *').count()
    op = await sec.locator('.acc-in > *').first.evaluate('e => getComputedStyle(e).opacity') if rows else '0'
    left = await pg.evaluate('''() => [...document.querySelectorAll('main *, .iv-page *')].filter(e => e.style.transform && !e.matches('.mast, .bar, .card-img > *, .hero > *, .co-top > *')).length''')
    ok = rows > 0 and op == '1' and left == 0
    print(where, title, 'rows', rows, 'opacity', op, 'still moving', left, 'ok' if ok else 'FAIL')
    if not ok: bad.append((where, title))
    await head.click(); await pg.wait_for_timeout(900)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844})
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(2000)
        for t in ['Worth a look', 'Routine announcements']: await fold(pg, '#/', t)
        await pg.goto(base + '/#/c/LT'); await pg.wait_for_timeout(2500)
        for t in ['Not yet due', 'For and against', 'The numbers', 'Sources for this page']:
            if await pg.locator('.fold-head', has_text=t).count(): await fold(pg, '#/c/LT', t)
        await b.close()
    sys.exit(1 if bad else 0)
asyncio.run(main())
