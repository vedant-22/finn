# Cold loads at 390x844 on a throttled phone profile: 150 ms round trip, 1.6 Mbps down, 750 kbps up, CPU 4x slower.
# Three loads, each in a fresh browser context (no cache, no worker); the medians of first contentful paint, largest
# contentful paint, and when Today's count first reads its final number. Then the gzip sizes of what Today loads.
# usage: python3 speed.py [base]   (default: a local preview at http://localhost:4173). Writes evals/speed_result.txt.
import asyncio, gzip, os, statistics, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
WEB = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(os.path.dirname(WEB), 'evals', 'speed_result.txt')
RUNS = 3
WATCH = """
window.__speed = {};
new PerformanceObserver(l => { for (const e of l.getEntries()) window.__speed.lcp = e.startTime }).observe({ type: 'largest-contentful-paint', buffered: true });
(function poll() {
  const f = document.querySelector('.hero-fig');
  if (f && /need a look|needs a look|Nothing/.test(f.textContent) && /^\\s*2(?!\\d)/.test(f.textContent)) window.__speed.count = performance.now();
  else requestAnimationFrame(poll);
})();
"""

async def once(p):
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block')
    pg = await ctx.new_page()
    cdp = await ctx.new_cdp_session(pg)
    await cdp.send('Network.enable')
    await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 150, 'downloadThroughput': 1.6e6 / 8, 'uploadThroughput': 750e3 / 8})
    await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
    await pg.add_init_script(WATCH)
    await pg.goto(base + '/#/', wait_until='load')
    for _ in range(600):   # the site's CSP forbids wait_for_function's eval; poll instead
        if await pg.evaluate('window.__speed && window.__speed.count'): break
        await pg.wait_for_timeout(100)
    await pg.wait_for_timeout(500)
    fcp = await pg.evaluate("performance.getEntriesByName('first-contentful-paint')[0]?.startTime")
    s = await pg.evaluate('window.__speed')
    await b.close()
    return fcp, s.get('lcp'), s['count']

def gz(path):
    with open(path, 'rb') as f: return len(gzip.compress(f.read(), 6))

async def main():
    async with async_playwright() as p:
        runs = [await once(p) for _ in range(RUNS)]
    med = lambda i: round(statistics.median(r[i] for r in runs))
    dist = os.path.join(WEB, 'dist')
    assets = os.listdir(os.path.join(dist, 'assets'))
    js = sum(gz(os.path.join(dist, 'assets', a)) for a in assets if a.endswith('.js'))
    css = sum(gz(os.path.join(dist, 'assets', a)) for a in assets if a.endswith('.css'))
    push, net = gz(os.path.join(dist, 'data', 'push.json')), gz(os.path.join(dist, 'data', 'network.json'))
    lines = [
        f'profile: 390x844, 150 ms RTT, 1.6 Mbps down, 750 kbps up, CPU 4x; {RUNS} cold loads of {base}, medians',
        f'runs (fcp, lcp, count) ms: {[tuple(round(x) for x in r) for r in runs]}',
        f'FCP {med(0)} ms', f'LCP {med(1)} ms', f'count settled {med(2)} ms',
        f'gzip KB: JS {js / 1000:.0f}, CSS {css / 1000:.0f}, push.json {push / 1000:.0f}, network.json {net / 1000:.0f}',
    ]
    print('\n'.join(lines))
    if '--write' in sys.argv:
        with open(OUT, 'w') as f: f.write('\n'.join(lines) + '\n')

asyncio.run(main())
