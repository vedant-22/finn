import { useEffect, useState } from 'react'
import { getCompany, pct, shortName, tone, wordScore, type Company, type Push, type Status } from './lib'
import { Mark } from './ui'

// The whole book, ordered by how far management's word has held. Weakest first: that's where to look.
export function Book({ push, openCompany }: { push: Push; openCompany: (s: string) => void }) {
  const [cos, setCos] = useState<Record<string, Company | null>>({})
  useEffect(() => {
    push.portfolio.forEach(p => getCompany(p.symbol).then(c => setCos(prev => ({ ...prev, [p.symbol]: c }))))
  }, [push])

  const rows = push.portfolio.map(p => {
    const c = cos[p.symbol]
    const bars = push.eod[p.symbol] || []
    const last = bars[bars.length - 1]
    return { p, c, score: wordScore(c || undefined), last }
  })
  rows.sort((a, b) => (a.score?.ratio ?? 2) - (b.score?.ratio ?? 2) || (b.score?.graded ?? 0) - (a.score?.graded ?? 0))

  return (
    <main className="screen book">
      <header className="top"><h1>Your book</h1><span className="sub">{push.portfolio.length} holdings, weakest word first</span></header>
      <ul className="book-list">
        {rows.map(({ p, c, score, last }) => {
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
                    {marks.slice(0, 10).map((m, i) => <Mark key={m.id} status={m.status} size={16} delay={i * 50} />)}
                  </span>
                  <span className="sub">{c === undefined ? '' : !score || !score.graded
                    ? (marks.length ? `${marks.length} not due yet` : 'No checkable promises')
                    : `${fmtKept(score.kept)} of ${score.graded} kept`}</span>
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
const fmtKept = (k: number) => (Number.isInteger(k) ? String(k) : k.toFixed(1))
