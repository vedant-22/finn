// What the screen says, checked. Run: npm test (Node 22.6+ reads lib.ts directly)
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cr, deadline, pct, rupees, tidyEvidence, when } from '../src/lib.ts'

test('percentages: sign, a true minus, never −0.0%', () => {
  assert.equal(pct(12.4), '+12%')
  assert.equal(pct(-5.25), '−5.3%')
  assert.equal(pct(-0.04), '0%')
  assert.equal(pct(0.04), '0%')
  assert.equal(pct(null), '–')
})

test('crore: Indian grouping, true minus', () => {
  assert.equal(cr(140300), '1,40,300')
  assert.equal(cr(-151), '−151')
})

test('rupees: model text in house style, numbers grouped', () => {
  assert.equal(rupees('INR1,450 crores of capex'), '₹1,450 crore of capex')
  assert.equal(rupees('Rs. 5600-5800 Cr disbursements'), '₹5,600–5,800 crore disbursements')
  assert.equal(rupees('Issued debentures for 300 crores.'), 'Issued debentures for ₹300 crore.')
  assert.equal(rupees('buyback of 150 crore rupees'), 'buyback of ₹150 crore')
  assert.equal(rupees('orders worth 10000 to 15000 crore'), 'orders worth ₹10,000–15,000 crore')
  assert.equal(rupees('capex of 422.76 Crores'), 'capex of ₹422.76 crore')
  assert.equal(rupees('allot 2 crore shares'), 'allot 2 crore shares')
  assert.equal(rupees('Order book reached ₹7.79 trillion'), 'Order book reached ₹7.79 lakh crore')
  assert.equal(rupees('capex of INR 6.1 billion'), 'capex of ₹610 crore')
  assert.equal(rupees('INR 12.5 billion'), '₹1,250 crore')
  assert.equal(rupees('in Sep 2026 to 53,356 crore'), 'in Sep 2026 to ₹53,356 crore')
  assert.equal(rupees('₹ 150 crore and ₹1,450 crore'), '₹ 150 crore and ₹1,450 crore')
})

test("'Yesterday' is the calendar day before, not any time in 48 hours", () => {
  const asof = '2026-10-28T16:30'
  assert.equal(when('2026-10-28T15:40', asof), '3:40 pm')
  assert.equal(when('2026-10-27T20:38', asof), 'Yesterday 8:38 pm')
  assert.equal(when('2026-10-26T20:32', asof), '26 Oct')
})

const p = (by_when, period, status = 'pending', target = 'Grow volumes 15%') => ({ target, by_when, period, status })
test('deadlines name the fiscal year from the call month', () => {
  assert.equal(deadline(p('this year', 'Nov 2025', 'kept')), 'by FY26')
  assert.equal(deadline(p('next year', 'Jan 2026')), 'by FY27')
  assert.equal(deadline(p('coming year', 'Jan 2026')), 'by FY27')
  assert.equal(deadline(p('upcoming year', 'May 2026')), 'by upcoming year')
  assert.equal(deadline({ target: 'Launch in coming year', by_when: 'coming year', period: 'Jan 2026' }), '(FY27)')
  assert.equal(deadline(p('end of this financial year', 'Oct 2025', 'kept')), 'by end of FY26')
  assert.equal(deadline(p('end of this calendar year', 'May 2026')), 'by end of 2026')
})

test('deadlines keep the words when the year is ambiguous or the grade has not caught up', () => {
  // April to June calls: 'this year' may mean the year just closed
  assert.equal(deadline(p('this year', 'May 2025')), 'by this year')
  // FY26 is over but the promise is still graded not due: don't print a contradiction
  assert.equal(deadline(p('this financial year', 'Nov 2025', 'pending')), 'by this financial year')
})

test("deadlines drop a 'by ...' the promise already states", () => {
  assert.equal(deadline(p('FY27', 'Nov 2025', 'pending', '15% margin by FY27')), '')
  assert.equal(deadline(p('unspecified', 'Nov 2025')), '')
})

test("the 'Reported' line reads like numbers, not a table dump", () => {
  assert.equal(tidyEvidence('Mar 2026 Revenue 3739.0, Mar 2026 OPM % 25.0'), 'Mar 2026 Revenue 3,739, Mar 2026 OPM 25%')
  assert.equal(tidyEvidence('Jun 2026 OPM 26 percent'), 'Jun 2026 OPM 26%')
  assert.equal(tidyEvidence('OPM % for Mar 2026 was 41.0%'), 'OPM for Mar 2026 was 41%')
  assert.equal(tidyEvidence('Revenue YoY % was 30.3% in Jun 2026'), 'Revenue YoY was 30.3% in Jun 2026')
  assert.equal(tidyEvidence('Revenue FY25 Rs 38860.0 crore'), 'Revenue FY25 ₹38,860 crore')
  assert.equal(tidyEvidence('FY26 PBT 15119.0, PAT 11509.0, implied tax rate 23.9%'), 'FY26 PBT 15,119, PAT 11,509, implied tax rate 23.9%')
})
