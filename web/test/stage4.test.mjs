// The brief and Ask, checked against the real snapshot. Run: npm test
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { DEFAULT_LINES, wordScore } from '../src/lib.ts'
import { buildBrief, act, remaining, notesKey, NO_DONE, newsQuestion, raisedNotice, foldNotices, netKey, questionKind } from '../src/queue.ts'
import { aliases, cameDue, parse, matching, tally, verdictHead, pace, fyOf, runningGuide, yearToDate } from '../src/question.ts'

const push = JSON.parse(fs.readFileSync(new URL('../public/data/push.json', import.meta.url)))
const names = JSON.parse(fs.readFileSync(new URL('../public/data/companies.json', import.meta.url)))
const known = Object.entries(names).map(([s, n]) => ({ symbol: s, names: aliases(s, n, push.portfolio.find(p => p.symbol === s)?.short) }))
const co = s => JSON.parse(fs.readFileSync(new URL(`../public/data/companies/${s}.json`, import.meta.url)))
const network = JSON.parse(fs.readFileSync(new URL('../public/data/network.json', import.meta.url)))

// The network raises at most one card a window: a join of filings Push reads one by one, with one person to ask
test('the network raises one card a window, last, outside the count of what needs you', () => {
  const want = { 24: 'net|onecall|HDFCBANK,HOMEFIRST|2026-10-27|meera-krishnan', 72: 'net|onecall|HDFCBANK,HOMEFIRST|2026-10-27|meera-krishnan',
    168: 'net|onecall|HDFCBANK,HOMEFIRST|2026-10-27|meera-krishnan', 720: 'net|seats|CROMPTON|2026-10-16|nitin-agarwal' }
  for (const [h, key] of Object.entries(want)) {
    const lines = { ...DEFAULT_LINES, hours: +h }
    const plain = buildBrief(push, lines), b = buildBrief(push, lines, network.notices)
    assert.equal(b.net?.key, key, `${h} hours`)
    assert.equal(b.net.kind, 'network')
    // what needs you, and so what may notify, is the market's alone
    assert.deepEqual(b.items.map(i => i.key), plain.items.map(i => i.key))
    assert.ok(!b.items.some(i => i.kind === 'network') && !b.spill.some(i => i.kind === 'network'))
  }
  assert.equal(buildBrief(push, DEFAULT_LINES).net, null, 'before the network loads, no card')
})

test('a notice outside the window raises nothing, and a pattern stays with a card its company already has', () => {
  const old = network.notices.map(n => ({ ...n, at: n.at && '2026-09-01' }))
  assert.equal(buildBrief(push, { ...DEFAULT_LINES, hours: 720 }, old).net, null)
  assert.equal(raisedNotice(network.notices, push.asof, 720, ['CROMPTON'])?.kind, 'onecall')
  assert.equal(raisedNotice(network.notices.filter(n => !n.card), push.asof, 720, []), null, 'only a notice with a card is raised')
})

test("the network card's key is what it is, not its words, so its deep link survives a reworded rebuild", () => {
  const n = raisedNotice(network.notices, push.asof, 24, [])
  const reworded = { ...n, line: 'x', why: 'y', card: { ...n.card, line: 'z', symbols: [...n.card.symbols].reverse() } }
  assert.equal(netKey(reworded), netKey(n))
})

test('a raised notice leaves the fold, so nothing is said twice', () => {
  for (const h of [24, 720]) {
    const b = buildBrief(push, { ...DEFAULT_LINES, hours: h }, network.notices), skip = b.items.map(i => i.symbol)
    const fold = foldNotices(network.notices, push.asof, h, skip, b.net.notice)
    assert.ok(!fold.includes(b.net.notice), `${h} hours`)
    assert.ok(foldNotices(network.notices, push.asof, h, skip).includes(b.net.notice), 'without the card it is in the fold')
  }
})

test('a notice with a card left in the fold opens the same full view, by its key', () => {
  const b = buildBrief(push, { ...DEFAULT_LINES, hours: 720 }, network.notices), skip = b.items.map(i => i.symbol)
  const carded = foldNotices(network.notices, push.asof, 720, skip, b.net.notice).filter(n => n.card)
  assert.deepEqual(carded.map(n => n.kind), ['onecall'], 'the month raises the pattern; the one call stays in the fold')
  assert.deepEqual(b.netFold.map(i => i.key), ['net|onecall|HDFCBANK,HOMEFIRST|2026-10-27|meera-krishnan'])
  assert.ok(carded.every(n => b.netFold.some(i => i.notice === n)), 'every carded row in the fold has a view to open')
  assert.deepEqual(buildBrief(push, DEFAULT_LINES, network.notices).netFold, [], 'a day raises the one call itself')
})

test('the 24-hour brief holds the two unusual days', () => {
  const b = buildBrief(push, DEFAULT_LINES)
  assert.deepEqual(b.items.map(i => i.symbol), ['SYNGENE', 'LT'])
  assert.ok(b.items.every(i => i.kind === 'move'))
})

test('a results-day move carries the management change filed with its results, even from outside the window', () => {
  const b = buildBrief(push, DEFAULT_LINES)
  const syn = b.items.find(i => i.symbol === 'SYNGENE')
  assert.equal(syn.kind, 'move')
  assert.ok(syn.with?.lead.people?.some(p => /Chief Financial Officer|CFO/.test(p.role)), 'the CFO change rides with the move, before a lower role')
})

test('a results-day move joins its results item, and a busy window stays short', () => {
  const b = buildBrief(push, { ...DEFAULT_LINES, hours: 72 })
  assert.ok(b.items.length <= 6)
  const syn = b.items.find(i => i.symbol === 'SYNGENE' && i.kind === 'results')
  assert.ok(syn?.move, 'Syngene results carry the 12% move')
  assert.equal(b.items.filter(i => i.kind === 'move' && i.symbol === 'SYNGENE').length, 0)
  assert.ok(b.items.filter(i => i.story?.category === 'results').length <= 3)
})

test('clearing and keeping take items off the brief; the notes page counts once', () => {
  const b = buildBrief(push, DEFAULT_LINES)
  let d = NO_DONE
  assert.equal(remaining(b, d).total, b.items.length + 1)
  d = act(d, b.items[0].key, 'clear'); d = act(d, b.items[1].key, 'keep')
  assert.equal(remaining(b, d).items.length, 0)
  d = { ...d, notes: [notesKey(b.notes, b.spill)] }
  assert.equal(remaining(b, d).total, 0)
  d = act(d, b.items[1].key, 'undo')
  assert.equal(remaining(b, d).total, 1)
})

test('Ask finds the company, the topic and the intent', () => {
  const p = parse('Did L&T deliver on revenue growth?', known)
  assert.equal(p.symbol, 'LT'); assert.equal(p.topic.key, 'revenue'); assert.equal(p.intent, 'delivered')
  assert.equal(parse('hdfc bank margins', known).symbol, 'HDFCBANK')
  assert.equal(parse("What has Syngene promised for FY27?", known).fy, 'FY27')
  assert.equal(parse('Who missed a promise?', known).book, true)
  assert.equal(parse('ASTRAL', known).ticker, 'ASTRAL')
  assert.equal(parse('read astral', known).ticker, 'ASTRAL')
  assert.equal(parse('Did Larsen keep its word on margins', known).symbol, 'LT')
  // a name said short, a year that is not a symbol, and asking words that are not the subject
  assert.equal(parse('What has KFin promised for FY27?', known).symbol, 'KFINTECH')
  assert.equal(parse('Did Home First deliver on margins?', known).symbol, 'HOMEFIRST')
  assert.equal(parse('Did Larsen and Toubro deliver?', known).rest, undefined)
  assert.equal(parse('Who has missed their FY26 guidance?', known).ticker, undefined)
  assert.equal(parse('Who has missed their FY26 guidance?', known).book, true)
  assert.equal(parse('What is still due at CEAT?', known).rest, undefined)
  assert.equal(parse('Did HDFC Life deliver on margins?', known).symbol, undefined)
  // the suggestions' wording reads the same as 'deliver on'
  for (const q of ['Did L&T meet its revenue growth targets?', 'Did L&T deliver on revenue growth?']) {
    const x = parse(q, known)
    assert.deepEqual([x.symbol, x.topic?.key, x.intent, x.rest, x.ticker], ['LT', 'revenue', 'delivered', undefined, undefined], q)
  }
  assert.equal(parse('Did Titan meet its margin targets?', known).topic.key, 'margin')
  assert.equal(parse('Did Titan meet its margin targets?', known).intent, 'delivered')
})

test('Ask answers from the ledger: L&T missed its FY26 revenue growth', () => {
  const xs = matching(co('LT').ledger, parse('Did L&T deliver on revenue growth?', known))
  assert.ok(xs.length >= 1)
  assert.equal(xs[0].status, 'missed')
  assert.match(tally(xs), /^1 missed/)
  const st = (...a) => a.map(status => ({ status }))
  assert.equal(verdictHead(st('missed')), 'missed')
  assert.equal(verdictHead(st('kept', 'missed', 'pending')), 'kept 1 of 2')
  assert.equal(verdictHead(st('pending')), 'not yet due')
  assert.ok(xs.every(x => x.metric !== 'working_capital'), 'a working-capital promise is not a revenue answer')
})

test('this year’s revenue guide reads against the quarter: ahead, on track or behind so far', () => {
  assert.equal(fyOf('Sep 2026'), 'FY27'); assert.equal(fyOf('Mar 2026'), 'FY26')
  const lt = co('LT'), q = lt.quarters[lt.quarters.length - 1]
  const r = runningGuide(lt.ledger, q.q)
  assert.equal(r.fy, 'FY27'); assert.match(r.g.target, /revenue growth 10% to 12%/)
  assert.equal(pace(r.g, q.rev_yoy), 'ahead')
  assert.equal(pace(r.g, 11), 'on track'); assert.equal(pace(r.g, 8), 'behind')
  // order inflows are not revenue
  assert.equal(pace(lt.ledger.find(p => /order inflows/.test(p.target)), 20), null)
})

test('one settled promise is named by its own word in the headline', () => {
  assert.equal(verdictHead([{ status: 'partly' }]), 'partly done')
  assert.equal(verdictHead([{ status: 'quiet' }]), 'no update')
  assert.equal(verdictHead([{ status: 'missed' }]), 'missed')
  assert.equal(verdictHead([{ status: 'kept' }, { status: 'missed' }]), 'kept 1 of 2')
})

test('an answer counts what came due as the company page does', () => {
  // Syngene: two kept, and two past their date with nothing said. 'Kept all 2' beside '2 of 4' was the fault.
  const syn = co('SYNGENE'), xs = matching(syn.ledger, parse('Did Syngene keep its word?', known))
  assert.equal(xs.length, wordScore(syn).graded)
  assert.equal(verdictHead(xs), 'kept 2 of 4')
  assert.match(tally(xs), /2 can’t tell yet, 2 kept/)
  for (const s of Object.keys(names)) {
    const c = co(s); if (!c) continue
    const d = matching(c.ledger, { intent: 'delivered' }).filter(cameDue)
    assert.equal(d.length, wordScore(c).graded, `${s}: Look up and the company page count the same promises as come due`)
  }
  assert.equal(verdictHead([{ status: 'unclear', checked: 'past_due' }]), 'can’t tell yet')
  assert.equal(verdictHead([{ status: 'missed' }, { status: 'partly' }, { status: 'partly' }]), '3 missed or partly done')
  assert.equal(verdictHead([{ status: 'missed' }, { status: 'quiet' }, { status: 'quiet' }]), 'kept none of 3')
  assert.equal(verdictHead([{ status: 'kept' }, { status: 'kept' }]), 'kept both')
  // 'What has it missed?' is never answered by a promise that is only past its date
  assert.ok(matching(syn.ledger, { intent: 'missed' }).every(x => x.status === 'missed' || x.status === 'partly'))
  // 'FY26-27' is FY27: Havells's FY27 capex is not an FY26 promise
  const hav = co('HAVELLS')
  assert.ok(matching(hav.ledger, { intent: null, fy: 'FY26' }).every(x => !/FY ?26-27/i.test(x.by_when)))
  assert.ok(matching(hav.ledger, { intent: null, fy: 'FY27' }).some(x => /FY ?26-27/i.test(x.by_when)))
  // a verb is not a symbol
  assert.equal(parse('Did Q2 go well?', known).ticker, undefined)
})

test('the next call asks about the news: a CFO leaving, then a margin that fell', () => {
  const b = buildBrief(push, DEFAULT_LINES)
  const q = s => newsQuestion(b.items.find(i => i.symbol === s), push)
  assert.match(q('SYNGENE'), /^Why did the CFO, Deepak Jain, leave/)
  assert.match(q('LT'), /^Revenue grew 15\.8% on a year ago and operating profit \(EBITDA\) only 0\.6%: the margin fell 1\.3 percentage points\./)
})

test('a year’s guide reads against the year so far: L&T’s H1 revenue is on track for 10 to 12%', () => {
  const lt = co('LT'), y = yearToDate(lt.quarters)
  assert.equal(y.label, 'H1'); assert.equal(y.fy, 'FY27')
  assert.ok(Math.abs(y.growth - 11.4) < 0.1, String(y.growth))
  assert.equal(pace(runningGuide(lt.ledger, lt.quarters.at(-1).q).g, y.growth), 'on track')
})

test('a question no topic covers is kept as what it is about, so the answer can say it is not in the filings', () => {
  const k = [{ symbol: 'TITAN', names: aliases('TITAN', 'Titan Company Ltd', 'Titan') }]
  const d = parse('What did Titan say about lab-grown diamonds?', k)
  assert.equal(d.symbol, 'TITAN'); assert.equal(d.topic, undefined); assert.equal(d.rest, 'lab grown diamonds')
  // keeping its word is a record question, not a topic FINN can't find
  assert.equal(parse('Did Titan keep its word?', k).rest, undefined)
  assert.equal(parse('Is Titan growing?', k).topic.key, 'revenue')
})

test('the person fits the kind of question: a departure, or the numbers, decided once per item', () => {
  const b = buildBrief(push, DEFAULT_LINES)
  assert.deepEqual(b.items.map(i => [i.symbol, questionKind(i)]), [['SYNGENE', 'leave'], ['LT', 'numbers']])
  // a move no filing explains raises neither kind, so it keeps who is closest to the company
  const days = buildBrief(push, { ...DEFAULT_LINES, hours: 72 })
  assert.equal(questionKind(days.items.find(i => i.symbol === 'CYIENT')), null)
  // a CEO change filed with an arrival is a departure, and the arrival's path still speaks first on the card
  assert.equal(questionKind(days.items.find(i => i.symbol === 'HDFCBANK')), 'leave')
})
