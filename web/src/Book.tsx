import { type ReactNode, useEffect, useState } from 'react'
import { cachedCompany, deadline, getCompany, rupees, shortName, wordScore, type Company, type Promise_, type Push, type Status } from './lib'
import { Roll } from './items'
import { Masthead, StatusLabel, useKept } from './ui'

// The whole book, ordered by how far management's word has held. Most broken first: that's where to look.
export function Book({ push, openCompany }: { push: Push; openCompany: (s: string) => void }) {
  // undefined: still loading; null: no file
  const [cos, setCos] = useState<Record<string, Company | null | undefined>>(() => Object.fromEntries(push.portfolio.map(p => [p.symbol, cachedCompany(p.symbol) ?? undefined])))
  const [only, setOnly] = useKept<Status | null>('book.only', null)
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    push.portfolio.forEach(p => getCompany(p.symbol).catch(() => null).then(c => setCos(prev => ({ ...prev, [p.symbol]: c }))))
    const t = setTimeout(() => setSlow(true), 400); return () => clearTimeout(t)
  }, [push])
  const head = (tally?: ReactNode) => <div className="band band-top">
    <Masthead />
    <header className="page-head">
      <h1 className="title">Your book</h1>
      <p className="sub">{push.portfolio.length} holdings, most promises missed or gone quiet first.</p>
    </header>
    {tally}
  </div>
  // Order and tally only once every holding is in, so counts don't climb and rows don't reshuffle
  if (push.portfolio.some(p => cos[p.symbol] === undefined)) {
    return <main className="screen book" aria-busy="true">{head(slow ? <div className="skel skel-block" /> : null)}</main>
  }

  const rows = push.portfolio.map(p => ({ p, c: cos[p.symbol], score: wordScore(cos[p.symbol] || undefined) }))
  const missed = (c?: Company | null) => c ? c.ledger.filter(x => x.hard && x.status === 'missed').length : 0
  // Most promises broken first (missed or gone quiet; partly kept counts half): Home First's 1 of 7 before Havells' 0 of 1.
  // Ties go to the lower share kept, then to more misses; nothing due yet comes last
  const broken = (s: ReturnType<typeof wordScore>) => s?.graded ? s.graded - s.kept : -1
  const share = (s: ReturnType<typeof wordScore>) => s?.graded ? s.kept / s.graded : 2
  rows.sort((a, b) => broken(b.score) - broken(a.score) || share(a.score) - share(b.score) || missed(b.c) - missed(a.c))
  const shown = only ? rows.filter(r => r.c?.ledger.some(x => x.hard && x.status === only)) : rows

  return (
    <main className="screen book">
      {head(<BookTally cos={Object.values(cos)} only={only} setOnly={setOnly} />)}
      <section className="sec">
        <h2 className="head" aria-live="polite">{only ? `${shown.length} with ${WITH[only]}` : 'Holdings'}{only && <button className="text-btn show-all" onClick={() => setOnly(null)}>Show all</button>}</h2>
        <ul className="rows">
          {shown.map(({ p, c, score }) => {
            const weak = weakest(c, only)
            const pending = c ? c.ledger.filter(x => x.hard && x.status === 'pending').length : 0
            const rec = score?.graded ? `${Math.floor(score.kept)} of ${score.graded} kept` : pending ? `${pending} not due` : ''
            const line = weak ? weakLine(weak) : c && c.calls.length && c.calls.every(x => x.error) ? 'The call transcripts couldn’t be opened.' : 'No promise with a number and a date yet.'
            return (
              <li key={p.symbol}>
                <button className="hold" onClick={() => openCompany(p.symbol)}>
                  <span className="hold-name">{p.short || shortName(p.name)}</span>
                  <span className="hold-rec num">{rec}</span>
                  <span className="hold-line">{weak && weak.status !== 'pending' && <StatusLabel status={weak.status} />} {line}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>
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
const weakLine = (p: Promise_) => `${cap(rupees(p.target))}${deadline(p) ? ` ${rupees(deadline(p))}` : ''}.`

// Across the whole book: how many promises management teams have kept, missed or let go quiet.
// Tap a count to see only the companies behind it; tap again for the whole book.
function BookTally({ cos, only, setOnly }: { cos: (Company | null | undefined)[]; only: Status | null; setOnly: (s: Status | null) => void }) {
  const all = cos.flatMap(c => (c?.ledger || []).filter(p => p.hard))
  if (!all.length) return null
  const n = (st: Status) => all.filter(p => p.status === st).length
  const teams = (st: Status) => cos.filter(c => c?.ledger.some(p => p.hard && p.status === st)).length
  // The promises that came due as one bar, in proportion; the counts under it filter the holdings
  const items: [Status, string][] = [['kept', 'kept'], ['partly', 'partly kept'], ['missed', 'missed'], ['quiet', 'gone quiet'], ['pending', 'not due']]
  const due = items.slice(0, 4).filter(([st]) => n(st) > 0)
  return (
    <section className="tally" aria-label="Promises across your book">
      <p className="small">{due.reduce((t, [st]) => t + n(st), 0)} promises have come due</p>
      <div className="tally-bar" aria-hidden>{due.map(([st]) => <span key={st} className={`t-${st}`} style={{ flexGrow: n(st) }} />)}</div>
      <ul>
        {items.filter(([st]) => n(st) > 0).map(([st, word]) => (
          <li key={st}>
            <button className={`tally-b t-${st}`} aria-pressed={only === st} aria-label={`${n(st)} ${word}, at ${teams(st)} ${teams(st) === 1 ? 'company' : 'companies'}`} onClick={() => setOnly(only === st ? null : st)}>
              <span className="tally-n num"><Roll to={n(st)} /></span>
              <span className="tally-w">{word}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
