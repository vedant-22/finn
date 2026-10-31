# The stage 4 flows at 390x844: the brief read to the end, the window, your lines, Book, a company, Ask.
# usage: python3 flows.py [base]   (default: finn-ledger-next). Prints each check; exits 1 if one fails.
import asyncio, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-ledger-next.vercel.app'
fails = []
def check(name, ok, got=''):
    print(('ok   ' if ok else 'FAIL ') + name + (f'  [{got}]' if got != '' else ''))
    if not ok: fails.append(name)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear()'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(2000)
        fig = lambda: pg.locator('.hero-fig').inner_text()
        check('brief opens on 2 to read', (await fig()).replace('\n', ' ') == '2 to read', await fig())
        check('two notifications', await pg.locator('.notif').count() == 2)
        syn = lambda: pg.locator('.notif', has_text='Syngene').first.locator('.notif-v').inner_text()
        syn24 = await syn()
        for w, want in [('3 days', 6), ('Week', 6), ('Month', 6), ('24 hours', 2)]:
            await pg.get_by_role('radio', name=w, exact=True).click(); await pg.wait_for_timeout(500)
            check(f'window {w}', await pg.locator('.notif').count() == want, await pg.locator('.notif').count())
            if w == 'Week': check('one event, one figure in every window', await syn() == syn24, f'{syn24} / {await syn()}')
        # Your lines from a notification's line; a tighter move line adds to the count
        await pg.locator('.notif-line').first.click(); await pg.wait_for_timeout(500)
        sheet = pg.locator('.sheet[aria-label="Your lines"]')
        check('lines open from a notification', await sheet.is_visible())
        before = await sheet.locator('.lines > .sub b').inner_text()
        await pg.get_by_role('button', name='Lower Price move in a day').click(); await pg.get_by_role('button', name='Lower Price move in a day').click(); await pg.wait_for_timeout(300)
        after = await sheet.locator('.lines > .sub b').inner_text()
        check('a lower line lets more through', int(after) >= int(before), f'{before} -> {after}')
        await pg.get_by_role('button', name='Reset to defaults').click()
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        check('lines close', not await sheet.is_visible())
        # Read the brief to the end
        await pg.get_by_role('button', name='Read the brief').click(); await pg.wait_for_timeout(900)
        check('reader opens at 1 of 2', await pg.locator('.r-count').inner_text() == '1 of 2')
        check('results behind the move', await pg.locator('.figs tbody tr:not(.figs-margin)').count() == 4)
        # Their word comes from the company's file, fetched as the item opens: wait for it rather than a fixed time
        try: await pg.locator('.r-sec .ba').first.wait_for(timeout=10000)
        except Exception: pass
        check('held against their word', await pg.locator('.r-sec .ba').count() >= 1)
        await pg.locator('.ask-chip').first.click(); await pg.wait_for_timeout(800)
        check('ask in place answers', await pg.locator('.r-sec .answer .head').count() == 1)
        await pg.get_by_role('button', name='Done', exact=True).click(); await pg.wait_for_timeout(600)
        await pg.get_by_role('button', name='Keep for later').click(); await pg.wait_for_timeout(600)
        await pg.get_by_role('button', name='Mark all read').click(); await pg.wait_for_timeout(700)
        check('ends up to date', 'up to date' in (await pg.locator('.done-t').inner_text()).lower())
        await pg.get_by_role('button', name='Back to the brief').click(); await pg.wait_for_timeout(800)
        check('brief says up to date', 'Up to date' in await fig())
        check('kept item listed', await pg.locator('#kept-h').count() == 1)
        await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(1500)
        check('state survives a reload', 'Up to date' in await fig())
        await pg.get_by_role('button', name='Bring back what you cleared').click(); await pg.wait_for_timeout(500)
        check('bring back', (await fig()).replace('\n', ' ') == '2 to read')
        # Book: filter, open a company, Back keeps the scroll
        await pg.goto(base + '/#/book'); await pg.wait_for_timeout(2500)
        await pg.locator('.tally-b').first.click(); await pg.wait_for_timeout(400)
        check('book filter', 'with a promise missed' in await pg.locator('.book .sec .head').inner_text())
        await pg.locator('.tally-b').first.click(); await pg.wait_for_timeout(300)
        await pg.evaluate('scrollTo(0,900)'); await pg.wait_for_timeout(400); y0 = await pg.evaluate('scrollY')
        await pg.locator('.hold').nth(6).click(); await pg.wait_for_timeout(1500)
        check('company opens', await pg.locator('.co-top .title').count() == 1)
        await pg.locator('.prow-head').first.click(); await pg.wait_for_timeout(500)
        check('promise opens on before-and-after', await pg.locator('.prow.open .ba-said').count() == 1)
        await pg.get_by_role('button', name='Back').click(); await pg.wait_for_timeout(1500)
        check('back keeps the scroll', abs(await pg.evaluate('scrollY') - y0) < 40, (y0, await pg.evaluate('scrollY')))
        # Ask
        await pg.goto(base + '/#/ask'); await pg.wait_for_timeout(1200)
        check('ask lists companies outside the book', await pg.locator('.ask-try .rows').nth(1).locator('li').count() == 5)
        await pg.locator('#ask').fill('Did L&T deliver on revenue growth?'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1200)
        head = await pg.locator('.answer > .head').inner_text()
        check('ask about L&T', 'Larsen & Toubro on revenue growth: missed' in head, head)
        check('answer is promised against delivered', await pg.locator('.answer .ba .st-missed').count() >= 1)
        await pg.locator('#ask').fill('Who missed a promise?'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
        check('book question', 'missed' in await pg.locator('.answer > .head').inner_text())
        await pg.locator('#ask').fill('ASTRAL'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(600)
        check('unknown company offers research', await pg.get_by_role('button', name='Read ASTRAL').count() == 1)
        # All quiet: strict lines, and the brief offers the nearest wider window that has something
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear(); localStorage.setItem("finn.lines", JSON.stringify({hours: 24, volX: 50, movePct: 15, interrupt: []}))'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(1500)
        wide = pg.locator('.hero .link')
        check('all quiet offers a wider window', await wide.count() == 1 and 'to read' in await wide.inner_text())
        await wide.click(); await pg.wait_for_timeout(600)
        check('the wider window opens with its items', await pg.locator('.stops .on').inner_text() == 'Month' and await pg.locator('.notif').count() >= 1)
        check('no page errors', not errs, errs)
        await b.close()
asyncio.run(main())
sys.exit(1 if fails else 0)
