import asyncio, json, os, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
d='/Users/vedantiwari/ENAM-FINN/app/web/public/data'
syms=sorted({f[:-5] for f in os.listdir(d+'/companies')} if os.path.isdir(d+'/companies') else [])
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in (320, 390):
            pg = await b.new_page(viewport={'width':w,'height':800}); errs=[]
            pg.on('pageerror', lambda e: errs.append(str(e)))
            bad=[]
            for s in syms:
                await pg.goto(f'{base}/#/c/{s}'); await pg.wait_for_timeout(700)
                r = await pg.evaluate("() => [document.documentElement.scrollWidth, /NaN|undefined/.test(document.body.innerText)]")
                if r[0] > w or r[1]: bad.append((s, r))
            print(w, len(syms), 'bad:', bad, 'errors:', errs[:3]); await pg.close()
        await b.close()
asyncio.run(main())
