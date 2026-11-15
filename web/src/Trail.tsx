import { deadline, markQuote, plainTerms, rupees, tidyEvidence, type Promise_, type QuotePart } from './lib'
import { Src, STATUS_WORD, StatusLabel } from './ui'

// A not-due verdict that only restates the promise ('... remains ongoing') says nothing; the chip already does
const FILLER = /\b(remains|is) (still )?(pending|ongoing)\b|\bnot yet due\b/i
export const verdictText = (p: Promise_) => p.status === 'pending' && FILLER.test(p.verdict || '') ? '' : p.verdict ? plainTerms(rupees(p.verdict)) : STATUS_WORD[p.status]
export const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)
// Plain words first, the finance term in brackets after (lib.ts, plainTerms). Figures are never touched
export { plainTerms }
export const promiseLine = (p: Promise_) => `${cap(plainTerms(rupees(p.target)))}${deadline(p) ? ` ${rupees(deadline(p))}` : ''}`

// On a card there's room for one sentence of the quote: the one the promise came from
export function clip(parts: QuotePart[]): QuotePart[] {
  const text = parts.map(x => x.t).join('')
  if (text.length <= 200) return parts
  let at = 0, first = -1
  for (const x of parts) { if (x.k && first < 0) first = at; at += x.t.length }
  if (first < 0) first = 0
  const before = text.slice(0, first), after = text.slice(first)
  const start = Math.max(0, ...[...before.matchAll(/[.!?]\s+/g)].map(m => m.index! + m[0].length))
  const endM = after.match(/[.!?](?=\s|$)/), end = endM ? first + endM.index! + 1 : text.length
  const out: QuotePart[] = []
  at = 0
  for (const x of parts) {
    const a = at, b = at + x.t.length; at = b
    const s = Math.max(a, start), e = Math.min(b, end)
    if (e > s) out.push({ t: x.t.slice(s - a, e - a), k: x.k })
  }
  if (start > 0) out.unshift({ t: '…' })
  if (end < text.length) out.push({ t: ' …' })
  return out
}

// Folio's before-and-after. What management said, with the figure and the date marked where they stand; chips naming
// what FINN found in it; the promise as one clean line; then what the filings showed. Compact on a card: one sentence
// of the quote, no speaker line; the company page shows it whole.
export function Trail({ p, compact }: { p: Promise_; compact?: boolean }) {
  const m = markQuote(p.quote, p.target, p.by_when)
  const parts = compact ? clip(m.parts) : m.parts
  const v = verdictText(p)
  return (
    <div className={`fo-trail${compact ? ' fo-trail-compact' : ''}`}>
      <div className="fo-trail-step fo-said">
        <p className="fo-trail-k">They said{compact ? `, ${p.period.replace(/ 20/, ' ’')}` : ''}</p>
        <blockquote className="fo-trail-q">“{parts.map((x, i) => x.k ? <mark key={i} className={`fo-mk fo-mk-${x.k}`}>{x.t}</mark> : <span key={i}>{x.t}</span>)}”</blockquote>
        {!compact && <p className="fo-trail-who">{p.speaker}, <Src href={`${p.url}#page=${p.page}`}>{p.period} call, page {p.page}</Src>
          {p.restated?.length ? <>. Said again: {p.restated.filter((r, k, all) => all.findIndex(x => x.period === r.period) === k).map((r, k) => <span key={k}>{k ? ', ' : ' '}<Src href={`${r.url}#page=${r.page}`}>{r.period}</Src></span>)}</> : null}</p>}
      </div>
      {(m.fig || m.date) && <div className="fo-trail-chips" aria-label="What FINN found in the quote">
        {m.fig && <span className="fo-chip fo-chip-fig">Target found</span>}
        {m.date && <span className="fo-chip fo-chip-date">Date found</span>}
      </div>}
      <div className="fo-trail-step fo-promise">
        <p className="fo-trail-k">The promise</p>
        <p className="fo-trail-p">{promiseLine(p)}</p>
      </div>
      <div className="fo-trail-step fo-shown">
        <p className="fo-trail-k">What the filings showed</p>
        <div className="fo-trail-v"><StatusLabel status={p.status} />{v && <p>{v}</p>}</div>
        {!compact && p.evidence && (p.evidence_kind === 'quote'
          ? <p className="fo-trail-ev">On the latest call: <q>{p.evidence}</q> <Src href={p.evidence_url ? `${p.evidence_url}#page=${p.evidence_page}` : undefined}>page {p.evidence_page}</Src></p>
          : <p className="fo-trail-ev">From its reported numbers: {plainTerms(tidyEvidence(p.evidence))}</p>)}
      </div>
    </div>
  )
}
