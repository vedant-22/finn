# Frame strips and short videos of the scroll motion, at 390x844 and 1440x900: the header leaving and coming back,
# card pictures settling as they scroll in, Today's opening and a company's header drifting, Look up's row, the load.
# usage: python3 scroll.py [base] [label] [scene ...]   writes shots/motion/{label}-{w}-{scene}.png and a .webm per size
import asyncio, sys, pathlib, shutil, time
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw
OUT = pathlib.Path(__file__).resolve().parents[3] / 'shots' / 'motion'
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173'
LABEL = sys.argv[2] if len(sys.argv) > 2 else 'local'
ONLY = set(sys.argv[3:])
SIZES = [(390, 844), (1440, 900)]

async def strip(pg, name, w, steps):
    # steps: a list of (action or None, wait ms); a frame after each
    shots = []
    for act, ms in steps:
        if act: await act()
        await pg.wait_for_timeout(ms)
        p = OUT / f'_f{len(shots)}.png'; await pg.screenshot(path=str(p)); shots.append(p)
    ims = [Image.open(p) for p in shots]
    k = 0.5 if w > 1000 else 1
    ims = [im.resize((int(im.width * k), int(im.height * k))) for im in ims]
    W, H = ims[0].size
    out = Image.new('RGB', (W * len(ims) + 8 * (len(ims) - 1), H), 'white')
    for i, im in enumerate(ims): out.paste(im, (i * (W + 8), 0))
    out.save(OUT / f'{LABEL}-{w}-{name}.png'); [p.unlink() for p in shots]; print(f'{LABEL}-{w}-{name}.png')

def wheel(pg, dy, n=6):
    async def go():
        for _ in range(n): await pg.mouse.wheel(0, dy / n); await pg.wait_for_timeout(16)
    return go

async def run(p, w, h):
    vid = OUT / f'_v{w}'; shutil.rmtree(vid, ignore_errors=True)
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={'width': w, 'height': h}, record_video_dir=str(vid), record_video_size={'width': w // (2 if w > 1000 else 1), 'height': h // (2 if w > 1000 else 1)})
    pg = await ctx.new_page()
    await pg.goto(BASE + '/#/'); await pg.wait_for_timeout(2500)
    await pg.mouse.move(w / 2, h / 2)
    want = lambda s: not ONLY or s in ONLY
    if want('today'):
        # down past the opening and the first card, then a short way back up
        await strip(pg, 'today', w, [(None, 0), (wheel(pg, 260), 120), (None, 600), (wheel(pg, 340), 120), (None, 600), (wheel(pg, -120), 120), (None, 600)])
    if want('book'):
        await pg.goto(BASE + '/#/book'); await pg.wait_for_timeout(2000); await pg.mouse.move(w / 2, h / 2)
        await strip(pg, 'book', w, [(None, 0), (wheel(pg, 400), 120), (None, 700), (wheel(pg, 500), 120), (None, 700), (wheel(pg, -160), 120), (None, 700)])
    if want('company'):
        await pg.goto(BASE + '/#/book'); await pg.wait_for_timeout(2000)
        await pg.locator('.book-card').first.click(); await pg.wait_for_timeout(1500); await pg.mouse.move(w / 2, h / 2)
        await strip(pg, 'company', w, [(None, 0), (wheel(pg, 200), 120), (None, 600), (wheel(pg, 400), 120), (None, 600), (wheel(pg, -150), 120), (None, 600)])
    if want('look'):
        await pg.goto(BASE + '/#/look'); await pg.wait_for_timeout(2000)
        row = pg.locator('.tiles-row, .tiles').last
        await row.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
        bx = await row.bounding_box()
        async def swipe():
            await pg.mouse.move(bx['x'] + bx['width'] / 2, bx['y'] + bx['height'] / 2)
            for _ in range(6): await pg.mouse.wheel(120 / 6 * 2, 0); await pg.wait_for_timeout(16)
        await strip(pg, 'look', w, [(None, 0), (swipe, 120), (None, 600), (swipe, 600)])
    if want('load'):
        # the app opening: the top 160px, a frame as fast as the browser gives them for the first second, stacked
        await pg.goto('about:blank'); shots = []
        await pg.goto(BASE + '/#/', wait_until='commit'); t0 = time.perf_counter()
        while time.perf_counter() - t0 < 1.0:
            p = OUT / f'_f{len(shots)}.png'; await pg.screenshot(path=str(p), clip={'x': 0, 'y': 0, 'width': w, 'height': 160})
            shots.append((p, int((time.perf_counter() - t0) * 1000)))
        ims = [Image.open(p) for p, _ in shots]
        out = Image.new('RGB', (w + 70, (160 + 4) * len(ims)), 'white'); d = ImageDraw.Draw(out)
        for i, (im, (_, ms)) in enumerate(zip(ims, shots)): out.paste(im, (70, i * 164)); d.text((6, i * 164 + 8), f'{ms} ms', fill='black')
        out.save(OUT / f'{LABEL}-{w}-load.png'); [p.unlink() for p, _ in shots]; print(f'{LABEL}-{w}-load.png')
    if want('hover') and w > 1000:
        await pg.goto(BASE + '/#/'); await pg.wait_for_timeout(2500)
        c = await pg.locator('.cards .card').first.bounding_box()
        async def mv(fx, fy):
            async def go(): await pg.mouse.move(c['x'] + c['width'] * fx, c['y'] + c['height'] * fy, steps=8)
            return go
        await strip(pg, 'hover', w, [(await mv(.3, .3), 400), (await mv(.6, .5), 120), (None, 400), (await mv(1.4, .5), 400)])
    await ctx.close(); await b.close()
    v = next(vid.glob('*.webm'), None)
    if v: v.rename(OUT / f'{LABEL}-{w}.webm'); print(f'{LABEL}-{w}.webm')
    shutil.rmtree(vid, ignore_errors=True)

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        for w, h in SIZES: await run(p, w, h)
asyncio.run(main())
