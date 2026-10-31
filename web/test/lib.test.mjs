// What the screen says, checked. Run: npm test (Node 22.6+ reads lib.ts directly)
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cr, crBig as crBigNb, deadline, pct, rupees as rupeesWj, tidyEvidence as tidyWj, when, numbersOnly, plainBio } from '../src/lib.ts'

// The word joiner that keeps a range on one line is invisible; compare without it
// and the no-break space that keeps an amount with its unit
const plain = s => s.replace(/\u2060/g, '').replace(/\u00a0/g, ' ')
const rupees = s => plain(rupeesWj(s))
const tidyEvidence = s => plain(tidyWj(s))
const crBig = v => plain(crBigNb(v))

test('ranges never break at the dash', () => {
  assert.equal(rupeesWj('EBITDA margin 22-23%'), 'EBITDA margin 22–\u206023%')
  assert.equal(rupeesWj('Rs 5600-5800 Cr'), '₹5,600–\u20605,800\u00a0crore')
  assert.equal(rupeesWj('FY 2022-23'), 'FY 2022-23')
})

test('percentages read as figures, ranges with an en dash', () => {
  assert.equal(rupees('12 to 15 percent growth by this year'), '12–15% growth by this year')
  assert.equal(rupees('Operating expenses to assets 2.6%-2.7% by FY26'), 'Operating expenses to assets 2.6–2.7% by FY26')
  assert.equal(rupees('23% to 24% top line growth'), '23–24% top line growth')
  assert.equal(rupees('30-ish percent seaways margin'), '30-ish percent seaways margin')
  assert.equal(rupees('ROE of 16 per cent'), 'ROE of 16%')
  assert.equal(rupees('fell from 18% to 12%'), 'fell from 18% to 12%')
  assert.equal(rupees('rose from 12% to 18%'), 'rose from 12% to 18%')
})

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
  assert.equal(rupees('Revenue decline 3-5%, EBITDA margin 22-23%'), 'Revenue decline 3–5%, EBITDA margin 22–23%')
  assert.equal(rupees('for FY 2022-23 and 2026-10-28'), 'for FY 2022-23 and 2026-10-28')
  assert.equal(rupees('240-245 million tons, 3-4x, 18-24 months'), '240–245 million tons, 3–4x, 18–24 months')
  assert.equal(rupees('revenue of ₹285,874 crore'), 'revenue of ₹2,85,874 crore')
  assert.equal(rupees('₹2,85,874 and ₹1,450 crore'), '₹2,85,874 and ₹1,450 crore')
  assert.equal(rupees('Rs 1,234,567 crore'), '₹12,34,567 crore')
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
  assert.equal(deadline(p('full year FY26', 'Jan 2026')), 'by FY26')
  assert.equal(deadline(p('end of fiscal 2030', 'Jan 2026')), 'by end of FY30')
  assert.equal(deadline(p('January March 28', 'Jan 2026')), 'by Q4 FY28')
  assert.equal(deadline(p('coming year', 'Jan 2026')), 'by FY27')
  assert.equal(deadline(p('next 9 months', 'Aug 2026')), 'within 9 months')
  assert.equal(deadline(p('2 to 3 months', 'Dec 2025')), 'within 2 to 3 months')
  assert.equal(deadline(p('annual basis', 'Oct 2025')), '')
  assert.equal(deadline(p('next two, three quarters', 'Oct 2025')), 'within two to three quarters')
  assert.equal(deadline(p('next couple of years', 'Oct 2025')), 'within a couple of years')
  assert.equal(deadline(p('next 18 months - 24 months', 'Oct 2025')), 'within 18 months to 24 months')
  assert.equal(deadline(p('upcoming year', 'May 2026')), 'by upcoming year')
  assert.equal(deadline({ target: 'Launch in coming year', by_when: 'coming year', period: 'Jan 2026' }), '(FY27)')
  assert.equal(deadline(p('end of this financial year', 'Oct 2025', 'kept')), 'by end of FY26')
  assert.equal(deadline(p('end of this calendar year', 'May 2026')), 'by end of 2026')
})

test('deadlines keep the words when the year is ambiguous or the grade has not caught up', () => {
  // April to June calls are year-end calls: 'this year' is the year just starting
  assert.equal(deadline(p('this year', 'May 2025', 'quiet')), 'by FY26')
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

test('big sums in lakh crore', () => {
  assert.equal(crBig(504279), '5.04 lakh cr')
  assert.equal(crBig(140300), '1.4 lakh cr')
  assert.equal(crBig(200000), '2 lakh cr')
  assert.equal(crBig(78750), '78,750 cr')
})

test('an amount keeps its unit on the same line', () => {
  assert.equal(crBigNb(523000), '5.23 lakh cr')
  assert.equal(rupeesWj('₹7.79 lakh crore'), '₹7.79 lakh crore')
  assert.equal(rupeesWj('2 crore shares'), '2 crore shares')
  assert.equal(rupeesWj('provision in Q1 FY27?'), 'provision in Q1\u00a0FY27?')
})

test('the before-and-after marks only what is in the quote', async () => {
  const { markQuote } = await import('../src/lib.ts')
  const marked = (q, t, w) => { const r = markQuote(q, t, w); return [r.parts.filter(p => p.k).map(p => `${p.k}:${p.t}`), r.fig, r.date] }
  assert.deepEqual(marked('We expect our group order inflows and group revenues to grow at 10% and 15% respectively for FY26.', 'Group revenue growth 15%', 'FY26'),
    [['fig:15%', 'date:FY26'], true, true])
  assert.deepEqual(marked('Our Net Working Capital-to-Revenue guidance for March ‘26 remains at 12%.', 'NWC-to-Revenue 12%', 'March 2026'),
    [['date:March ‘26', 'fig:12%'], true, true])
  assert.deepEqual(marked('we continue to target the 8.3% to 8.5% range for the full year FY26', 'P&M margin 8.3% to 8.5%', 'FY26'),
    [['fig:8.3%', 'fig:8.5%', 'date:FY26'], true, true])
  assert.deepEqual(marked('Disbursements of Rs 5,600 crores to 5,800 crores in 2025-26', '₹5,600–5,800 crore disbursements', 'FY26'),
    [['fig:Rs 5,600 crores', 'fig:5,800 crores', 'date:2025-26'], true, true])
  // a year inside the target is a date, not a figure; nothing found means no claim
  assert.deepEqual(marked('We will grow faster than the industry.', 'Revenue growth 20% by FY27', 'FY27'), [[], false, false])
})

test("the 'Reported' line gives only the figures the verdict doesn't", () => {
  const v = 'FY26 group revenue grew 11.8% to ₹2,85,874 crore against the 15% growth target.'
  assert.equal(numbersOnly('FY25 revenue ₹2,55,734 crore, FY26 revenue ₹2,85,874 crore (11.8% growth).', v), 'FY25 revenue ₹2,55,734 crore.')
  assert.equal(numbersOnly('FY26 revenue ₹2,85,874 crore (11.8% growth).', v), '')
  assert.equal(numbersOnly('FY26 revenue ₹2,90,000 crore (11.8% growth).', v), 'FY26 revenue ₹2,90,000 crore.')
  assert.equal(numbersOnly('Q1 OPM 7%, Q2 OPM 9%', 'Margin reached 9% in Q2.'), 'Q1 OPM 7%.')
})

test('a joiner with a listed career gets one plain sentence, not the press release', () => {
  assert.equal(plainBio('Chartered Accountant with over 25 years of experience in finance, treasury, regulatory compliance, capital planning and financial controls.'), 'Chartered Accountant with over 25 years of experience.')
  assert.equal(plainBio('A seasoned financial services leader with over three decades of experience across banking, capital markets, wealth management and insurance.'), 'A financial services leader with over three decades of experience.')
  assert.equal(plainBio('Mr. K. C. Jhanwar has been the Managing Director of UltraTech Cement Limited since 1st January, 2020. A Chartered Accountant by profession, he joined the Aditya Birla Group in 1981.'), 'Mr. K. C. Jhanwar has been the Managing Director of UltraTech Cement Limited since 1st January, 2020.')
  assert.equal(plainBio('Founder & CEO of Samara Capital Group, a leading alternative asset manager with USD 2 billion+ invested since 2007 across various industry segments.'), 'Founder & CEO of Samara Capital Group, an alternative asset manager with USD 2 billion+ invested since 2007 across various industry segments.')
})
