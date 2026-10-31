// The brief and Ask, checked against the real snapshot. Run: npm test
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { DEFAULT_LINES } from '../src/lib.ts'
import { buildBrief, act, remaining, notesKey, NO_DONE } from '../src/queue.ts'
import { aliases, parse, matching, tally, verdictHead, pace, fyOf, runningGuide } from '../src/question.ts'

const push = JSON.parse(fs.readFileSync(new URL('../public/data/push.json', import.meta.url)))
const names = JSON.parse(fs.readFileSync(new URL('../public/data/companies.json', import.meta.url)))
const known = Object.entries(names).map(([s, n]) => ({ symbol: s, names: aliases(s, n, push.portfolio.find(p => p.symbol === s)?.short) }))
const co = s => JSON.parse(fs.readFileSync(new URL(`../public/data/companies/${s}.json`, import.meta.url)))

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
})

test('Ask answers from the ledger: L&T missed its FY26 revenue growth', () => {
  const xs = matching(co('LT').ledger, parse('Did L&T deliver on revenue growth?', known))
  assert.ok(xs.length >= 1)
  assert.equal(xs[0].status, 'missed')
  assert.match(tally(xs), /^1 missed/)
  const st = (...a) => a.map(status => ({ status }))
  assert.equal(verdictHead(st('missed')), 'missed')
  assert.equal(verdictHead(st('kept', 'missed', 'pending')), 'kept 1 of 2')
  assert.equal(verdictHead(st('pending')), 'not due yet')
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
