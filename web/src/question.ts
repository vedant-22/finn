// Ask: a question about a company or the book, answered from the promise ledgers FINN has already built.
// No model call. A question is a company, a topic and what the investor wants to know (delivered? missed? still due?).
import type { Promise_, Status } from './lib.ts'

export interface Topic { key: string; label: string; metrics: string[]; words: RegExp }
// Checked in order: 'volume growth' is volume before it is growth
export const TOPICS: Topic[] = [
  { key: 'volume', label: 'volumes', metrics: ['volume'], words: /\bvolumes?\b/ },
  { key: 'margin', label: 'margins', metrics: ['margin'], words: /margin|ebitda|profitab/ },
  { key: 'profit', label: 'profit', metrics: ['profit'], words: /profit|\bpat\b|earnings|bottom ?line/ },
  { key: 'revenue', label: 'revenue growth', metrics: ['revenue_growth'], words: /revenue|sales|top ?line|growth|\bgrow/ },
  { key: 'capacity', label: 'capacity and capex', metrics: ['capacity', 'capex'], words: /capex|capacity|plant|factor(y|ies)|expan|commission|invest|spend/ },
  { key: 'launch', label: 'launches', metrics: ['launch'], words: /launch|new products?/ },
  { key: 'share', label: 'market share', metrics: ['market_share'], words: /market share|\bshare\b/ },
  { key: 'wc', label: 'working capital', metrics: ['working_capital'], words: /working capital|receivable|inventor|cash cycle/ },
  { key: 'debt', label: 'debt', metrics: ['debt'], words: /\bdebt|borrow|leverage|net cash/ },
]

export type Intent = 'delivered' | 'missed' | 'quiet' | 'due' | null
export interface Parsed { symbol?: string; ticker?: string; topic?: Topic; intent: Intent; fy?: string; book: boolean }

const STOP = new Set(`a an and any are as at be by can did do does for from has have how i in is it its me my of on or our show tell the their them they this to was were what when where which who why will with you your
  deliver delivered delivering kept keep keeping miss missed missing promise promised promises said say guide guided guidance plan planned expect
  quiet gone hit meet met achieve achieved book holdings companies company management team teams read research look up open about any anything
  margin margins revenue growth profit capex capacity debt volume volumes launch launches share working capital fy next year quarter`.split(/\s+/))

export interface Known { symbol: string; names: string[]; held?: boolean }
// The names a company goes by in a question: its symbol, its short name, its full name without 'Ltd'
export function aliases(symbol: string, name: string, short?: string): string[] {
  const full = name.toLowerCase().replace(/\b(ltd|limited|india)\b\.?/g, '').replace(/\s+/g, ' ').trim()
  const first = full.split(' ')[0]
  const out = [symbol.toLowerCase(), full, (short || '').toLowerCase()]
  if (first.length >= 5 && !['blue', 'home', 'power'].includes(first)) out.push(first)
  // 'Larsen & Toubro' is L&T in conversation
  const amp = full.match(/^(\w)\w* & (\w)\w*$/)
  if (amp) out.push(`${amp[1]}&${amp[2]}`, `${amp[1]} and ${amp[2]}`)
  return [...new Set(out.filter(Boolean))]
}

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
export function parse(q: string, known: Known[]): Parsed {
  const t = ` ${q.toLowerCase().replace(/[’']s\b/g, '').replace(/[?!.,]/g, ' ').replace(/\s+/g, ' ')} `
  // The longest name that appears as whole words wins: 'hdfc bank' over 'hdfc'
  let symbol: string | undefined, best = 0
  for (const k of known) for (const a of k.names) {
    if (a.length > best && new RegExp(`[^a-z0-9&]${esc(a)}[^a-z0-9&]`).test(t)) { symbol = k.symbol; best = a.length }
  }
  const topic = TOPICS.find(x => x.words.test(t))
  const intent: Intent = /\bmiss|fail|fell short|slip/.test(t) ? 'missed'
    : /quiet|forgot|dropp|silent|stopped talking/.test(t) ? 'quiet'
      : /deliver|\bkeep|\bkept|achiev|\bhit\b|\bmet\b|\bmeet|did they|have they|track record|record/.test(t) ? 'delivered'
        : /promis|guid|expect|plan|due|next|upcoming|coming/.test(t) ? 'due' : null
  const fy = t.match(/\bfy ?'?(\d{2})\b/)?.[1]
  // No known company: a word that looks like a symbol is one to research ('ASTRAL', 'read astral')
  let ticker: string | undefined
  if (!symbol) {
    const words = q.replace(/[?!.,]/g, ' ').split(/\s+/).filter(w => /^[A-Za-z][A-Za-z0-9&-]{1,19}$/.test(w) && !STOP.has(w.toLowerCase()))
    const caps = words.find(w => w === w.toUpperCase() && w.length >= 2)
    ticker = (caps || (words.length === 1 ? words[0] : undefined))?.toUpperCase()
  }
  const book = !symbol && !ticker
  return { symbol, ticker, topic, intent, fy: fy ? `FY${fy}` : undefined, book }
}

const SETTLED: Status[] = ['missed', 'partly', 'quiet', 'kept']
const ORDER: Status[] = ['missed', 'partly', 'quiet', 'kept', 'pending', 'unclear']
const month = (p: Promise_) => +p.period.slice(-4) * 12 + ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].indexOf(p.period.slice(0, 3).toLowerCase())

// The promises that answer the question, worst-kept first, newest call first among equals
export function matching(ledger: Promise_[], p: Pick<Parsed, 'topic' | 'intent' | 'fy'>): Promise_[] {
  let xs = ledger.filter(x => x.hard && x.status !== 'unclear')
  if (p.topic) {
    const tw = p.topic.words
    // The grader's metric decides; the words only place promises it filed under 'other'
    xs = xs.filter(x => p.topic!.metrics.includes(x.metric) || (x.metric === 'other' && tw.test(`${x.topic} ${x.target}`.toLowerCase())))
  }
  if (p.fy) xs = xs.filter(x => `${x.by_when} ${x.target}`.toUpperCase().replace(/\s/g, '').includes(p.fy!))
  if (p.intent === 'missed') xs = xs.filter(x => x.status === 'missed' || x.status === 'partly')
  else if (p.intent === 'quiet') xs = xs.filter(x => x.status === 'quiet')
  else if (p.intent === 'due') xs = xs.filter(x => x.status === 'pending')
  else if (p.intent === 'delivered' && xs.some(x => SETTLED.includes(x.status))) xs = xs.filter(x => SETTLED.includes(x.status))
  return xs.sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || month(b) - month(a))
}

// The answer in a word or two, for the headline: 'missed', 'kept', 'kept 2 of 3', 'not due yet'
export function verdictHead(xs: Promise_[]): string {
  const done = xs.filter(x => ['kept', 'partly', 'missed', 'quiet'].includes(x.status))
  if (!done.length) return xs.some(x => x.status === 'pending') ? 'not due yet' : 'can’t tell yet'
  const k = done.filter(x => x.status === 'kept').length
  if (k === done.length) return done.length === 1 ? 'kept' : `kept all ${done.length}`
  if (done.every(x => x.status === 'missed')) return done.length === 1 ? 'missed' : `missed all ${done.length}`
  return `kept ${k} of ${done.length}`
}
// 'On revenue growth: 1 missed, 2 not due yet.'
export function tally(xs: Promise_[]): string {
  const word: Record<string, string> = { missed: 'missed', partly: 'partly kept', quiet: 'gone quiet', kept: 'kept', pending: 'not due yet' }
  const n = (s: Status) => xs.filter(x => x.status === s).length
  return ORDER.filter(s => n(s) > 0 && word[s]).map(s => `${n(s)} ${word[s]}`).join(', ')
}
