import asyncio, sys
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':390,'height':844})
        for h,names in [('#/c/LT',['For and against','The numbers','Read for this page']),('#/',['Worth a look','Routine filings'])]:
            await pg.goto(base+'/'+h); await pg.wait_for_timeout(1500)
            for t in names:
                btn=pg.get_by_role('button', name=t).first
                await btn.scroll_into_view_if_needed(); await pg.wait_for_timeout(900)
                await btn.click(); await pg.wait_for_timeout(1500)
                op=await btn.evaluate("e=>getComputedStyle(e.closest('section')).opacity")
                print(h, t, 'opacity', op)
                await btn.click(); await pg.wait_for_timeout(300)
        await b.close()
asyncio.run(main())
