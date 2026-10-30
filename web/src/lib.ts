// Data, settings and the triage logic that decides what reaches the investor.

export type Tier = 'act' | 'note' | 'fold'
export type Status = 'kept' | 'partly' | 'missed' | 'quiet' | 'pending' | 'unclear'

export interface Filing {
  id: string; symbol: string; at: string; desc: string; subject: string; url: string
  category: string; tier: Tier; line: string; how?: string
  amount_cr?: number; pct_rev?: number; downgraded?: string
  results?: Results; people?: Person[]
}
export interface Results {
  quarter: string; basis: string; bank: boolean
  lines: { key: string; label: string; value: number | null; prev: number | null; yago: number | null; qoq: number | null; yoy: number | null }[]
  ebitda_margin: number | null; prev_margin: number | null; yago_margin: number | null
  source: { xbrl: string; pdf: string; filed: string }; compare: { prev: string; yago: string }
}
export interface Person {
  name: string; role: string; action: string; seniority: string; effective: string; reason: string
  background: string; previous: string[]; education: string; verified: boolean
}
export interface Holding { short?: string; symbol: string; sector: string; size: string; name: string; mcap: number; ttm_rev: number }
export interface Bar { d: string; close: number; chg: number; vol: number }
export interface Push { asof: string; portfolio: Holding[]; filings: Filing[]; eod: Record<string, Bar[]>; usage: any }

export interface Promise_ {
  id: number; quote: string; page: number; speaker: string; topic: string; metric: string; target: string
  by_when: string; hard: boolean; period: string; url: string
  status: Status; verdict: string; evidence_kind: string; evidence: string; evidence_page?: number; evidence_url?: string
  restated?: { period: string; page: number; url: string }[]
}
export interface Company {
  symbol: string; name: string; basis: string; source: string; asof: string
  snapshot: any; quarters: any[]
  calls: { period: string; url: string; pages: number; found: number; dropped: number; soft: number; error?: string }[]
  ledger: Promise_[]; open: Promise_[]; score: Record<Status, number>
  read: string; questions: string[]; bull: string[]; bear: string[]; usage: any; built_in?: number
  live?: boolean
}

// ---------- formatting ----------
const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
export const cr = (v: number | null | undefined) => (v == null ? '–' : minus(inr.format(Math.round(v))))
// Big sums the way they're said: ₹5,04,279 cr is '5.04 lakh cr'
// No-break spaces: 'Worth ₹5.23 lakh cr' never leaves 'cr' alone on the next line
export const crBig = (v: number) => v >= 1e5 ? `${(v / 1e5).toFixed(2).replace(/\.?0+$/, '')}\u00a0lakh\u00a0cr` : `${cr(v)}\u00a0cr`
export const minus = (s: string | number) => String(s).replace(/^-/, '−')
export const pct = (v: number | null | undefined, sign = true) => {
  if (v == null) return '–'
  const a = Math.abs(v).toFixed(Math.abs(v) < 10 ? 1 : 0)
  return +a === 0 ? '0%' : `${sign && v > 0 ? '+' : v < 0 ? '−' : ''}${a}%`  // never '−0.0%'
}
export const tone = (v: number | null | undefined) => (v == null || Math.abs(v) < 0.05 ? '' : v > 0 ? 'up' : 'down')
export const shortName = (n: string) =>
  n.replace(/\s*\(India\)/i, '').replace(/\s+(Ltd|Limited)\.?$/i, '').replace(/\s+(India|Industries|International|Company|Finance Company India|Corporation of India|Express)$/i, '').replace(/\s+(India|Industries)$/i, '')

export function when(iso: string, asof: string) {
  const d = new Date(iso), now = new Date(asof)
  const hrs = (now.getTime() - d.getTime()) / 36e5
  const time = d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()
  // Calendar days, not hours: 8:30 pm two days back is not 'Yesterday'
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((day(now) - day(d)) / 864e5)
  if (days === 0 && hrs >= 0) return time
  if (days === 1) return `Yesterday ${time}`
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

// ---------- settings: the investor decides what "unusual" means ----------
export interface Lines {
  hours: number
  volX: number        // volume vs its 20-session average
  movePct: number     // absolute daily move
  interrupt: string[] // filing categories allowed to interrupt
}
export const DEFAULT_LINES: Lines = {
  hours: 24, volX: 2, movePct: 4,
  interrupt: ['results', 'management_change', 'M&A', 'litigation', 'fund_raise', 'credit_rating'],
}
export const CATEGORY_LABEL: Record<string, string> = {
  results: 'Results', management_change: 'Management change', 'M&A': 'Deals', litigation: 'Legal and regulatory',
  fund_raise: 'Fund raising and buybacks', credit_rating: 'Credit rating', capex: 'Capacity and capex',
  press_release: 'Orders and updates', dividend: 'Dividends', bonus_split: 'Bonus and splits', earnings_call: 'Calls and decks',
  insider_trading: 'Insider and promoter', investor_meetings: 'Investor meetings', agm_egm: 'Shareholder meetings',
  pledging: 'Pledges', postal_ballot: 'Postal ballots', unclassified: 'Paperwork',
}
export function loadLines(): Lines {
  try { return { ...DEFAULT_LINES, ...JSON.parse(localStorage.getItem('finn.lines') || '{}') } } catch { return DEFAULT_LINES }
}
export const saveLines = (l: Lines) => localStorage.setItem('finn.lines', JSON.stringify(l))

// ---------- triage ----------
export interface Story { key: string; symbol: string; category: string; tier: Tier; at: string; lead: Filing; filings: Filing[] }
export interface Move { symbol: string; d: string; close: number; chg: number; volX: number; avgVol: number; series: Bar[]; why: string[]; explainedBy?: Filing }

const ORDER = ['results', 'management_change', 'M&A', 'litigation', 'fund_raise', 'credit_rating', 'capex', 'insider_trading', 'pledging']

// Several filings about one event (results + press release + deck + newspaper ad) become one story.
export function stories(filings: Filing[]): Story[] {
  const map = new Map<string, Story>()
  for (const f of filings) {
    const day = f.at.slice(0, 10)
    const key = `${f.symbol}|${f.category}|${f.category === 'results' ? '' : day}`
    const s = map.get(key)
    if (!s) { map.set(key, { key, symbol: f.symbol, category: f.category, tier: f.tier, at: f.at, lead: f, filings: [f] }); continue }
    s.filings.push(f)
    const rank = (x: Filing) => (x.tier === 'act' ? 0 : x.tier === 'note' ? 1 : 2) - (x.results || x.people ? 1 : 0)
    if (rank(f) < rank(s.lead)) s.lead = f
    if (f.tier === 'act' || (f.tier === 'note' && s.tier === 'fold')) s.tier = f.tier
    if (f.at > s.at) s.at = f.at
  }
  return [...map.values()]
}

export function triage(push: Push, lines: Lines) {
  const end = new Date(push.asof).getTime()
  const start = end - lines.hours * 36e5
  const inWindow = push.filings.filter(f => { const t = new Date(f.at).getTime(); return t >= start && t <= end })
  const all = stories(inWindow)
  const needs: Story[] = [], notes: Story[] = [], folded: Story[] = []
  for (const s of all) {
    if (s.tier === 'act' && lines.interrupt.includes(s.category)) needs.push(s)
    else if (s.tier === 'fold') folded.push(s)
    else notes.push(s)
  }
  const rank = (s: Story) => { const i = ORDER.indexOf(s.category); return i < 0 ? 99 : i }
  needs.sort((a, b) => rank(a) - rank(b) || b.at.localeCompare(a.at))
  notes.sort((a, b) => b.at.localeCompare(a.at))
  const moves = unusualMoves(push, lines, start, end, push.filings)
  return { needs, notes, folded, moves, filings: inWindow.length }
}

// A session closes at 3:30pm IST; it belongs to the window if its close does.
function sessionTime(d: string) { return new Date(`${d}T15:30:00+05:30`).getTime() }

export function unusualMoves(push: Push, lines: Lines, start: number, end: number, filings: Filing[]): Move[] {
  const out: Move[] = []
  for (const [sym, bars] of Object.entries(push.eod)) {
    bars.forEach((b, i) => {
      const t = sessionTime(b.d)
      if (t < start || t > end || i < 20) return
      const prior = bars.slice(i - 20, i)
      const avgVol = prior.reduce((s, x) => s + x.vol, 0) / prior.length
      const volX = avgVol ? b.vol / avgVol : 0
      const why: string[] = []
      if (volX >= lines.volX) why.push('volume')
      if (Math.abs(b.chg) >= lines.movePct) why.push('price')
      if (!why.length) return
      const sameDay = filings.filter(f => f.symbol === sym && f.at.slice(0, 10) <= b.d && f.at.slice(0, 10) >= bars[i - 1].d && f.tier !== 'fold')
      const explainedBy = sameDay.find(f => f.tier === 'act') || sameDay[0]
      out.push({ symbol: sym, d: b.d, close: b.close, chg: b.chg, volX, avgVol, series: bars.slice(Math.max(0, i - 29), i + 1), why, explainedBy })
    })
  }
  return out.sort((a, b) => Math.abs(b.chg) - Math.abs(a.chg))
}

// ---------- the word ----------
export const GRADED: Status[] = ['kept', 'partly', 'missed', 'quiet']
export function wordScore(c: Company | undefined) {
  if (!c) return null
  const hard = c.ledger.filter(p => p.hard)
  const graded = hard.filter(p => GRADED.includes(p.status))
  const kept = graded.filter(p => p.status === 'kept').length + 0.5 * graded.filter(p => p.status === 'partly').length
  return { graded: graded.length, kept, hard: hard.length, ratio: graded.length ? kept / graded.length : null }
}

// ---------- loading ----------
const cache = new Map<string, Company>()
export async function getPush(fresh = false): Promise<Push> {
  const r = await fetch('/data/push.json', fresh ? { cache: 'no-cache' } : undefined)
  if (!r.ok) throw new Error('Could not load filings')
  const p: Push = await r.json()
  // The model's one-line summaries in house style: '300 crores' reads '₹300 crore'
  for (const f of p.filings) if (f.line) f.line = rupees(f.line)
  return p
}
export const forgetCompanies = () => cache.clear()
export const cachedCompany = (sym: string) => cache.get(sym.toUpperCase()) ?? null
export async function getCompany(sym: string): Promise<Company | null> {
  sym = sym.toUpperCase()
  if (cache.has(sym)) return cache.get(sym)!
  const local = localStorage.getItem(`finn.c.${sym}`)
  if (local) { const c = JSON.parse(local); cache.set(sym, c); return c }
  const r = await fetch(`/data/companies/${sym}.json`)
  if (!r.ok || !(r.headers.get('content-type') || '').includes('json')) return null
  const c = await r.json(); cache.set(sym, c); return c
}
export function remember(c: Company) {
  cache.set(c.symbol, c)
  try { localStorage.setItem(`finn.c.${c.symbol}`, JSON.stringify(c)) } catch { /* storage full: keep in memory only */ }
  const recent = JSON.parse(localStorage.getItem('finn.recent') || '[]').filter((s: string) => s !== c.symbol)
  localStorage.setItem('finn.recent', JSON.stringify([c.symbol, ...recent].slice(0, 8)))
}

// Live research for a ticker we haven't built: three kinds of request, each well inside a serverless time limit.
export type Step = { label: string; state: 'wait' | 'run' | 'done' | 'fail'; detail?: string; note?: string }
// Turn API and model errors into a sentence an investor can act on.
export function plainError(m: string): string {
  if (/429|RESOURCE_EXHAUSTED|quota/i.test(m)) return 'The free model quota is used up for now. It resets daily; companies already read still open.'
  if (/NotFound|404/.test(m)) return 'No listed company with that NSE symbol.'
  if (/Failed to fetch|NetworkError|Load failed/i.test(m)) return 'No connection. Check your network and try again.'
  if (/50[0-9]|timeout|timed out/i.test(m)) return 'The server took too long. Try again in a minute.'
  return m.length > 90 ? m.slice(0, 90) + '…' : m
}

export async function buildLive(sym: string, onStep: (steps: Step[]) => void): Promise<Company> {
  const steps: Step[] = [{ label: 'Financials', state: 'run' }]
  const emit = () => onStep(steps.map(s => ({ ...s })))
  emit()
  const post = async (path: string, body: any) => {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    const j = await r.json().catch(() => ({ error: `HTTP ${r.status}` }))
    if (!r.ok || j.error) throw new Error(j.error || `HTTP ${r.status}`)
    return j
  }
  let src: any
  try { src = await post('/api/sources', { symbol: sym }) } catch (e: any) {
    steps[0].state = 'fail'; steps[0].detail = 'stopped'; emit(); throw e
  }
  steps[0].state = 'done'; steps[0].detail = `${src.basis}, ${src.quarters.length} quarters`
  const calls = src.transcripts as any[]
  calls.forEach((t: any) => steps.push({ label: `${t.period} call`, state: 'run' }))
  steps.push({ label: 'Checking promises against the numbers', state: 'wait' })
  emit()
  const results = await Promise.all(calls.map(async (t: any, i: number) => {
    try {
      const c = await post('/api/call', { symbol: sym, period: t.period })
      steps[i + 1].state = c.error ? 'fail' : 'done'
      const n = c.promises?.length ?? 0, first = c.promises?.find((p: any) => p.hard) || c.promises?.[0]
      steps[i + 1].detail = c.error ? 'not readable' : `${c.pages} pages, ${n} ${n === 1 ? 'promise' : 'promises'}`
      // Something real to read while the rest comes in: one promise this call made
      if (!c.error && first?.target) steps[i + 1].note = rupees(first.target.charAt(0).toUpperCase() + first.target.slice(1)) + ((d => d ? `${d[0] === '(' ? ' ' : ', '}${d}` : '')(deadline({ ...first, period: t.period })))
      emit(); return c
    } catch (e: any) {
      steps[i + 1].state = 'fail'; steps[i + 1].detail = plainError(e.message); emit()
      return { period: t.period, url: t.url, error: e.message, promises: [] }
    }
  }))
  const last = steps.length - 1
  steps[last].state = 'run'; emit()
  try {
    const c = await post('/api/grade', { src, calls: results.map(({ usage, ...r }: any) => r) })
    steps[last].state = 'done'; emit()
    // The grade step only meters itself; add the per-call extraction it was built from.
    for (const r of results as any[]) if (r.usage && c.usage) {
      c.usage.calls += r.usage.calls; c.usage.tokens_in += r.usage.tokens_in; c.usage.tokens_out += r.usage.tokens_out
      c.usage.usd_if_billed += r.usage.usd_if_billed
      for (const [m, n] of Object.entries(r.usage.by_model || {})) c.usage.by_model[m] = (c.usage.by_model[m] || 0) + (n as number)
    }
    c.live = true
    remember(c)
    return c
  } catch (e: any) {
    steps[last].state = 'fail'; steps[last].detail = e.message.slice(0, 80); emit(); throw e
  }
}

// The grey "by ..." after a promise. Empty when the promise already names its date ("Ready by August 25")
// or the date is a placeholder, so lines never read "by Q1 next fiscal by Q1 of next fiscal" or "by by".
const DATE_STOP = new Set(['of', 'the', 'this', 'next', 'by', 'a', 'in', 'end', 'to', 'and', 'or'])
const dateWords = (s: string) => s.toLowerCase().replace(/fy\s*20(\d\d)/g, 'fy$1').split(/[^a-z0-9]+/)
  .map(x => x.replace(/^20(\d\d)$/, '$1')).filter(x => x && !DATE_STOP.has(x))
// 'This year' in a November 2025 call means FY26 by the time anyone reads it, so name the year from the call's month.
// Not for April to June calls: on a full-year call 'this year' can mean the year just closed or the one starting.
// Not when the named year is over but the promise is graded not due: the words stay until the grading catches up.
const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
function absolute(w: string, period?: string, status?: string) {
  const m = (period || '').toLowerCase().match(/^([a-z]{3})\w*\s+(\d{4})$/)
  const r = w.match(/^(?:the\s+)?(end of\s+)?(?:the\s+)?(this|current|next|upcoming|coming)\s+(calendar\s+year|(?:fiscal|financial)(?:\s+year)?|year)$/i)
  if (!m || !MONTHS.includes(m[1]) || !r) return w
  const month = MONTHS.indexOf(m[1]), year = +m[2], next = /next|coming/i.test(r[2]) ? 1 : 0
  let label: string, ends: Date
  if (/calendar/i.test(r[3])) { label = `end of ${year + next}`; ends = new Date(year + next, 11, 31) }
  else {
    if (month >= 3 && month <= 5) return w
    const fy = (month >= 3 ? year + 1 : year) + next
    label = `${r[1] ? 'end of ' : ''}FY${String(fy % 100).padStart(2, '0')}`; ends = new Date(fy, 2, 31)
  }
  return status === 'pending' && ends.getTime() < Date.now() ? w : label
}
export function deadline(p: { target: string; by_when: string; period?: string; status?: string }) {
  const raw = (p.by_when || '').replace(/^by\s+/i, '').trim()
  if (!raw || /^(unspecified|not specified|none|n\/a|ongoing)$/i.test(raw)) return ''
  // Already in the promise's own words: just name the year, 'Launch in coming year (FY27)', not '... by FY27'
  const said = new Set(dateWords(p.target))
  const stated = (x: string) => dateWords(x).every(y => said.has(y))
  // 'full year FY26' is just FY26; 'fiscal 29' and 'fiscal 2030' are FY29 and FY30; 'January March 28' is Q4 FY28
  const plain = raw.replace(/^full (?:financial )?year (FY\d\d)$/i, '$1').replace(/\bfiscal (?:20)?(\d\d)\b/i, 'FY$1')
    .replace(/^jan(?:uary)?[-– ]+mar(?:ch)? '?(?:20)?(\d\d)$/i, 'Q4 FY$1')
  const w = absolute(plain, p.period, p.status)
  if (stated(w)) return ''
  // A rate is no deadline ('by annual basis'); a span reads 'within 2 to 3 months', not 'by next 9 months'
  if (/^(?:on an? )?(?:annual|yearly|quarterly|monthly) basis$|^(?:annually|quarterly|per annum|(?:every|each) (?:year|quarter)|(?:consistently )?year[- ]over[- ]year)$/i.test(raw)) return ''
  const n = '(?:\\d+|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|few|couple of)', unit = '(?:weeks?|months?|quarters?|years?)'
  const span = raw.match(new RegExp(`^(?:the\\s+)?(?:over the next|over|next|within|in|coming)?\\s*(${n}(?:\\s+${unit})?(?:\\s*(?:to|-|–|,)\\s*${n})?\\s+${unit})$`, 'i'))
  if (span) return `within ${/^(few|couple)/i.test(span[1]) ? 'a ' : ''}${span[1].replace(/\s*(?:[-–,]|\bto\b)\s*/, ' to ')}`
  if (/^for the (?:full )?year$/i.test(raw)) return 'for the year'
  return stated(raw) ? `(${w})` : `by ${w}`
}

// The 'Reported' line under a graded promise, written by the model from the numbers table:
// 'Mar 2026 Revenue 3739.0, Mar 2026 OPM % 25.0' -> 'Mar 2026 Revenue 3,739, Mar 2026 OPM 25%'
export const tidyEvidence = (t: string) => rupees(t
  .replace(/(\d)\.0\b/g, '$1')
  .replace(/\s?percent\b/g, '%')
  .replace(/\b(OPM|YoY|margin) % (-?\d[\d.]*)(?!\s?%)/gi, '$1 $2%')
  .replace(/\b(OPM|YoY|margin) % /gi, '$1 '))
  // Long numbers grouped, years left as they are
  .replace(/(?<![\d,.₹])(\d{4,})(?!\d|,\d)/g, (m, n) => +n >= 1990 && +n <= 2099 ? m : inr.format(+n))

// Model-written text says 'INR1,450 crores'; the app writes '₹1,450 crore'. Never applied to quotes.
export const rupees = (t: string) => t
  .replace(/\b(?:INR|Rs\.?)\s?(\d[\d,.]*)(\s?(?:to|-|–)\s?(?:(?:INR|Rs\.?)\s?)?(\d[\d,.]*))?\s?([Cc]r(?:ores?)?)\b/g, (_, a, r, b) => `₹${a}${r ? `–${b}` : ''} crore`)
  .replace(/\b(?:INR|Rs\.?)\s?(?=\d)/g, '₹')
  // Lakh crore and crore, not trillion and billion: ₹7.79 trillion is ₹7.79 lakh crore, ₹6.1 billion is ₹610 crore
  .replace(/₹(\d+(?:\.\d+)?)\s?(?:trillion|tn)\b/gi, '₹$1 lakh crore')
  .replace(/₹(\d+(?:\.\d+)?)\s?(?:billion|bn)\b/gi, (_, n) => `₹${+(+n * 100).toFixed(2)} crore`)
  // A bare '300 crores' or '150 crore rupees' is money too, unless it counts something ('2 crore shares')
  .replace(/(?<![₹\d.,–-]|₹\s)(?!(?:19|20)\d\d\s+to\s)(\d[\d,]*(?:\.\d+)?)(?:\s?(?:to|-|–)\s?(\d[\d,]*(?:\.\d+)?))?\s?[Cc]rores?(?:\s+rupees)?\b(?!\s+(?:equity\s+)?(?:shares|units|customers|users|clients|tonnes|tons|people|subscribers|accounts|investors|folios|policies|households|farmers|doses|litres|liters))/g,
    (_, a, b) => `₹${a}${b ? `–${b}` : ''} crore`)
  .replace(/₹(\d{4,})(?:–(\d{4,}))?/g, (_, a, b) => `₹${inr.format(+a)}${b ? `–${inr.format(+b)}` : ''}`)
  // Ranges take an en dash like the rupee ones: '3-5%' -> '3–5%', '240-245 million tons' -> '240–245 million tons'.
  // Only when a unit closes it, so 'FY 2022-23' and dates stay
  .replace(/(\d)\s?-\s?(\d+(?:\.\d+)?)(?=\s?(?:%|x\b|×|(?:million|billion|lakh|crore|bps|basis points|days|months|years|quarters|weeks|GW|MW|tons|tonnes|mtpa|MTPA|stores|plants)\b))/g, '$1–$2')
  // Percentages read as figures: '12 to 15 percent' -> '12–15%', '2.6%-2.7%' and '23% to 24%' -> '2.6–2.7%', '23–24%'
  .replace(/(\d)\s?(?:percent|per cent)\b/gi, '$1%')
  .replace(/(?<!\bfrom\s|[\d.])(\d+(?:\.\d+)?)%?\s?(?:-|–|to)\s?(\d+(?:\.\d+)?)%/g, (m, a, b) => +a < +b ? `${a}–${b}%` : m)
  // Western grouping from the model, '₹285,874', regrouped the Indian way: '₹2,85,874'
  .replace(/₹(\d{1,3}(?:,\d{3})+)(?![\d,])/g, (_, n) => `₹${inr.format(+n.replace(/,/g, ''))}`)
  // A range never splits at its dash ('22–' at a line end, '23%' on the next): word joiner after it
  .replace(/(\d)–(?=[₹\d])/g, '$1–\u2060')
  // and an amount keeps its unit: '₹5.23 lakh crore' never breaks before 'crore'
  .replace(/(₹[\d,.–\u2060]+) (lakh )?crore\b/g, (_, a, l) => `${a}\u00a0${l ? 'lakh\u00a0' : ''}crore`)
  // and a quarter keeps its year: 'Q1 FY27', 'H2 FY26'
  .replace(/\b([QH][1-4]) (FY\d{2,4})\b/g, '$1\u00a0$2')

// ---------- the before-and-after: where a promise stands in the words it came from ----------
// Finds the promise's figures and its deadline inside the verbatim quote, so the quote can be shown with them marked.
// Only what is really in the quote is marked; 'Target found' and 'Date found' are claimed from this and nothing else.
export type QuotePart = { t: string; k?: 'fig' | 'date' }
const MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const ORD = ['first', 'second', 'third', 'fourth']
export function markQuote(quote: string, target: string, byWhen: string): { parts: QuotePart[]; fig: boolean; date: boolean } {
  const spans: [number, number, 'fig' | 'date'][] = []
  const free = (a: number, b: number) => spans.every(([x, y]) => b <= x || a >= y)
  const take = (re: RegExp, k: 'fig' | 'date') => {
    for (const m of quote.matchAll(re)) {
      const a = m.index!, b = a + m[0].length
      if (m[0].trim() && free(a, b)) { spans.push([a, b, k]); return true }
    }
    return false
  }
  // Figures: each number in the promise that isn't part of a date (FY26, Q4, 2026), with its unit as the quote writes it
  const nums = [...new Set([...target.matchAll(/(?<![A-Za-z'’\d.,])\d[\d,]*(?:\.\d+)?/g)]
    .map(m => m[0].replace(/,/g, '')).filter(n => !/^20\d\d$/.test(n)))]
  for (const n of nums) {
    const body = n.split('.').map(part => part.split('').join(',?')).join('\\.')
    take(new RegExp(`(?<![\\d.,])(?:(?:Rs\\.?|INR|₹)\\s?)?${body}(?![\\d])(?:\\s?(?:%|per\\s?cent|percent|times|crores?|bps|basis points|billion|million|lakh|days|MW|GW|MTPA|x|cr)(?![a-z]))?`, 'gi'), 'fig')
  }
  const fig = spans.length > 0
  // The deadline: as written first ('FY26', 'March 2026'), then the usual ways a call says it
  const when = (byWhen || '').replace(/^by\s+/i, '').trim()
  const yy = when.match(/(?:FY|fiscal)\s*['’]?(?:20)?(\d\d)\b/i)?.[1] || when.match(/\b20(\d\d)\b/)?.[1] || when.match(/['’](\d\d)\b/)?.[1]
  const res: RegExp[] = []
  if (when.length > 1) res.push(new RegExp(`(?<![\\w])${when.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+')}(?![\\w])`, 'gi'))
  if (yy) {
    const prev = String(+yy - 1).padStart(2, '0')
    const q = when.match(/\b([QH])([1-4])\b/i)
    if (q) res.push(new RegExp(`\\b(?:${q[1]}${q[2]}|${q[1].toUpperCase() === 'Q' ? ORD[+q[2] - 1] + ' quarter' : (q[2] === '1' ? 'first' : 'second') + ' half'})(?:\\s*(?:of\\s*)?(?:FY|fiscal|financial year)?\\s*['’]?\\s*(?:20)?${yy})?\\b`, 'gi'))
    const mon = MON.findIndex(m => new RegExp(`\\b${m}`, 'i').test(when))
    if (mon >= 0) res.push(new RegExp(`\\b${MON[mon]}[a-z]*\\.?\\s*[-'’‘]?\\s*(?:20)?${yy}\\b`, 'gi'))
    res.push(new RegExp(`\\b(?:FY|F\\.Y\\.?|fiscal(?:\\s+year)?|financial\\s+year)\\s*['’‘]?\\s*(?:20)?${yy}\\b`, 'gi'))
    res.push(new RegExp(`\\b(?:20)?${prev}\\s*[-–/]\\s*(?:20)?${yy}\\b`, 'g'))
    res.push(new RegExp(`\\b20${yy}\\b`, 'g'))
    if (q) res.push(new RegExp(`\\b${q[1]}${q[2]}\\b`, 'gi'))
  }
  const date = res.some(re => take(re, 'date'))
  spans.sort((a, b) => a[0] - b[0])
  const parts: QuotePart[] = []
  let at = 0
  for (const [a, b, k] of spans) { if (a > at) parts.push({ t: quote.slice(at, a) }); parts.push({ t: quote.slice(a, b), k }); at = b }
  if (at < quote.length) parts.push({ t: quote.slice(at) })
  return { parts, fig, date }
}
