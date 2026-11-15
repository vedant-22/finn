# The recorded walkthrough, checked: reads each beat's `On screen:` strings from docs/WALKTHROUGH_SCRIPT.md, starts
# from cleared storage, does the beat's taps at 390x844 and checks that every string was on screen during the beat.
# Asks /api/sources (no model call) whether the link has a model key; without one the optional beat is skipped.
# usage: python3 web/test/e2e/walkthrough.py [base]   (default: finn-network). Exits 1 if a check fails.
import asyncio, json, os, re, sys, urllib.request
from playwright.async_api import async_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
base = (sys.argv[1] if len(sys.argv) > 1 else 'https://finn-network.vercel.app').rstrip('/')
SCRIPT = open(os.path.join(ROOT, 'docs/WALKTHROUGH_SCRIPT.md')).read()
BEATS = {t: re.findall(r'`([^`]+)`', re.search(r'(?m)^On screen: (.*)$', body).group(1))
         for t, body in re.findall(r'(?ms)^### (.+?)\n(.*?)(?=^### |\Z)', SCRIPT)}
flat = lambda s: re.sub(r'\s+', '', s).casefold()
fails = []
def check(name, ok, got=''):
    print(('ok   ' if ok else 'FAIL ') + name + (f'  [{got}]' if got != '' else ''))
    if not ok: fails.append(name)

def has_key():
    try:
        r = urllib.request.Request(base + '/api/sources', json.dumps({'symbol': 'ASTRAL'}).encode(), {'Content-Type': 'application/json'})
        with urllib.request.urlopen(r, timeout=30) as f:
            return json.loads(f.read()).get('live') is True
    except Exception:
        return False

async def main():
    key = has_key()
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        seen = []
        async def look(): seen.append(flat(await pg.locator('body').inner_text()))
        tab = lambda name: pg.locator('nav.tabs').get_by_text(name, exact=True).first.click()
        async def beat(n):
            title = next(t for t in BEATS if t.startswith(n))
            for s in BEATS[title]:
                check(f'{title.split(" (")[0]}: {s[:60]}', any(flat(s) in x for x in seen))
            seen.clear()

        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear()'); await pg.reload(wait_until='domcontentloaded')
        await pg.wait_for_timeout(2600); await look(); await beat('1.')
        await pg.locator('.card', has_text='Syngene').first.locator('.read-more').click(); await pg.wait_for_timeout(1000)
        try: await pg.locator('.item-view .word-item').first.wait_for(timeout=10000)
        except Exception: pass
        await look(); await beat('2.')
        await pg.locator('.item-view').get_by_role('button', name='Back').click(); await pg.wait_for_timeout(900)
        await pg.get_by_role('button', name='Change alert levels').click(); await pg.wait_for_timeout(500); await look()
        for _ in range(2): await pg.get_by_role('button', name='Lower Price move in a day').click()
        await pg.wait_for_timeout(300); await look()
        await pg.get_by_role('button', name='Reset to defaults').click(); await pg.wait_for_timeout(300)
        await pg.get_by_role('dialog', name='Your alert levels').get_by_role('button', name='Your data').click(); await pg.wait_for_timeout(900); await look()
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        await beat('3.')
        await tab('Holdings'); await pg.wait_for_timeout(2000)
        await pg.locator('.book-card[data-sym="LT"]').click(); await pg.wait_for_timeout(1500)
        await pg.locator('.p-item .og-btn').first.click(); await pg.wait_for_timeout(600); await look()
        href = await pg.locator('.p-item.open a', has_text='page 9').first.get_attribute('href')
        check('4. The ledger: the quote links to its page', (href or '').endswith('#page=9'), href)
        await beat('4.')
        await pg.get_by_role('button', name='Back').first.click(); await pg.wait_for_timeout(900)
        await pg.locator('.book-card[data-sym="ULTRACEMCO"]').click()
        ar = pg.locator('button.fold-head', has_text='The annual report'); await ar.wait_for(timeout=15000); await ar.click(); await pg.wait_for_timeout(500)
        await pg.get_by_role('button', name='Read the paragraph').first.click(); await pg.wait_for_timeout(400); await look()
        await beat('4b')
        await tab('Look up'); await pg.wait_for_timeout(1200)
        await pg.locator('.net-chips .btn-outline', has_text='Brief me before I meet Home First').click(); await pg.wait_for_timeout(2500)
        await look(); await beat('5.')
        if key:
            await pg.goto(base + '/#/c/ASTRAL')
            try: await pg.get_by_text('Checking promises against the numbers').first.wait_for(timeout=30000)
            except Exception: pass
            await look(); await beat('Optional')
        else:
            print('skip the optional beat: the link has no model key, so record without it')
        if key: await pg.goto(base + '/#/c/LT'); await pg.wait_for_timeout(1500)
        await tab('Today'); await pg.wait_for_timeout(1500)
        await pg.locator('.end-band').scroll_into_view_if_needed(); await pg.wait_for_timeout(500); await look(); await beat('6.')
        check('no page errors', not errs, errs[:2])
        await b.close()
    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    sys.exit(1 if fails else 0)

asyncio.run(main())
