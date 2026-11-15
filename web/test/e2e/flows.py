# The flows at 390x844: Today and its window, your lines, a card opened into its full view and closed, the folds,
# Book, a company, Look up (a symbol, a name, a question, an unknown symbol), a filing kind switched off, all quiet.
# usage: python3 flows.py [base]   (default: finn-network). Prints each check; exits 1 if one fails.
import asyncio, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from playwright.async_api import async_playwright
base = sys.argv[1] if len(sys.argv) > 1 else 'https://finn-network.vercel.app'
fails = []
def check(name, ok, got=''):
    print(('ok   ' if ok else 'FAIL ') + name + (f'  [{got}]' if got != '' else ''))
    if not ok: fails.append(name)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear()'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(2600)
        fig = lambda: pg.locator('.hero-fig').inner_text()
        check('Today opens on 2 of your companies need a look today', (await fig()).replace('\n', ' ') == '2 of your companies need a look today', await fig())
        check('two cards that need a look, then one about people you know, last', await pg.locator('.cards .card').count() == 3 and await pg.locator('.cards li:last-child .card-netcard').count() == 1)
        check('... the grey line names it apart from the count', (await pg.locator('.hero-2').inner_text()).endswith('. One more is about people you know.'), await pg.locator('.hero-2').inner_text())
        nc = pg.locator('.card-netcard')
        check('... titled with the companies, the person in the sentence, labelled', await nc.locator('.card-title').inner_text() == 'Home First Finance and HDFC Bank'
              and await nc.locator('.card-desc').inner_text() == 'A new CFO at Home First Finance and a new MD & CEO at HDFC Bank: one call to Meera Krishnan, CFO at Aavas Financiers, has a question for each.' and 'sample contacts' in (await nc.inner_text()).lower(), await nc.inner_text())
        await nc.locator('.read-more').click(); await pg.wait_for_timeout(1000)
        nv = pg.locator('.item-view')
        check('... it opens to each company\'s question for the one person, and the call sheet', await nv.locator('.net-row').count() == 2
              and 'What catches a new CFO out in housing finance?' in await nv.inner_text() and 'Were you at ICICI Bank with Anup Bagchi, and what is Anup remembered for there?' in await nv.inner_text()
              and await nv.get_by_role('button', name='Copy the call sheet').count() == 1 and 'it passed none of your alert levels' in await nv.inner_text())
        check('... its deep link is its key', 'net%7Conecall%7CHDFCBANK%2CHOMEFIRST%7C2026-10-27%7Cmeera-krishnan' in pg.url or 'net|onecall|HDFCBANK,HOMEFIRST|2026-10-27|meera-krishnan' in pg.url, pg.url)
        await nv.get_by_role('button', name='Back').click(); await pg.wait_for_timeout(900)
        syn = lambda: pg.locator('.card', has_text='Syngene').first.locator('.o-val').inner_text()
        syn24 = await syn()
        for w, want in [('3 days', 6), ('Week', 6), ('Month', 6), ('24 hours', 2)]:
            await pg.get_by_role('radio', name=w, exact=True).click(); await pg.wait_for_timeout(500)
            check(f'window {w}', (await pg.locator('.cards .card:not(.card-netcard)').count(), await pg.locator('.cards .card-netcard').count()) == (want, 1),
                  (await pg.locator('.cards .card:not(.card-netcard)').count(), await pg.locator('.cards .card-netcard').count()))
            if w == 'Week': check('one event, one figure in every window', await syn() == syn24, f'{syn24} / {await syn()}')
        # Your alert levels from the end band; a tighter move line lets more through
        await pg.get_by_role('button', name='Change alert levels').click(); await pg.wait_for_timeout(500)
        sheet = pg.locator('.sheet[aria-label="Your alert levels"]')
        check('lines open', await sheet.is_visible())
        count = lambda: sheet.locator('.lines > .serif-line').inner_text()
        before = await count()
        for _ in range(2): await pg.get_by_role('button', name='Lower Price move in a day').click()
        await pg.wait_for_timeout(300); after = await count()
        n = lambda t: int(t.split('At these levels, ')[1].split(' ')[0])
        check('a lower line lets more through', n(after) >= n(before), f'{n(before)} -> {n(after)}')
        await pg.get_by_role('button', name='Reset to defaults').click()
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        check('lines close', not await sheet.is_visible())
        # A card opens into its full view; Back returns to the same place
        await pg.evaluate('scrollTo(0, 300)'); await pg.wait_for_timeout(300); y0 = await pg.evaluate('scrollY')
        await pg.locator('.card .read-more').first.click(); await pg.wait_for_timeout(1000)
        view = pg.locator('.item-view')
        check('a card opens its full view', await view.count() == 1 and 'Syngene' in await view.locator('h1').inner_text())
        check('results: four lines, QoQ and YoY', await view.locator('.figs tbody tr:not(.figs-margin)').count() == 4 and await view.locator('.figs thead th').count() == 4)
        check('the management change with its background', await view.locator('.people li').count() >= 1)
        leena = await view.locator('.net-row', has_text='Leena Joshi').first.inner_text()
        check('the CFO left: the one who fits is someone who worked there, with the seat question from where they sat', 'Where did R&D and finance pull against each other at Syngene?' in leena and 'Why are so many' not in leena, leena)
        asks = await view.locator('.net-asks').inner_text() if await view.locator('.net-asks').count() else ''
        check('... two who only moved off the senior list are not counted as leaving, so no "so many leaving" question', 'Why are so many' not in asks, asks)
        check('... and the filing says they stay', await view.locator('.people li', has_text='no longer listed as senior management').count() == 2)
        try: await view.locator('.word-item').first.wait_for(timeout=10000)
        except Exception: pass
        check('held against their word', await view.locator('.word-item').count() >= 1)
        await view.locator('.ask-chip').first.click(); await pg.wait_for_timeout(900)
        check('ask in place answers', await view.locator('.answer .t-b1').count() == 1)
        await view.get_by_role('button', name='Back').click(); await pg.wait_for_timeout(900)
        check('Back closes the view', await pg.locator('.item-view').count() == 0)
        check('Back keeps the scroll', abs(await pg.evaluate('scrollY') - y0) < 40, (y0, await pg.evaluate('scrollY')))
        await pg.goto(base + '/#/read/' + 'nothing-here'); await pg.wait_for_timeout(800)
        check('a stale item link says so', 'Not in this window' in await pg.locator('.item-view h1').inner_text())
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(1200)
        # The folds open in place
        # Seen without a tap: the Network's fold says its first notice while it is closed
        net = pg.locator('.fold', has_text='People you know')
        check('the closed fold says what the network noticed, and not the card it raised', await net.locator('.fold-l').inner_text() == 'Three people you know have worked where Rinkoo Somani works or has worked.', await net.locator('.fold-l').inner_text())
        await net.locator('.fold-head').click(); await pg.wait_for_timeout(600)
        check('opened, the raised one call is not said again', 'One call' not in await net.inner_text() and await net.locator('.fold-l').count() == 0)
        check('a day\'s fold holds only what is dated in the day', await net.locator('.note').count() == 2 and await net.locator('.note', has_text='Arvind Pillai').count() == 0 and await net.locator('.note', has_text='A reason to call').count() == 0 and 'going cold' not in await net.inner_text(), await net.locator('.note').count())
        await net.locator('.fold-head').click(); await pg.wait_for_timeout(500)
        await pg.get_by_role('button', name='Worth a look (4)').click(); await pg.wait_for_timeout(500)
        check('Worth a look opens', await pg.locator('.fold.is-open .note').count() == 4)
        await pg.get_by_role('button', name='Routine announcements (3)').click(); await pg.wait_for_timeout(500)
        check('Routine announcements opens', await pg.locator('.fold.is-open .folded li').count() >= 1)
        check('the window ends on its band', 'last 24 hours' in await pg.locator('.end-band h2').inner_text())
        band = await pg.locator('.end-qs').inner_text()
        check('Ask first fits the question: a former insider for the departure, a competitor today for the margin',
              'Ask first: Dr. Leena Joshi, Director, Discovery Chemistry there, 2011–2019. Where did R&D and finance pull against each other at Syngene?' in band
              and 'Ask first: Anand Raghavan, Chief Operating Officer, Urban Infrastructure, Tata Projects, a competitor. Which costs are moving most in engineering & construction, as Tata Projects sees it?' in band, band)
        check('... the L&T card names the same person', 'Ask someone you know: Anand Raghavan, Chief Operating Officer, Urban Infrastructure, Tata Projects, a competitor.' in await pg.locator('.card', has_text='Larsen').first.inner_text())
        # The path: an arrival's card says how many of your people are on it; the full view draws it, one question each
        await pg.context.grant_permissions(['clipboard-read', 'clipboard-write'])
        await pg.get_by_role('radio', name='3 days', exact=True).click(); await pg.wait_for_timeout(600)
        home = pg.locator('.card', has_text='Home First').first
        check('an arrival\'s card counts your people on the path', "Three people you know have worked where Rinkoo Somani works or has worked." in await home.inner_text())
        await home.locator('.read-more').click(); await pg.wait_for_timeout(1200)
        sec = pg.locator('section[aria-label="Who was there"]')
        check('the full view shows Who was there', await sec.count() == 1 and await pg.locator('section[aria-label="Who to ask"]').count() == 0)
        check('four people, one question each', (await sec.locator('.path-line .stn-ask').count(), await sec.locator('.path-line .stn-who').count()) == (4, 4))
        check('the gap is a station of its own', 'No housing finance employer in the filing' in await sec.locator('.stn-gap').inner_text())
        check('in the room: the question for the person', 'What was the interim brief at IDFC Limited?' in await sec.locator('.path-room').inner_text())
        top, end = await sec.locator('h2').bounding_box(), await sec.locator('.path-copy').bounding_box()
        check('the path fits in 560 px at 390 wide', end['y'] + end['height'] - top['y'] <= 560, round(end['y'] + end['height'] - top['y']))
        await sec.locator('.path-copy').click(); await pg.wait_for_timeout(300)
        clip = await pg.evaluate('navigator.clipboard.readText()')
        check('Copy the call sheet: names and questions', all(x in clip for x in ('Kavita Deshmukh', 'Nitin Agarwal', 'Were you at IDFC Limited with Rinkoo Somani, and what did treasury need from the CFO?', 'Used to work at IDFC Limited', 'In the room')), clip[:60])
        text = await sec.inner_text()
        check('the path has no NaN or undefined', 'NaN' not in text and 'undefined' not in text)
        await pg.set_viewport_size({'width': 320, 'height': 844}); await pg.wait_for_timeout(400)
        check('the path at 320: no sideways scroll', await pg.evaluate('document.documentElement.scrollWidth') <= 320)
        await pg.set_viewport_size({'width': 390, 'height': 844})
        await pg.goto(base + '/#/look'); await pg.wait_for_timeout(1200)
        await pg.locator('.net-chips .btn-outline', has_text='Brief me before I meet Home First').click(); await pg.wait_for_timeout(2500)
        try: await pg.locator('.answer .path-line .stn-ask').first.wait_for(timeout=45000)   # answered by /api: a cold instance on the link takes seconds
        except Exception: pass
        check('Brief me before I meet Home First: the same path', await pg.locator('.answer .path-line .stn-ask').count() == 4 and 'Meeting Home First Finance' in await pg.locator('.answer > .t-b1').inner_text())
        check('no sideways scroll on the answer', await pg.evaluate('document.documentElement.scrollWidth') <= 390)
        # Asked directly, a person with a path is answered by it: the filing gives no years, so nobody "overlapped" and nobody is "ruled out"
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(600); await pg.goto(base + '/#/look'); await pg.wait_for_timeout(1200)
        await pg.locator('.net-chips .btn-outline', has_text='Who knows the new MD of HDFC Bank?').click(); await pg.wait_for_timeout(2500)
        try: await pg.locator('.answer .path-line .stn-ask').first.wait_for(timeout=45000)   # answered by /api: a cold instance on the link takes seconds
        except Exception: pass
        who = await pg.locator('.answer').inner_text()
        check('Who knows …? is answered by the path, and claims no overlap', await pg.locator('.answer .path-line .stn-ask').count() == 2 and 'The filing gives no years' in who and 'overlapped' not in who and 'Ruled out' not in who, who[:80])
        check('... each asked what they can know', 'Were you at ICICI Securities with Anup Bagchi, and what is Anup remembered for there?' in who)
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(1200)
        # Two filings read together: the month's fold leads with the pattern, and the company page carries it with one person, one question
        await pg.get_by_role('radio', name='Month', exact=True).click(); await pg.wait_for_timeout(600)
        mc = pg.locator('.card-netcard')
        check('the month\'s network card is the pattern across filings', await mc.locator('.card-title').inner_text() == 'Crompton'
              and (await mc.locator('.card-desc').inner_text()).startswith('Within two days, the Head of Internal Audit, Risk & Control moved to another role in the company'))
        await mc.locator('.read-more').click(); await pg.wait_for_timeout(1000)
        mv = pg.locator('.item-view')
        check('... it opens to the filings\' words, the one person and question, and the question for management', 'No successor is filed for either.' in await mv.inner_text()
              and 'How long does it usually take to fill audit and compliance seats in consumer electricals?' in await mv.inner_text() and 'Who holds audit and compliance at Crompton now, and who do they report to?' in await mv.inner_text()
              and await mv.get_by_role('button', name='Open Crompton').count() == 1)
        await mv.get_by_role('button', name='Back').click(); await pg.wait_for_timeout(900)
        check('... and the month\'s fold, which led with it, now leads with the one call', await pg.locator('.fold', has_text='People you know').locator('.fold-l').inner_text() == 'One call, two answers: Meera Krishnan.')
        mfold = pg.locator('.fold', has_text='People you know'); await mfold.locator('.fold-head').click(); await pg.wait_for_timeout(600)
        check('no notice in the fold says two people overlapped', 'overlapped' not in await mfold.inner_text())
        check('the only one is said once, on the path that already asks', await mfold.locator('.note', has_text='Arvind is the only person you know who has worked inside CEAT; you last spoke in Oct 2021.').count() == 1 and await mfold.locator('.note', has_text='Arvind').count() == 1)
        check('a reason to call about a company with a card above is left to the card', await mfold.locator('.note', has_text='Eris Lifesciences reported results').count() == 0)
        one = mfold.locator('a.note', has_text='One call, two answers')
        check('the one call in the fold says the card\'s sentence, not its evidence, and opens its full view', await one.count() == 1
              and 'one call to Meera Krishnan, CFO at Aavas Financiers, has a question for each.' in await one.inner_text() and 'Ask:' not in await one.inner_text())
        await one.click(); await pg.wait_for_timeout(1200)
        check('... the same view as the card, by its key', await pg.locator('.item-view .net-row').count() == 2 and 'onecall' in pg.url, pg.url)
        await pg.locator('.item-view').get_by_role('button', name='Back').click(); await pg.wait_for_timeout(900)
        mfold = pg.locator('.fold', has_text='People you know')
        if not await mfold.locator('.net-notes').count(): await mfold.locator('.fold-head').click(); await pg.wait_for_timeout(600)
        check('someone you know is one row: Rajat Shah\'s news carries the capex filing', await mfold.locator('li', has_text='Rajat Shah').count() == 1
              and 'capex' in await mfold.locator('li', has_text='Rajat Shah').inner_text())
        mband = await pg.locator('.end-qs').inner_text()
        check('Ask first follows a lender\'s credit-cost question: Home First, Meera Krishnan', 'credit cost' in mband
              and 'How are credit costs moving in housing finance, as Aavas Financiers sees it?' in mband, mband)
        check('a path in the fold opens the brief on that person', await mfold.locator('a.note', has_text='have worked where').count() >= 1)
        await mfold.locator('a.note', has_text='have worked where').first.click()
        # the answer comes from /api/network: warm it draws in half a second, a cold function takes longer, so wait for it
        for _ in range(100):
            if await pg.locator('.answer .path-line .stn-ask').count() >= 2: break
            await pg.wait_for_timeout(100)
        check('... with the path drawn', await pg.locator('.answer .path-line .stn-ask').count() >= 2)
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(1200)
        # Yes or No on a name FINN can't place: answered in the fold, kept on the phone, every view rebuilt from it
        await pg.get_by_role('radio', name='Month', exact=True).click(); await pg.wait_for_timeout(600)
        jf = pg.locator('.fold', has_text='People you know')
        if not await jf.locator('.net-notes').count(): await jf.locator('.fold-head').click(); await pg.wait_for_timeout(600)
        q = jf.locator('li', has_text='Is it the same person?')
        check('the month asks about the Jigar Shah at HDFC Bank, with two answers', await q.count() == 1 and await q.get_by_role('button', name='Same person').count() == 1 and await q.get_by_role('button', name='Someone else').count() == 1)
        await q.get_by_role('button', name='Same person').click()
        news = jf.locator('li', has_text='Jigar Shah, who you know, has joined HDFC Bank as General Counsel.')
        try: await news.wait_for(timeout=45000)          # a cold server rebuilds the views in a few seconds
        except Exception: pass
        check('Same person: the question becomes the news, with Change', await news.count() == 1 and await jf.locator('li', has_text='Is it the same person?').count() == 0 and await news.get_by_role('button', name='Change').count() == 1,
              (await news.count(), await jf.locator('.note-co').all_inner_texts()))
        check('... with the caution, and a way to the company', 'keep the conversation to what is public' in await news.inner_text()
              and await news.locator('a[href="#/c/HDFCBANK"]').count() == 1)
        check('... the answer stays on the phone', await pg.evaluate("localStorage.getItem('finn.identity')") == '{"jigar-shah@HDFCBANK|jigar-shah":"same"}')
        await pg.reload(); await pg.wait_for_timeout(3000)
        jf = pg.locator('.fold', has_text='People you know')
        await jf.locator('.fold-head').wait_for(timeout=30000)   # the fold, not a time: a cold link can take seconds
        if not await jf.locator('.net-notes').count(): await jf.locator('.fold-head').click(); await pg.wait_for_timeout(600)
        check('... and a reload keeps it, from the one cache slot', await jf.locator('li', has_text='Jigar Shah, who you know, has joined HDFC Bank').count() == 1
              and await pg.evaluate("JSON.parse(localStorage.getItem('finn.identity.views') || '{}').build") == json.load(open(os.path.join(ROOT, 'web/public/data/network.json')))['build'])
        await pg.goto(base + '/#/c/HDFCBANK'); await pg.wait_for_timeout(3000)
        co = pg.locator('section.net-co')
        await co.locator('.net-row').first.wait_for(timeout=30000)
        check('... and the company page lists everyone its count names, Jigar Shah too', '2 people you know have worked inside HDFC Bank.' in await co.inner_text()
              and await co.locator('.net-row', has_text='Jigar Shah').count() == 1 and await co.locator('.net-row', has_text='Rahul Menon').count() == 1, await co.inner_text())
        await pg.goto(base + '/#/'); await pg.wait_for_timeout(1500)
        jf = pg.locator('.fold', has_text='People you know')
        await jf.locator('.fold-head').wait_for(timeout=30000)
        if not await jf.locator('.net-notes').count(): await jf.locator('.fold-head').click(); await pg.wait_for_timeout(600)
        await jf.locator('li', has_text='Jigar Shah, who you know').get_by_role('button', name='Change').click(); await pg.wait_for_timeout(1500)
        check('Change: the question again, as the file has it', await jf.locator('li', has_text='Is it the same person?').count() == 1)
        await jf.locator('li', has_text='Is it the same person?').get_by_role('button', name='Someone else').click()
        other = jf.locator('li', has_text='is not the Jigar Shah you know.')
        try: await other.wait_for(timeout=45000)
        except Exception: pass
        check('Someone else: the question is gone, no news about Jigar, and the answer stays with Change', await jf.locator('li', has_text='Is it the same person?').count() == 0
              and await jf.locator('li', has_text='who you know, has joined').count() == 0 and await other.get_by_role('button', name='Change').count() == 1, await jf.locator('.note-co').all_inner_texts())
        await other.get_by_role('button', name='Change').click(); await pg.wait_for_timeout(1500)
        check('... and Change undoes it: the question again', await jf.locator('li', has_text='Is it the same person?').count() == 1)
        await pg.evaluate("localStorage.removeItem('finn.identity'); localStorage.removeItem('finn.identity.views')")
        await pg.goto(base + '/#/c/CROMPTON'); await pg.wait_for_timeout(2500)
        pat = pg.locator('section.net-co .net-pat')
        await pat.first.wait_for(timeout=30000)
        check('the company page carries the pattern and the filed reasons', await pat.count() == 1 and 'Reason filed: Transitioning to a new role within the Company.' in await pat.inner_text())
        check('one person, one question', 'Nitin Agarwal' in await pat.locator('.net-row').inner_text() and 'How long does it usually take to fill audit and compliance seats in consumer electricals?' in await pat.locator('.stn-ask').inner_text())
        check('the pattern\'s person is listed once', await pg.locator('section.net-co .net-row', has_text='Nitin Agarwal').count() == 1)
        check('its question joins the next call\'s', 'Who holds audit and compliance at Crompton now, and who do they report to?' in await pg.locator('section.ask.lead').inner_text())
        check('Crompton: no sideways scroll', await pg.evaluate('document.documentElement.scrollWidth') <= 390)
        # The annual report: read by rules, the verdict on the closed row, each line on its page
        await pg.goto(base + '/#/c/MARUTI')
        ar = pg.locator('section.fold', has=pg.locator('button.fold-head', has_text='The annual report'))
        await ar.wait_for(timeout=30000)
        check('annual report: Maruti\'s closed row carries the verdict', 'The auditor drew attention to note 38(B)' in await ar.locator('.fold-l').inner_text())
        await ar.locator('button.fold-head').click(); await pg.wait_for_timeout(500)
        body = await ar.inner_text()
        check('... open, the matter by its defined term, and what one readable call can say',
              'Note 38(B) of the consolidated accounts: Extended Producer Responsibility (EPR).' in body and 'in the one call FINN could read (May 2026)' in body, body[:300])
        await ar.get_by_role('button', name='Read the paragraph').first.click(); await pg.wait_for_timeout(300)
        check('... the paragraph a tap away, linked to its page', await ar.locator('.ar-reveal a.src[href$="#page=230"]', has_text='Consolidated report, page 230').count() == 1
              and 'inability of the Holding Company to reliably estimate' in await ar.locator('.ar-reveal').first.inner_text())
        check('... and Maruti\'s question takes the plain form: one readable call is too few to say a term is absent',
              'The auditor drew attention to note 38(B) of the consolidated accounts (Extended Producer Responsibility, EPR). What would settle it, and by when?' in await pg.locator('section.ask.lead').inner_text())
        check('Maruti: no sideways scroll with the annual report open', await pg.evaluate('document.documentElement.scrollWidth') <= 390)
        await pg.goto(base + '/#/c/ULTRACEMCO')
        await pg.locator('section.ask.lead').wait_for(timeout=15000); await pg.wait_for_timeout(800)
        ask = await pg.locator('section.ask.lead').inner_text()
        check('annual report: UltraTech\'s question says what five calls measured, and who wrote it',
              'Neither term is in the transcripts of the last five calls. What would settle it, and by when?' in ask and 'from the annual report, by FINN’s own rules' in ask, ask[-260:])
        await pg.goto(base + '/#/c/SYNGENE')
        ar = pg.locator('section.fold', has=pg.locator('button.fold-head', has_text='The annual report'))
        await ar.wait_for(timeout=30000); await ar.locator('button.fold-head').click(); await pg.wait_for_timeout(500)
        served = await pg.evaluate("fetch('/data/annual/SYNGENE.json').then(r => r.json())")
        claims = next(b for b in served['blocks'] if b['title'] == 'Contingent liabilities')
        check('annual report: Syngene\'s claims are the served file\'s, with the printed figures and the note\'s page',
              claims['text'] in await ar.inner_text() and '₹531 crore' in claims['text'] and await ar.locator('a.src[href$="#page=366"]').count() == 1, claims['text'])
        await pg.goto(base + '/#/c/KFINTECH')
        ar = pg.locator('section.fold', has=pg.locator('button.fold-head', has_text='The annual report'))
        await ar.wait_for(timeout=30000); await ar.locator('button.fold-head').click(); await pg.wait_for_timeout(400)
        check('annual report: KFin is not read, and says the filing is a cover letter', 'Not read' in await ar.locator('.fold-l').inner_text() and 'cover letter' in await ar.inner_text())
        await pg.goto(base + '/#/c/HOMEFIRST'); await pg.wait_for_timeout(2500)
        await pg.locator('.net-before a').wait_for(timeout=30000)
        await pg.locator('.net-before a').click()   # answered by /api: waits for it, since a cold start on the link can take seconds
        await pg.locator('.answer .path-line .stn-ask').first.wait_for(timeout=15000); await pg.wait_for_timeout(300)
        check('Pull: Before you meet them opens the path', await pg.locator('.answer .path-line .stn-ask').count() == 4)
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear()'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(1500)
        # Book: filter, open a company, Back keeps the scroll
        await pg.goto(base + '/#/book'); await pg.wait_for_timeout(2500)
        await pg.locator('.og-btn').first.click(); await pg.wait_for_timeout(400)
        check('book filter', 'with a promise missed' in await pg.locator('.book-filter').inner_text())
        await pg.get_by_role('button', name='Show all').click(); await pg.wait_for_timeout(300)
        card = pg.locator('.book-card').nth(5); await card.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
        # where the list stood at the tap itself: Playwright may scroll again before pressing, when something overlaps the card
        await pg.evaluate("addEventListener('pointerdown', () => { window.__y0 = scrollY }, {capture: true, once: true})")
        await card.click(); await pg.wait_for_timeout(1500); y0 = await pg.evaluate('window.__y0')
        check('company opens', await pg.locator('.co-top .co-name').count() == 1)
        await pg.locator('.p-item .og-btn').first.click(); await pg.wait_for_timeout(500)
        check('promise opens on before-and-after', await pg.locator('.p-item.open .ba-said').count() == 1)
        await pg.get_by_role('button', name='Back').click(); await pg.wait_for_timeout(1500)
        check('back keeps the scroll', abs(await pg.evaluate('scrollY') - y0) < 40, (y0, await pg.evaluate('scrollY')))
        # Look up: tiles, a name, a question, an unknown symbol
        await pg.goto(base + '/#/look'); await pg.wait_for_timeout(1500)
        check('ready to open lists companies outside the book', await pg.locator('.tiles').last.locator('li').count() >= 4)
        await pg.locator('#sym').fill('pidil'); await pg.wait_for_timeout(300)
        check('a name finds its symbol', await pg.locator('.chips .btn-outline', has_text='Pidilite').count() == 1)
        await pg.locator('#sym').fill('Did L&T deliver on revenue growth?'); await pg.wait_for_timeout(200)
        check('a question turns the button to Ask', await pg.locator('.look-row .btn-primary').inner_text() == 'Ask')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
        head = await pg.locator('.answer > .t-b1').inner_text()
        check('ask about L&T', 'Larsen & Toubro on revenue growth: missed' in head, head)
        check('answer is promised against delivered', await pg.locator('.answer .ba .st-missed').count() >= 1)
        await pg.locator('#sym').fill('Who missed a promise?'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
        check('book question', 'missed' in await pg.locator('.answer > .t-b1').inner_text())
        check('book answer is about the holdings', 'of your 18 holdings' in await pg.locator('.answer > .sub').inner_text())
        await pg.locator('#sym').fill('NOSUCHCO'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(4000)
        check('an unknown symbol is said plainly', 'NOSUCHCO' in await pg.locator('main').inner_text())
        # A kind of filing switched off leaves Today: the week's new MD & CEO goes when management changes are off
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear()'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(1500)
        await pg.get_by_role('radio', name='Week', exact=True).click(); await pg.wait_for_timeout(500)
        ceo = lambda: pg.locator('.card', has_text='MD').count()
        had = await ceo()
        await pg.get_by_role('button', name='Change alert levels').click(); await pg.wait_for_timeout(500)
        await pg.get_by_role('switch', name='Management change').click(); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        check('a filing kind switched off leaves Today', had >= 1 and await ceo() < had, (had, await ceo()))
        # All quiet: strict lines, and Today offers the nearest wider window that has something
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear(); localStorage.setItem("finn.lines", JSON.stringify({hours: 24, volX: 50, movePct: 15, interrupt: []}))'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(1500)
        check('all quiet says so', 'Nothing' in await fig())
        wide = pg.locator('.hero-wider')
        check('all quiet offers a wider window', await wide.count() == 1 and 'need' in await wide.inner_text())
        await wide.click(); await pg.wait_for_timeout(600)
        check('the wider window opens with its cards', await pg.locator('.window .on').inner_text() == 'Month' and await pg.locator('.cards .card').count() >= 1)
        # A returning investor: what arrived since the last visit is marked, and the page stays one screen wide
        await pg.goto(base + '/#/'); await pg.evaluate('localStorage.clear(); localStorage.setItem("finn.seen", "2026-10-28T09:00:00+05:30")'); await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(1500)
        check('new since the last visit is marked', await pg.locator('.card .lbl-new').count() >= 1)
        check('no sideways scroll for a returning investor', await pg.evaluate('document.documentElement.scrollWidth') <= 390)
        check('no page errors', not errs, errs)
        await b.close()
        await trust(p)
        await offline(p)

# Your data: two doors, every count and date from the served files, the live line from the server, Clear this phone,
# plain sentences when the server fails, and Look up saying reading is off before the tap
AT_LOAD = ("window.__finnAtLoad = { keys: Object.keys(localStorage).concat(Object.keys(sessionStorage)).filter(k => /^finn[.-]/.test(k)), "
           "cos: caches.keys().then(ns => Promise.all(ns.map(n => caches.open(n).then(c => c.keys())))).then(a => a.flat().filter(r => r.url.includes('/data/companies/')).length) }")
SET_ALL = ('localStorage.setItem("finn.lines", JSON.stringify({hours: 168, volX: 3, movePct: 5, interrupt: ["results"]})); '
           'localStorage.setItem("finn.identity", JSON.stringify({"jigar-shah@HDFCBANK|jigar-shah": "same"})); localStorage.setItem("finn.recent", \'["ASTRAL"]\'); '
           'localStorage.setItem("finn.c.ASTRAL", "{}"); localStorage.setItem("finn.alerts", "off")')
HTML500 = '<!doctype html><html><title>500 Internal Server Error</title><body>Traceback (most recent call last)</body></html>'
async def trust(p):
    b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 390, 'height': 844}); pg = await ctx.new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    J = lambda path: pg.evaluate(f"fetch('{path}').then(r => r.json())")
    await pg.goto(base + '/#/'); await pg.wait_for_timeout(2600)
    push = await J('/data/push.json')
    push_asof, filings, held = push['asof'], len(push['filings']), len(push['portfolio'])
    built, contacts = len(await J('/data/companies.json')), (await J('/data/network.json'))['contacts']
    live = (await pg.evaluate("fetch('/api/sources', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({op: 'status'})}).then(r => r.json())"))['live']
    day = f"{int(push_asof[8:10])} {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(push_asof[5:7]) - 1]}"
    sheet = pg.get_by_role('dialog', name='Your data')
    for tab, h in [('Today', '#/'), ('Holdings', '#/book'), ('Look up', '#/ask')]:
        await pg.goto(base + '/' + h); await pg.wait_for_timeout(1500)
        pill = pg.get_by_role('button', name=f'Sample data, as of {day}. Your data')
        check(f'{tab}: the masthead says the demo day, from push.json', await pill.count() == 1 and await pill.locator('span').first.inner_text() == f'Sample data, as of {day}', await pill.count())
        await pill.click(); await pg.wait_for_timeout(700)
        check('... and opens Your data', await sheet.is_visible())
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        check('... Escape closes it, focus back on the pill', not await sheet.is_visible() and await pg.evaluate("!!document.activeElement?.classList.contains('demo-pill')"))
    await pg.goto(base + '/#/'); await pg.wait_for_timeout(1500)
    await pg.get_by_role('button', name='Change alert levels').click(); await pg.wait_for_timeout(500)
    await pg.get_by_role('dialog', name='Your alert levels').get_by_role('button', name='Your data').click(); await pg.wait_for_timeout(900)
    check('Your alert levels has a lasting row to Your data', await sheet.is_visible() and not await pg.get_by_role('dialog', name='Your alert levels').is_visible())
    t = await sheet.inner_text()
    check('the sheet states the day and time the filings stop', f'{day} {push_asof[:4]}' in t and f"{int(push_asof[11:13]) % 12 or 12}:{push_asof[14:16]}" in t, t[:200])
    check('... the book and the network as invented, with their counts', f'The {held} holdings and the {contacts} people you know here are made up, the same for everyone who opens this link' in t)
    check('... the filings count and the companies read, from the files', f'{filings} from' in t and f'read {built} companies' in t and f'Results calls of {built} companies' in t)
    check('... and the one thing the server holds about you, the address, for about ten minutes', 'it holds your internet address for about ten minutes' in t)
    check('... every group stored on the phone', all(x in t for x in ['Your alert levels', 'What you’ve read and cleared', 'Your answers on whether two names are the same person', 'The companies you looked up', 'Whether alerts are on', 'for when there is no signal']))
    check("... the live line is the server's own answer", ('Reading a new company is off on this link: it isn’t connected to a model yet.' in t) == (live is False) and ('Reading a new company is on' in t) == (live is True), live)
    check('... no internal words', not any(w in t for w in ['ADR', 'registry', 'localStorage', 'XBRL', 'schema']))
    # Clear this phone: set some of everything, open a company so its file is in the copy, then clear
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
    await pg.goto(base + '/#/c/KPIL'); await pg.wait_for_timeout(2500)
    await pg.evaluate(SET_ALL)
    COS = "caches.open('finn-v1').then(c => c.keys()).then(ks => ks.filter(r => r.url.includes('/data/companies/')).length)"
    had = await pg.evaluate(COS)
    for _ in range(30):   # the worker keeps a file as it lands: on a slowed link that is seconds after the page shows
        if had >= 1: break
        await pg.wait_for_timeout(500); had = await pg.evaluate(COS)
    await pg.add_init_script(AT_LOAD)
    await pg.goto(base + '/#/'); await pg.wait_for_timeout(1500)
    await pg.get_by_role('button', name=f'Sample data, as of {day}. Your data').click(); await pg.wait_for_timeout(700)
    await sheet.get_by_role('button', name='Clear this phone').click(); await pg.wait_for_timeout(300)
    check('Clear this phone asks first, Keep focused', 'Clear your alert levels, reading, answers and the saved copy?' in await sheet.inner_text() and await pg.evaluate("document.activeElement?.textContent") == 'Keep')
    # Clear awaits the cache deletes, replaces the URL, then reloads: wait for the new page's load event, since a
    # navigation wait can wake on the replaceState and leave the evaluate below racing the reload
    async with pg.expect_event('load', timeout=20000):
        await sheet.get_by_role('button', name='Clear', exact=True).click()
    await pg.wait_for_timeout(2600)
    at = await pg.evaluate("window.__finnAtLoad.cos.then(cos => ({keys: window.__finnAtLoad.keys, cos}))")
    check('... after it no FINN key is left, and no company file in the copy', had >= 1 and at['keys'] == [] and at['cos'] == 0, (had, at))
    check('... Today is a first visit: default lines, the count', await pg.locator('.window .on').inner_text() == '24 hours' and (await pg.locator('.hero-fig').inner_text()).replace('\n', ' ') == '2 of your companies need a look today')
    # Look up says reading is off before the tap, when the server says so
    if live is False:
        await pg.goto(base + '/#/ask')
        try: await pg.locator('.banner', has_text='reading a new one is off').wait_for(timeout=20000)   # the line waits on /api/sources: seconds on a slowed link
        except Exception: pass
        check('Look up says reading a new one is off, up front', 'reading a new one is off' in await pg.locator('.banner').inner_text())
        await pg.locator('#sym').fill('Did ASTRAL deliver on margins?'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
        ans = pg.locator('.look-answer')
        check('... and on an unread company, before any tap, with no Read button', 'Reading a new company is off on this link' in await ans.inner_text() and await ans.get_by_role('button', name='Read ASTRAL').count() == 0, await ans.inner_text())
    # The server failing: plain sentences, never raw text
    await pg.route('**/api/network', lambda r: r.abort())
    await pg.goto(base + '/#/'); await pg.wait_for_timeout(1500)
    await pg.get_by_role('radio', name='Month', exact=True).click(); await pg.wait_for_timeout(600)
    jf = pg.locator('.fold', has_text='People you know')
    if not await jf.locator('.net-notes').count(): await jf.locator('.fold-head').click(); await pg.wait_for_timeout(600)
    await jf.locator('li', has_text='Is it the same person?').get_by_role('button', name='Same person').click(); await pg.wait_for_timeout(1500)
    check('an unreachable server keeps the answer and says so plainly', 'Saved on this phone. FINN will apply it when it can reach the server.' in await pg.locator('main').inner_text())
    await pg.unroute('**/api/network')
    await pg.evaluate('localStorage.clear()')
    html500 = lambda r: r.fulfill(status=500, content_type='text/html', body=HTML500)
    await pg.route('**/api/sources', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'symbol': 'ASTRAL', 'live': True, 'basis': 'consolidated', 'quarters': [], 'transcripts': [{'period': 'Aug 2026', 'url': 'https://example.invalid/x.pdf'}]})))
    await pg.route('**/api/call', html500); await pg.route('**/api/grade', html500)
    await pg.goto(base + '/#/c/ASTRAL')
    try: await pg.locator('main', has_text='Something went wrong on FINN’s side').first.wait_for(timeout=20000)   # after two routed calls, however long the page takes to make them
    except Exception: pass
    await pg.wait_for_timeout(300)
    m = await pg.locator('main').inner_text()
    check('an HTML 500 from the server is a plain sentence', 'Something went wrong on FINN’s side. Try again.' in m and not any(x in m for x in ['<', 'Traceback', 'HTTP 500', 'doctype']), m[-300:])
    await pg.unroute('**/api/sources'); await pg.unroute('**/api/call'); await pg.unroute('**/api/grade')
    # 320 px: the pill sits beside the wordmark with no sideways scroll
    await pg.set_viewport_size({'width': 320, 'height': 700})
    for h in ['#/', '#/book', '#/ask']:
        await pg.goto(base + '/' + h); await pg.wait_for_timeout(1200)
        check(f'320 px {h}: no sideways scroll, the pill on one line', await pg.evaluate('document.documentElement.scrollWidth') <= 320
              and await pg.evaluate("(() => { const r = document.querySelector('.demo-pill span').getBoundingClientRect(); return r.height < 40 && r.right <= 320 })()"))
    check('Your data: no page errors', not errs, errs)
    await b.close()

# A first visit, then no signal: FINN opens from the copy the worker kept (public/sw.js, main.tsx hands it the first visit)
async def offline(p):
    b = await p.chromium.launch(); ctx = await b.new_context(viewport={'width': 390, 'height': 844}); pg = await ctx.new_page()
    await pg.goto(base + '/#/'); await pg.wait_for_timeout(2600)
    await pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=10000)
    kept = []
    for _ in range(20):
        kept = await pg.evaluate("caches.open('finn-v1').then(c => c.keys()).then(ks => ks.map(r => new URL(r.url).pathname))")
        if '/' in kept and '/data/push.json' in kept and any(k.startswith('/assets/index-') for k in kept): break
        await pg.wait_for_timeout(300)
    check('a first visit is kept for no signal: the page, its code and the snapshot', '/' in kept and '/data/push.json' in kept and any(k.startswith('/assets/index-') for k in kept), kept)
    check('... and nothing from /api', not any(k.startswith('/api/') for k in kept), kept)
    # A data file opened in the tab is a navigation too: it must never replace the saved page
    await pg.goto(base + '/data/network.json'); await pg.wait_for_timeout(600)
    page = await pg.evaluate("caches.open('finn-v1').then(c => c.match('/', {ignoreVary: true})).then(r => r ? r.headers.get('content-type') : '')")
    check('... a JSON file opened in the tab is not saved as the page', (page or '').startswith('text/html'), page)
    await pg.goto(base + '/#/'); await pg.wait_for_timeout(1500)
    await ctx.set_offline(True)
    await pg.reload(wait_until='domcontentloaded'); await pg.wait_for_timeout(2600)
    fig = await pg.locator('.hero-fig').inner_text() if await pg.locator('.hero-fig').count() else ''
    check('with no signal after one visit, Today opens', fig.replace('\n', ' ') == '2 of your companies need a look today', fig)
    await b.close()
asyncio.run(main())
sys.exit(1 if fails else 0)
