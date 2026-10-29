import asyncio, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger.vercel.app'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':390,'height':844})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(2000)
        out = {}
        for w in ['24h','3 days','Week','Month']:
            await pg.get_by_role('radio', name=w, exact=True).click(); await pg.wait_for_timeout(500)
            out[w] = (await pg.locator('.hero-fig').first.inner_text()).replace('\n',' '), await pg.locator('.cards .card').count()
        # Alert lines live in the menu's index list
        await pg.get_by_role('button', name='Menu', exact=True).click(); await pg.wait_for_timeout(500)
        await pg.locator('.fo-row', has_text='Alert lines').click(); await pg.wait_for_timeout(500)
        lines = pg.locator('.sheet[aria-label="Alert lines"]')
        out['lines_open'] = await lines.is_visible() and not await pg.locator('.sheet[aria-label="Menu"]').is_visible()
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(600)
        out['lines_closed'] = not await lines.is_visible()
        await pg.goto(base + '/#/book'); await pg.wait_for_timeout(2500)
        await pg.locator('.og-btn').nth(0).click(); await pg.wait_for_timeout(400)
        out['filter'] = await pg.locator('.book-filter').inner_text()
        await pg.locator('.og-btn').nth(0).click(); await pg.wait_for_timeout(400)
        await pg.evaluate('scrollTo(0,1400)'); await pg.wait_for_timeout(600)
        y0 = await pg.evaluate('scrollY')
        await pg.locator('.tile-card').nth(4).click(); await pg.wait_for_timeout(1500)
        out['co'] = await pg.locator('.co-name').inner_text()
        await pg.get_by_role('button', name='Back').click(); await pg.wait_for_timeout(1500)
        out['scroll'] = (y0, await pg.evaluate('scrollY'))
        await pg.goto(base + '/#/look'); await pg.wait_for_timeout(1500)
        await pg.locator('#sym').fill('larsen'); await pg.wait_for_timeout(500)
        out['suggest'] = await pg.locator('main').inner_text()
        out['suggest'] = 'Larsen' in out['suggest']
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
        out['look_open'] = pg.url
        out['errors'] = errs
        for k,v in out.items(): print(k, v)
        await b.close()
asyncio.run(main())
