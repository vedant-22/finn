import { type ReactNode, useEffect, useState } from 'react'
import { cachedCompany, dayMon, deadline, getCompany, pct, rupees, shortName, wordScore, type Company, type Promise_, type Push, type Status } from './lib'
import { Masthead, Outcome, StatusLabel, useKept } from './ui'

// The whole book, as v4 set it: a warm tally, then a tile for each holding, the most promises broken first
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
  const closeLabel = closeDay ? dayMon(new Date(closeDay + 'T12:00:00')) : ''
  // The top of the page is warm edge to edge, as the reference's outcomes page: title, line, tally
  const head = (tally?: ReactNode) => <>
    <Masthead warm />
    <div className="warm-top">
      <header className="page-top">
        <h1 className="t-h1">Your book</h1>
        <p className="serif-line">{push.portfolio.length} holdings, and how well each management team has kept its word. Prices at the {closeLabel} close.</p>
      </header>
      {tally}
    </div>
  </>
  // Order and tally only once every holding is in, so counts don't climb and rows don't reshuffle
  if (push.portfolio.some(p => cos[p.symbol] === undefined)) {
    return <main className="screen book">{head()}{slow && <div className="book-list skel-tiles" aria-busy="true">{[0, 1, 2, 3].map(k => <div key={k} className="skel skel-tile" />)}</div>}</main>
  }

  const rows = push.portfolio.map(p => {
    const c = cos[p.symbol]
    const bars = push.eod[p.symbol] || []
    return { p, c, score: wordScore(c || undefined), last: bars[bars.length - 1] }
  })
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
      {only && <p className="book-filter sub" aria-live="polite">{shown.length} with {WITH[only]} <button className="text-btn" onClick={() => setOnly(null)}>Show all</button></p>}
      {!only && <h2 className="sec-head book-head2">Weakest word first</h2>}
      <ul className="book-list">
        {shown.map(({ p, c, score, last }, i) => {
          const weak = weakest(c, only)
          const kept = score ? Math.floor(score.kept) : 0
          const pending = c ? c.ledger.filter(x => x.hard && x.status === 'pending').length : 0
          const lead = i === 0 && !only
          const rec = score?.graded
            ? <Outcome size="xs" value={kept} unit={`\u00a0of ${score.graded} kept`} />
            : pending ? <Outcome size="xs" value={pending} unit={'\u00a0not due'} /> : null
          const desc = <p className="card-desc">{weak ? weakLine(weak) : c && c.calls.length && c.calls.every(x => x.error) ? "The call transcripts couldn't be opened." : 'No promise with a number and a date yet.'}</p>
          const px = last && <p className="book-px"><span className="num">₹{last.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>, <span className="num">{pct(last.chg)}</span> on the day</p>
          return (
            <li key={p.symbol} className={lead ? 'wide' : undefined}>
              {lead
                // The lead's picture is its record, not its price: '1 of 7 kept' in the big figure, the price a quiet line under
                ? <button className="book-card lead" onClick={() => openCompany(p.symbol)}>
                    <div className="card-lbl"><span className="lbl lbl-quiet">{p.sector}</span>{weak && <StatusLabel status={weak.status} />}</div>
                    <span className="card-title">{p.short || shortName(p.name)}</span>
                    {score?.graded ? <span className="book-big"><Outcome size="s" value={kept} unit={`\u00a0of ${score.graded} kept`} /></span> : rec && <span className="book-rec">{rec}</span>}
                    {desc}{px}
                  </button>
                // In the grid, as the reference's news cards: status, name, record, the weakest promise. The price is on the lead and each company page
                : <button className="book-card tile-card" onClick={() => openCompany(p.symbol)}>
                    {weak ? <StatusLabel status={weak.status} /> : <span className="lbl lbl-quiet">Nothing graded</span>}
                    <span className="card-title">{p.short || shortName(p.name)}</span>
                    {rec && <span className="book-rec">{rec}</span>}
                    {desc}
                  </button>}
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
const weakLine = (p: Promise_) => `${cap(rupees(p.target))}${deadline(p) ? ` ${rupees(deadline(p))}` : ''}.`

// Across the whole book: how many promises management teams have kept, missed or let go quiet.
// Tap a count to see only the companies behind it; tap again for the whole book.
function BookTally({ cos, only, setOnly }: { cos: (Company | null | undefined)[]; only: Status | null; setOnly: (s: Status | null) => void }) {
  const all = cos.flatMap(c => (c?.ledger || []).filter(p => p.hard))
  if (!all.length) return null
  const n = (st: Status) => all.filter(p => p.status === st).length
  const teams = (st: Status) => cos.filter(c => c?.ledger.some(p => p.hard && p.status === st)).length
    // One row of four: the count in Inter, the status word under it in its colour. Partly kept rides under, still tappable
  const items: [Status, string][] = [['missed', 'Missed'], ['quiet', 'Gone quiet'], ['kept', 'Kept'], ['pending', 'Not due']]
  return (
    <section className="og-panel tally" aria-label="Promises across your book">
      <h2 className="lbl lbl-quiet">Promises across your book</h2>
      <ul className="tally-row">
        {items.map(([st, word]) => (
          <li key={st}>
            <button className="og-btn tally-b" aria-pressed={only === st} aria-label={`${n(st)} ${word.toLowerCase()}, at ${teams(st)} ${teams(st) === 1 ? 'company' : 'companies'}`} onClick={() => setOnly(only === st ? null : st)}>
              <Outcome size="xs" value={n(st)} />
              <span className={`lbl st-${st}`}>{word}</span>
            </button>
          </li>
        ))}
      </ul>
      {n('partly') > 0 && <button className={`og-link${only === 'partly' ? ' on' : ''}`} aria-pressed={only === 'partly'} onClick={() => setOnly(only === 'partly' ? null : 'partly')}>And {n('partly')} partly kept</button>}
    </section>
  )
}
