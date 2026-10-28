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
export const minus = (s: string | number) => String(s).replace(/^-/, '−')
export const pct = (v: number | null | undefined, sign = true) =>
  v == null ? '–' : `${sign && v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(Math.abs(v) < 10 ? 1 : 0)}%`
export const tone = (v: number | null | undefined) => (v == null || Math.abs(v) < 0.05 ? '' : v > 0 ? 'up' : 'down')
export const shortName = (n: string) =>
  n.replace(/\s*\(India\)/i, '').replace(/\s+(Ltd|Limited)\.?$/i, '').replace(/\s+(India|Industries|International|Company|Finance Company India|Corporation of India|Express)$/i, '').replace(/\s+(India|Industries)$/i, '')

export function when(iso: string, asof: string) {
  const d = new Date(iso), now = new Date(asof)
  const hrs = (now.getTime() - d.getTime()) / 36e5
  const time = d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()
  if (hrs < 24 && d.getDate() === now.getDate()) return time
  if (hrs < 48) return `Yesterday ${time}`
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
export async function getPush(): Promise<Push> {
  const r = await fetch('/data/push.json')
  if (!r.ok) throw new Error('Could not load filings')
  return r.json()
}
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
export type Step = { label: string; state: 'wait' | 'run' | 'done' | 'fail'; detail?: string }
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
      steps[i + 1].detail = c.error ? 'not readable' : `${c.pages} pages, ${c.promises.length} promises`
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
  const r = w.match(/^(?:the\s+)?(end of\s+)?(?:the\s+)?(this|current|next)\s+(calendar\s+year|(?:fiscal|financial)(?:\s+year)?|year)$/i)
  if (!m || !MONTHS.includes(m[1]) || !r) return w
  const month = MONTHS.indexOf(m[1]), year = +m[2], next = /next/i.test(r[2]) ? 1 : 0
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
  const w = absolute((p.by_when || '').replace(/^by\s+/i, '').trim(), p.period, p.status)
  if (!w || /^(unspecified|not specified|none|n\/a|ongoing)$/i.test(w)) return ''
  const said = new Set(dateWords(p.target))
  return dateWords(w).every(x => said.has(x)) ? '' : `by ${w}`
}

// Model-written text says 'INR1,450 crores'; the app writes '₹1,450 crore'. Never applied to quotes.
export const rupees = (t: string) => t
  .replace(/\b(?:INR|Rs\.?)\s?(\d[\d,.]*)(\s?(?:to|-|–)\s?(?:(?:INR|Rs\.?)\s?)?(\d[\d,.]*))?\s?([Cc]r(?:ores?)?)\b/g, (_, a, r, b) => `₹${a}${r ? `–${b}` : ''} crore`)
  .replace(/\b(?:INR|Rs\.?)\s?(?=\d)/g, '₹')
  .replace(/₹(\d{4,})(?:–(\d{4,}))?/g, (_, a, b) => `₹${inr.format(+a)}${b ? `–${inr.format(+b)}` : ''}`)
