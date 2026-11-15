# Accessibility at 390x844: axe-core (WCAG 2.2 A and AA rules) on every main view and both sheets, with 0 serious or
# critical findings allowed; every visible control at least 24x24 px (WCAG 2.5.8, inline links in a sentence exempt);
# Tab reaches the masthead's pill; with reduced motion the count reads its number at first paint and nothing animates.
# usage: python3 a11y.py [base]   (default: finn-network). Prints each check; exits 1 if one fails.
import asyncio, os, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-network.vercel.app'
AXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'node_modules', 'axe-core', 'axe.min.js')
TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
# Rules left off, each with its reason. None today.
OFF: dict[str, str] = {}
fails = []
VIEWS = {}   # view -> (serious or critical, controls under 24 px)
def check(name, ok, got=''):
    print(('ok   ' if ok else 'FAIL ') + name + (f'  [{got}]' if got != '' and not ok else ''))
    if not ok: fails.append(name)

SMALL = """() => [...document.querySelectorAll('button, a[href], input, select, [role=switch], [role=radio], [tabindex="0"]')].filter(e => {
  const r = e.getBoundingClientRect(), s = getComputedStyle(e)
  if (!r.width || !r.height || s.visibility === 'hidden' || e.closest('[inert], [aria-hidden=true]')) return false
  if (s.display === 'inline') return false            // a link inside a sentence: the inline exception
  if (e.type === 'checkbox' && e.closest('label')) { const l = e.closest('label').getBoundingClientRect(); return l.width < 24 || l.height < 24 }
  return r.width < 23.5 || r.height < 23.5
}).map(e => `${e.tagName.toLowerCase()}.${e.className || ''} "${(e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 30)}" ${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`)"""

async def audit(pg, name):
    await pg.add_script_tag(path=AXE)
    res = await pg.evaluate("tags => axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] })", TAGS)
    bad = [v for v in res['violations'] if v['impact'] in ('serious', 'critical') and v['id'] not in OFF]
    check(f'{name}: 0 serious or critical', not bad, [(v['id'], v['impact'], [n['target'] for n in v['nodes'][:3]]) for v in bad])
    minor = [(v['id'], v['impact'], len(v['nodes'])) for v in res['violations'] if v not in bad]
    if minor: print(f'     (moderate or minor, not gated: {minor})')
    small = await pg.evaluate(SMALL)
    check(f'{name}: every control at least 24x24', not small, small[:6])
    VIEWS[name] = (len(bad), len(small))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 390, 'height': 844}, bypass_csp=True); pg = await ctx.new_page()   # axe is injected; the site's CSP rightly forbids that
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear()'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(2600)
        await audit(pg, 'Today')
        await pg.locator('.cards .card .read-more').first.click(); await pg.wait_for_timeout(1500)
        await audit(pg, 'An opened card')
        await pg.goto(base + '/#/book'); await pg.wait_for_timeout(2000)
        await audit(pg, 'Holdings')
        await pg.goto(base + '/#/c/KPIL'); await pg.wait_for_timeout(2000)
        await audit(pg, 'A company')
        await pg.goto(base + '/#/c/MARUTI')
        head = pg.locator('button.fold-head', has_text='The annual report'); await head.wait_for(timeout=15000); await head.click()
        # the fold fades in over about a second; axe reads contrast mid-fade, so wait for it to settle
        await pg.get_by_role('button', name='Read the paragraph').first.click(); await pg.wait_for_timeout(1500)
        await audit(pg, 'The annual report, a paragraph open')
        await pg.goto(base + '/#/ask'); await pg.wait_for_timeout(1500)
        await audit(pg, 'Look up')
        await pg.locator('#sym').fill('Did L&T deliver on revenue growth?'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2000)
        await audit(pg, 'Look up, an answer')
        await pg.locator('#sym').fill('Brief me before I meet Home First'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
        check('a network path is on screen', await pg.locator('.answer .path-line').count() >= 1)
        await audit(pg, 'A network path')
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(1500)
        await pg.get_by_role('button', name='Change alert levels').click(); await pg.wait_for_timeout(600)
        await audit(pg, 'Your alert levels')
        await pg.get_by_role('dialog', name='Your alert levels').get_by_role('button', name='Your data').click(); await pg.wait_for_timeout(900)
        await audit(pg, 'Your data')
        # The keyboard: from a fresh load, Tab reaches the pill within the first three stops
        await pg.goto(base + '/#/'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(2000)
        hit = False
        for _ in range(3):
            await pg.keyboard.press('Tab')
            if await pg.evaluate("!!document.activeElement?.classList.contains('demo-pill')"): hit = True; break
        check('Tab reaches the pill within three stops', hit)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(700)
        check('... Enter opens Your data, focus inside it', await pg.evaluate("!!document.activeElement?.closest('[role=dialog][aria-label=\"Your data\"]')"))
        await b.close()
        # Reduced motion: the count is its number at first paint, and nothing is animating once loaded
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce'); pg = await ctx.new_page()
        await pg.goto(base + '/#/', wait_until='domcontentloaded'); await pg.wait_for_selector('.hero-fig', timeout=10000)
        first = (await pg.locator('.hero-fig').inner_text()).replace('\n', ' ')
        check('reduced motion: the count reads its number at first paint', first.replace('\n', ' ') == '2 of your companies need a look today', first)
        await pg.wait_for_timeout(2600)
        await pg.mouse.wheel(0, 1600); await pg.wait_for_timeout(800)
        anims = await pg.evaluate("document.getAnimations().filter(a => a.playState === 'running').map(a => (a.effect?.target?.className || '') + ' ' + (a.animationName || a.transitionProperty || ''))")
        check('reduced motion: nothing animates after load, scrolled too', not anims, anims[:6])
        await b.close()
asyncio.run(main())
print(f"{'FAIL' if fails else 'ok'}: {len(fails)} failed")
if '--write' in sys.argv:
    clean = sum(1 for v in VIEWS.values() if v[0] == 0)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'evals', 'a11y_result.txt'), 'w') as f:
        f.write(f'{base}, 390x844, axe-core tags {" ".join(TAGS)}\n'
                f'views {len(VIEWS)}: {", ".join(VIEWS)}\n'
                f'0 serious or critical on {clean} of {len(VIEWS)} views\n'
                f'controls under 24 px: {sum(v[1] for v in VIEWS.values())}\n'
                f'rules left off: {len(OFF)}\n'
                f'checks failed: {len(fails)}\n')
sys.exit(1 if fails else 0)
