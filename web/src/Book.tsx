import { useEffect, useState } from 'react'
import { cachedCompany, deadline, getCompany, pct, rupees, shortName, wordScore, type Company, type Promise_, type Push, type Status } from './lib'
import { Masthead, Outcome, StatusLabel, useKept } from './ui'

// The whole book, ordered by how far management's word has held. Weakest first: that's where to look.
export function Book({ push, openCompany }: { push: Push; openCompany: (s: string) => void }) {
  // undefined: still loading; null: no file
  const [cos, setCos] = useState<Record<string, Company | null | undefined>>(() => Object.fromEntries(push.portfolio.map(p => [p.symbol, cachedCompany(p.symbol) ?? undefined])))
  const [only, setOnly] = useKept<Status | null>('book.only', null)
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    push.portfolio.forEach(p => getCompany(p.symbol).catch(() => null).then(c => setCos(prev => ({ ...prev, [p.symbol]: c }))))
    const t = setTimeout(() => setSlow(true), 400); return () => clearTimeout(t)
  }, [push])
  // Prices are the last exchange close in the snapshot, often the day before it; say which
  const closeDay = Object.values(push.eod).reduce((m, bars: any) => { const d = bars?.[bars.length - 1]?.d; return d && d > m ? d : m }, '')
  const closeLabel = closeDay ? new Date(closeDay + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : ''
  const head = <>
    <Masthead />
    <header className="page-top">
      <h1 className="sec-head">Your book</h1>
      <p className="serif-line">{push.portfolio.length} holdings, the weakest word first. Prices at the {closeLabel} close.</p>
    </header>
  </>
  // Order and tally only once every holding is in, so counts don't climb and rows don't reshuffle
  if (push.portfolio.some(p => cos[p.symbol] === undefined)) {
    return <main className="screen book">{head}{slow && <p className="sub opening"><span className="dot-run" />Opening the ledgers</p>}</main>
  }

  const rows = push.portfolio.map(p => {
    const c = cos[p.symbol]
    const bars = push.eod[p.symbol] || []
    return { p, c, score: wordScore(c || undefined), last: bars[bars.length - 1] }
  })
  const missed = (c?: Company | null) => c ? c.ledger.filter(x => x.hard && x.status === 'missed').length : 0
  // Kept share with one kept and one not added, so 0 of 1 doesn't outrank 1 of 7
  const share = (s: ReturnType<typeof wordScore>) => s?.graded ? (s.kept + 1) / (s.graded + 2) : 2
  rows.sort((a, b) => share(a.score) - share(b.score) || missed(b.c) - missed(a.c) || (b.score?.graded ?? 0) - (a.score?.graded ?? 0))
  const shown = only ? rows.filter(r => r.c?.ledger.some(x => x.hard && x.status === only)) : rows

  return (
    <main className="screen book">
      {head}
      <BookTally cos={Object.values(cos)} only={only} setOnly={setOnly} />
      {only && <p className="book-filter sub" aria-live="polite">{shown.length} with {WITH[only]} <button className="text-btn" onClick={() => setOnly(null)}>Show all</button></p>}
      <ul className="book-list">
        {shown.map(({ p, c, score, last }) => {
          const weak = weakest(c, only)
          const kept = score ? Math.floor(score.kept) : 0
          const pending = c ? c.ledger.filter(x => x.hard && x.status === 'pending').length : 0
          return (
            <li key={p.symbol}>
              <button className="book-card" onClick={() => openCompany(p.symbol)}>
                <div className="card-lbl"><span className="lbl lbl-quiet">{p.sector}</span>{weak && <StatusLabel status={weak.status} />}</div>
                <div className="book-head">
                  <span className="card-title">{p.short || shortName(p.name)}</span>
                  <span className="book-rec">
                    {score?.graded
                      ? <Outcome size="xs" value={kept} unit={`/${score.graded} kept`} />
                      : <Outcome size="xs" value={pending || '–'} unit={pending ? ' not due' : ''} />}
                  </span>
                </div>
                <p className="card-desc">{weak ? weakLine(weak) : c && c.calls.length && c.calls.every(x => x.error) ? "The call transcripts couldn't be opened." : 'No promise with a number and a date yet.'}</p>
                {last && <p className="book-px"><span className="num">₹{last.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>, <span className="num">{pct(last.chg)}</span> on the day</p>}
              </button>
            </li>
          )
        })}
      </ul>
    </main>
  )
}
const ORDER: Status[] = ['missed', 'quiet', 'partly', 'kept', 'pending', 'unclear']
const WITH: Partial<Record<Status, string>> = { kept: 'a promise kept', partly: 'a promise partly kept', missed: 'a promise missed', quiet: 'a promise gone quiet', pending: 'a promise not yet due' }
// The one promise to name on the card: the worst-kept, newest call first; under a filter, one of that kind
function weakest(c: Company | null | undefined, only: Status | null): Promise_ | undefined {
  const hard = (c?.ledger || []).filter(x => x.hard && x.status !== 'unclear' && (!only || x.status === only))
  return [...hard].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status))[0]
}
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)
const weakLine = (p: Promise_) => `${cap(rupees(p.target))}${deadline(p) ? ` ${deadline(p)}` : ''}.`

// Across the whole book: how many promises management teams have kept, missed or let go quiet.
// Tap a count to see only the companies behind it; tap again for the whole book.
function BookTally({ cos, only, setOnly }: { cos: (Company | null | undefined)[]; only: Status | null; setOnly: (s: Status | null) => void }) {
  const all = cos.flatMap(c => (c?.ledger || []).filter(p => p.hard))
  if (!all.length) return null
  const n = (st: Status) => all.filter(p => p.status === st).length
  const teams = (st: Status) => cos.filter(c => c?.ledger.some(p => p.hard && p.status === st)).length
  const at = (st: Status) => `At ${teams(st)} ${teams(st) === 1 ? 'company' : 'companies'}`
  const items: [Status, string, string][] = [
    ['missed', 'Missed: the date passed without it.', at('missed')],
    ['quiet', 'Gone quiet: due now, not mentioned on the latest call.', at('quiet')],
    ['kept', 'Kept: delivered, or on track in the numbers.', at('kept')],
    ['partly', 'Partly kept, or kept late.', at('partly')],
    ['pending', 'Not due yet.', 'Still running'],
  ]
  return (
    <section className="og-panel" aria-label="Promises across your book">
      <h2 className="lbl lbl-quiet">Promises across your book</h2>
      <ul className="og book-og">
        {items.map(([st, d1, d2]) => n(st) ? (
          <li key={st}>
            <button className="og-item og-btn" aria-pressed={only === st} onClick={() => setOnly(only === st ? null : st)}>
              <Outcome value={n(st)} />
              <span className="og-d1">{d1}</span>
              <span className="og-d2">{d2}</span>
            </button>
          </li>
        ) : null)}
      </ul>
    </section>
  )
}
