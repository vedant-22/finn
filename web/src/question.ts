// Ask: a question about a company or the book, answered from the promise ledgers FINN has already built.
// No model call. A question is a company, a topic and what the investor wants to know (delivered? missed? still due?).
import type { Promise_, Status } from './lib.ts'

export interface Topic { key: string; label: string; metrics: string[]; words: RegExp }
// Checked in order: 'volume growth' is volume before it is growth
export const TOPICS: Topic[] = [
  { key: 'volume', label: 'volumes', metrics: ['volume'], words: /\bvolumes?\b/ },
  { key: 'margin', label: 'margins', metrics: ['margin'], words: /margin|ebitda|profitab/ },
  { key: 'profit', label: 'profit', metrics: ['profit'], words: /profit|\bpat\b|earnings|bottom ?line/ },
  // 'grow', 'grows', 'growing', not 'lab-grown'
  { key: 'revenue', label: 'revenue growth', metrics: ['revenue_growth'], words: /revenue|sales|top ?line|growth|\bgrow(?!n)/ },
  { key: 'capacity', label: 'capacity and capex', metrics: ['capacity', 'capex'], words: /capex|capacity|plant|factor(y|ies)|expan|commission|invest|spend/ },
  { key: 'launch', label: 'launches', metrics: ['launch'], words: /launch|new products?/ },
  { key: 'share', label: 'market share', metrics: ['market_share'], words: /market share|\bshare\b/ },
  { key: 'wc', label: 'working capital', metrics: ['working_capital'], words: /working capital|receivable|inventor|cash cycle/ },
  { key: 'debt', label: 'debt', metrics: ['debt'], words: /\bdebt|borrow|leverage|net cash/ },
]

export type Intent = 'delivered' | 'missed' | 'quiet' | 'due' | null
// rest: what the question is about when no topic covers it ('lab grown diamonds'), so the answer can say it isn't there
export interface Parsed { symbol?: string; ticker?: string; topic?: Topic; intent: Intent; fy?: string; book: boolean; rest?: string }

const STOP = new Set(`a an and any are as at be by can did do does for from has have how i in is it its me my of on or our show tell the their them they this to was were what when where which who why will with you your
  deliver delivered delivering kept keep keeping miss missed missing promise promised promises said say guide guided guidance plan planned expect
  quiet gone hit meet met achieve achieved book holdings companies company management team teams read research look up open about any anything
  margin margins revenue growth profit capex capacity debt volume volumes launch launches share working capital fy next year quarter
  think view outlook update latest recent comment commentary talk talked mention mentioned doing going today now much more last call calls
  results good well there been should would could into than then also just still over under since target targets number numbers
  word words record track trust credible credibility honest reliable doing done
  due pending outstanding running against corp saying says go went happen happened new news`.split(/\s+/))

export interface Known { symbol: string; names: string[]; held?: boolean }
// The names a company goes by in a question: its symbol, its short name, its full name without 'Ltd'
export function aliases(symbol: string, name: string, short?: string): string[] {
  const full = name.toLowerCase().replace(/\b(ltd|limited|india)\b\.?/g, '').replace(/\(\s*\)/g, '').replace(/\s+/g, ' ').trim()
  const first = full.split(' ')[0]
  const out = [symbol.toLowerCase(), full, (short || '').toLowerCase()]
  // 'KFin' and 'Titan' are said alone; 'home' and 'blue' are not, and 'HDFC' alone could be another HDFC company
  if (first.length >= 4 && !['blue', 'home', 'power', 'hdfc'].includes(first)) out.push(first)
  // 'Home First', 'Sun Pharmaceutical', 'Transport Corporation': a longer name's first two words
  for (const n of [full, (short || '').toLowerCase()]) {
    const w = n.split(' ')
    if (w.length >= 3 && /^[a-z]+ [a-z]+$/.test(`${w[0]} ${w[1]}`)) out.push(`${w[0]} ${w[1]}`)
  }
  if (full.includes(' & ')) out.push(full.replace(' & ', ' and '))
  // 'Larsen & Toubro' is L&T in conversation
  const amp = full.match(/^(\w)\w* & (\w)\w*$/)
  if (amp) out.push(`${amp[1]}&${amp[2]}`, `${amp[1]} and ${amp[2]}`)
  return [...new Set(out.filter(Boolean))]
}

const NOT_SYMBOL = /^(?:FY'?\d\d|[1-4]?Q[1-4]?|H[12]|9M|CEO|CFO|COO|CTO|MD|EBITDA|EBIT|PAT|PBT|ROE|ROCE|AUM|LDR|NSE|BSE|AI|IT|US|FINN)$/i
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
export function parse(q: string, known: Known[]): Parsed {
  const t = ` ${q.toLowerCase().replace(/[’']s\b/g, '').replace(/[?!.,]/g, ' ').replace(/\s+/g, ' ')} `
  // The longest name that appears as whole words wins: 'hdfc bank' over 'hdfc'
  let symbol: string | undefined, best = 0, said = ''
  for (const k of known) for (const a of k.names) {
    if (a.length > best && new RegExp(`[^a-z0-9&]${esc(a)}[^a-z0-9&]`).test(t)) { symbol = k.symbol; best = a.length; said = a }
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
    // A year, a quarter or a title in capitals is not a symbol: 'FY27', 'Q2', 'CFO'
    const words = q.replace(/[?!.,]/g, ' ').split(/\s+/).filter(w => /^[A-Za-z][A-Za-z0-9&-]{1,19}$/.test(w) && !STOP.has(w.toLowerCase()) && !NOT_SYMBOL.test(w))
    const caps = words.find(w => w === w.toUpperCase() && w.length >= 2)
    ticker = (caps || (words.length === 1 ? words[0] : undefined))?.toUpperCase()
  }
  const book = !symbol && !ticker
  // With no topic, the words left once the company and the asking words are gone are what it is about
  const rest = topic ? undefined : (said ? t.replace(said, ' ') : t).split(/[\s-]+/)
    .filter(w => w.length >= 3 && /^[a-z]+$/.test(w) && !STOP.has(w) && w !== ticker?.toLowerCase()).join(' ') || undefined
  return { symbol, ticker, topic, intent, fy: fy ? `FY${fy}` : undefined, book, rest }
}

const SETTLED: Status[] = ['missed', 'partly', 'quiet', 'kept']
const ORDER: Status[] = ['missed', 'partly', 'quiet', 'unclear', 'kept', 'pending']
// A promise past its date with nothing said has come due, as the company page and Book count it (wordScore).
// It is the only 'can’t tell yet' an answer holds.
const pastDue = (x: Pick<Promise_, 'checked'>) => x.checked === 'past_due'
export const cameDue = (x: Pick<Promise_, 'status' | 'checked'>) => SETTLED.includes(x.status) || pastDue(x)
// 'FY26-27' and 'FY 25-26' name the later year
const years = (s: string) => s.toUpperCase().replace(/\s/g, '').replace(/FY(\d\d)-(\d\d)/g, 'FY$2')
const month = (p: Promise_) => +p.period.slice(-4) * 12 + ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].indexOf(p.period.slice(0, 3).toLowerCase())

// The promises that answer the question, worst-kept first, newest call first among equals
export function matching(ledger: Promise_[], p: Pick<Parsed, 'topic' | 'intent' | 'fy'>): Promise_[] {
  let xs = ledger.filter(x => x.hard && (x.status !== 'unclear' || pastDue(x)))
  if (p.topic) {
    const tw = p.topic.words
    // The grader's metric decides; the words only place promises it filed under 'other'
    xs = xs.filter(x => p.topic!.metrics.includes(x.metric) || (x.metric === 'other' && tw.test(`${x.topic} ${x.target}`.toLowerCase())))
  }
  if (p.fy) xs = xs.filter(x => years(`${x.by_when} ${x.target}`).includes(p.fy!))
  if (p.intent === 'missed') xs = xs.filter(x => x.status === 'missed' || x.status === 'partly')
  else if (p.intent === 'quiet') xs = xs.filter(x => x.status === 'quiet')
  else if (p.intent === 'due') xs = xs.filter(x => x.status === 'pending')
  else if (p.intent === 'delivered' && xs.some(cameDue)) xs = xs.filter(cameDue)
  return xs.sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || month(b) - month(a))
}

// The answer in a word or two, for the headline: 'missed', 'kept', 'kept 2 of 3', 'not yet due'
export function verdictHead(xs: Promise_[]): string {
  const done = xs.filter(cameDue)
  if (!done.length) return xs.some(x => x.status === 'pending') ? 'not yet due' : 'can’t tell yet'
  // One settled promise is named by its own word: 'partly done', 'no update', never 'kept 0 of 1'
  if (done.length === 1) return ({ kept: 'kept', partly: 'partly done', missed: 'missed', quiet: 'no update', unclear: 'can’t tell yet' } as Record<string, string>)[done[0].status]
  const k = done.filter(x => x.status === 'kept').length
  const all = done.length === 2 ? 'both' : `all ${done.length}`
  if (k === done.length) return `kept ${all}`
  if (done.every(x => x.status === 'missed')) return `missed ${all}`
  if (done.every(x => x.status === 'quiet')) return `no update on ${all}`
  // 'What has Dixon missed?' holds no kept promise by its asking: count what it found, as the book answer does
  if (done.every(x => x.status === 'partly')) return `${done.length} partly done`
  if (done.every(x => x.status === 'missed' || x.status === 'partly')) return `${done.length} missed or partly done`
  return `kept ${k || 'none'} of ${done.length}`
}
// 'On revenue growth: 1 missed, 2 not yet due.'
export function tally(xs: Promise_[]): string {
  const word: Record<string, string> = { missed: 'missed', partly: 'partly done', quiet: 'no update', unclear: 'can’t tell yet', kept: 'kept', pending: 'not yet due' }
  const n = (s: Status) => xs.filter(x => x.status === s).length
  return ORDER.filter(s => n(s) > 0 && word[s]).map(s => `${n(s)} ${word[s]}`).join(', ')
}

// The financial year a quarter's month falls in: 'Sep 2026' is FY27 (April to March)
export const fyOf = (q: string) => { const m = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].indexOf(q.slice(0, 3).toLowerCase()), y = +q.slice(-4); return `FY${String((m >= 3 ? y + 1 : y) % 100).padStart(2, '0')}` }

// This year's revenue guide, read against the latest quarter's revenue growth on a year ago. A pace, not a verdict:
// one quarter says how it's going, the year decides. Revenue in percent only; order books, loan books and CAGRs don't map.
export function pace(p: Promise_, revYoy: number | null | undefined): 'ahead' | 'on track' | 'behind' | null {
  if (revYoy == null || p.status !== 'pending' || p.metric !== 'revenue_growth' || !/revenue/i.test(p.target) || /order|loan|book|inflow|cagr/i.test(p.target)) return null
  const m = p.target.match(/(\d+(?:\.\d+)?)\s*%?\s*(?:to|–|-)\s*(\d+(?:\.\d+)?)\s*%/) || p.target.match(/(\d+(?:\.\d+)?)\s*%/)
  if (!m) return null
  const lo = +m[1], hi = m[2] ? +m[2] : lo
  return revYoy > hi ? 'ahead' : revYoy < lo ? 'behind' : 'on track'
}

// The running revenue guide for the year of the latest quarter, if management gave one
export function runningGuide(ledger: Promise_[], quarter: string | undefined) {
  if (!quarter) return undefined
  const fy = fyOf(quarter)
  const g = ledger.find(p => p.hard && p.status === 'pending' && (p.by_when || '').toUpperCase().replace(/\s/g, '').includes(fy) && pace(p, 0) !== null)
  return g && { g, fy }
}

// Revenue growth for the year so far, on the same quarters a year earlier: Q1, H1 or 9M. A guide for the year is
// read against this, not against one quarter. Each quarter's year-ago figure comes from its own growth.
export function yearToDate(quarters: { q: string; rev: number; rev_yoy: number | null }[]): { growth: number; label: string; fy: string } | null {
  const last = quarters[quarters.length - 1]
  if (!last) return null
  const fy = fyOf(last.q)
  const xs = quarters.filter(x => fyOf(x.q) === fy)
  if (!xs.length || xs.some(x => x.rev_yoy == null || !x.rev)) return null
  const now = xs.reduce((n, x) => n + x.rev, 0), then = xs.reduce((n, x) => n + x.rev / (1 + x.rev_yoy! / 100), 0)
  return { growth: (now / then - 1) * 100, label: ['Q1', 'H1', '9M', 'FY'][xs.length - 1] || 'FY', fy }
}
