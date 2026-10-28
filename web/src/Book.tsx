import { useEffect, useState } from 'react'
import { getCompany, pct, shortName, tone, wordScore, type Company, type Push, type Status } from './lib'
import { Mark } from './ui'

// The whole book, ordered by how far management's word has held. Weakest first: that's where to look.
export function Book({ push, openCompany }: { push: Push; openCompany: (s: string) => void }) {
  const [cos, setCos] = useState<Record<string, Company | null>>({})
  const [only, setOnly] = useState<Status | null>(null)
  useEffect(() => {
    push.portfolio.forEach(p => getCompany(p.symbol).then(c => setCos(prev => ({ ...prev, [p.symbol]: c }))))
  }, [push])

  const rows = push.portfolio.map(p => {
    const c = cos[p.symbol]
    const bars = push.eod[p.symbol] || []
    const last = bars[bars.length - 1]
    return { p, c, score: wordScore(c || undefined), last }
  })
  const missed = (c?: Company | null) => c ? c.ledger.filter(x => x.hard && x.status === 'missed').length : 0
  rows.sort((a, b) => (a.score?.ratio ?? 2) - (b.score?.ratio ?? 2) || missed(b.c) - missed(a.c) || (b.score?.graded ?? 0) - (a.score?.graded ?? 0))
  const shown = only ? rows.filter(r => r.c?.ledger.some(x => x.hard && x.status === only)) : rows

  return (
    <main className="screen book">
      <header className="top"><h1>Your book</h1><span className="sub">{push.portfolio.length} holdings, weakest word first</span></header>
      <BookTally cos={Object.values(cos)} only={only} setOnly={setOnly} />
      {only && <p className="book-filter sub" aria-live="polite">{shown.length} with {WITH[only]} <button className="text-btn" onClick={() => setOnly(null)}>Show all</button></p>}
      <ul className="book-list">
        {shown.map(({ p, c, score, last }) => {
          const marks = (c?.ledger || []).filter(x => x.hard && x.status !== 'unclear')
            .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status))
          return (
            <li key={p.symbol}>
              <button className="book-row" onClick={() => openCompany(p.symbol)}>
                <div className="book-name">
                  <b>{p.short || shortName(p.name)}</b>
                  <span className="sub">{p.sector}</span>
                </div>
                <div className="book-px">
                  {last && <><span className="num">{last.close.toLocaleString('en-IN')}</span> <span className={`num ${tone(last.chg)}`}>{pct(last.chg)}</span></>}
                </div>
                <div className="book-word">
                  <span className="marks">
                    {marks.slice(0, 12).map((m, i) => <Mark key={m.id} status={m.status} size={16} delay={i * 50} />)}
                    {marks.length > 12 && <span className="sub more">+{marks.length - 12}</span>}
                  </span>
                  <span className="sub">{c === undefined ? '' : marks.length ? summary(marks.map(m => m.status)) : 'No checkable promises'}</span>
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </main>
  )
}
const ORDER: Status[] = ['missed', 'quiet', 'partly', 'kept', 'pending', 'unclear']
const WORDS: Partial<Record<Status, string>> = { kept: 'kept', partly: 'partly kept', missed: 'missed', quiet: 'gone quiet', pending: 'not due' }
const WITH: Partial<Record<Status, string>> = { kept: 'a promise kept', partly: 'a promise partly kept', missed: 'a promise missed', quiet: 'a promise gone quiet', pending: 'a promise not yet due' }
const summary = (ss: Status[]) => (['missed', 'quiet', 'partly', 'kept', 'pending'] as Status[])
  .map(st => [st, ss.filter(x => x === st).length] as const).filter(([, n]) => n).map(([st, n]) => `${n} ${WORDS[st]}`).join(', ')

// Across the whole book: how many promises management teams have kept, missed or let go quiet.
// Tap a count to see only the companies behind it; tap again for the whole book.
function BookTally({ cos, only, setOnly }: { cos: (Company | null)[]; only: Status | null; setOnly: (s: Status | null) => void }) {
  const all = cos.flatMap(c => (c?.ledger || []).filter(p => p.hard))
  if (!all.length) return null
  const n = (st: Status) => all.filter(p => p.status === st).length
  const teams = (st: Status) => cos.filter(c => c?.ledger.some(p => p.hard && p.status === st)).length
  const items: [Status, string][] = [['missed', `missed, at ${teams('missed')} companies`], ['quiet', 'gone quiet'], ['partly', 'partly kept'], ['kept', 'kept'], ['pending', 'not due yet']]
  return (
    <section className="book-tally" aria-label="Promises across your book">
      <p className="sub">Promises across your book</p>
      <ul className="tally">
        {items.map(([st, label]) => n(st) ? (
          <li key={st}>
            <button className={`tally-btn${only === st ? ' on' : ''}`} aria-pressed={only === st} onClick={() => setOnly(only === st ? null : st)}>
              <Mark status={st} size={18} /><b className="num">{n(st)}</b> <span>{label}</span>
            </button>
          </li>
        ) : null)}
      </ul>
    </section>
  )
}
