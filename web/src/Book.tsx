import { type ReactNode, useEffect, useState } from 'react'
import { cachedCompany, deadline, getCompany, rupees, shortName, wordScore, type Company, type Promise_, type Push, type Status } from './lib'
import { Roll } from './items'
import { Masthead, StatusLabel, useKept } from './ui'

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
  const head = (tally?: ReactNode) => <>
    <Masthead />
    <header className="page-head">
      <h1 className="title">Your book</h1>
      <p className="sub">{push.portfolio.length} holdings, weakest word first. Promises from each company’s last earnings calls, checked against filed results.</p>
    </header>
    {tally}
  </>
  // Order and tally only once every holding is in, so counts don't climb and rows don't reshuffle
  if (push.portfolio.some(p => cos[p.symbol] === undefined)) {
    return <main className="screen book" aria-busy="true">{head(slow ? <div className="skel skel-block" /> : null)}</main>
  }

  const rows = push.portfolio.map(p => ({ p, c: cos[p.symbol], score: wordScore(cos[p.symbol] || undefined) }))
  const missed = (c?: Company | null) => c ? c.ledger.filter(x => x.hard && x.status === 'missed').length : 0
  // Kept share with one kept and one not added, so 0 of 1 doesn't outrank 1 of 7
  const share = (s: ReturnType<typeof wordScore>) => s?.graded ? (s.kept + 1) / (s.graded + 2) : 2
  rows.sort((a, b) => share(a.score) - share(b.score) || missed(b.c) - missed(a.c) || (b.score?.graded ?? 0) - (a.score?.graded ?? 0))
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
  const items: [Status, string][] = [['missed', 'missed'], ['quiet', 'gone quiet'], ['kept', 'kept'], ['pending', 'not due yet']]
  return (
    <section className="tally" aria-label="Promises across your book">
      <ul>
        {items.map(([st, word]) => (
          <li key={st}>
            <button className={`tally-b t-${st}`} aria-pressed={only === st} onClick={() => setOnly(only === st ? null : st)}>
              <span className="tally-n num"><Roll to={n(st)} /></span>
              <span className="tally-w">{word}</span>
              <span className="small">at {teams(st)} {teams(st) === 1 ? 'company' : 'companies'}</span>
            </button>
          </li>
        ))}
      </ul>
      {n('partly') > 0 && <button className={`text-btn tally-partly${only === 'partly' ? ' on' : ''}`} aria-pressed={only === 'partly'} onClick={() => setOnly(only === 'partly' ? null : 'partly')}>And {n('partly')} partly kept</button>}
    </section>
  )
}
