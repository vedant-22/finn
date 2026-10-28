import { useEffect, useMemo, useRef, useState } from 'react'
import {
  CATEGORY_LABEL, cr, deadline, getCompany, pct, rupees, shortName, tone, triage, when,
  type Company, type Lines, type Move, type Push, type Story,
} from './lib'
import { Mark, Spark, Src, STATUS_WORD, useKept } from './ui'

const WINDOWS = [{ h: 24, label: '24h' }, { h: 72, label: '3 days' }, { h: 168, label: 'Week' }, { h: 720, label: 'Month' }]

export function Today({ push, lines, setLines, openCompany, openLines }: {
  push: Push; lines: Lines; setLines: (l: Lines) => void; openCompany: (s: string) => void; openLines: () => void
}) {
  const t = useMemo(() => triage(push, lines), [push, lines])
  const names = useMemo(() => Object.fromEntries(push.portfolio.map(p => [p.symbol, p.short || shortName(p.name)])), [push])
  const [showNotes, setShowNotes] = useKept('today.notes', false)
  const [showFold, setShowFold] = useKept('today.fold', false)
  const count = t.needs.length + t.moves.length
  const asof = new Date(push.asof)

  return (
    <main className="screen today">
      <header className="top">
        <div className="asof">
          {asof.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
          <span className="sub"> Filings to {asof.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()}</span>
        </div>
        <button className="pill" onClick={openLines}>Your lines</button>
      </header>

      <div className="window" role="radiogroup" aria-label="Time window">
        {WINDOWS.map(w => (
          <button key={w.h} role="radio" aria-checked={lines.hours === w.h} className={lines.hours === w.h ? 'on' : ''}
            onClick={() => setLines({ ...lines, hours: w.h })}>{w.label}</button>
        ))}
      </div>

      <section className="verdict" aria-live="polite">
        <div className="big">{count === 0 ? 'Nothing' : <Roll to={count} />}</div>
        <div className="big-label">
          {count === 0 ? 'needs you' : count === 1 ? 'thing needs you' : 'things need you'}
          <span className="sub"> out of {t.filings} filings across {push.portfolio.length} holdings</span>
        </div>
      </section>

      {count === 0 && <p className="sub empty-line">No filing or price move crossed your lines in this window. The rest is folded below.</p>}

      <ol className="needs">
        {t.needs.map(s => (
          <li key={s.key}><StoryCard s={s} name={names[s.symbol]} asof={push.asof} openCompany={openCompany} /></li>
        ))}
        {t.moves.map(m => (
          <li key={m.symbol + m.d}><MoveCard m={m} name={names[m.symbol]} lines={lines} openCompany={openCompany} /></li>
        ))}
      </ol>

      {t.notes.length > 0 && (
        <section className="fold-group">
          <button className="fold-head" aria-expanded={showNotes} onClick={() => setShowNotes(!showNotes)}>
            <span>{t.notes.length} worth a line</span><span className="chev" aria-hidden>{showNotes ? '–' : '+'}</span>
          </button>
          {showNotes && (
            <ul className="notes">
              {t.notes.map(s => <NoteRow key={s.key} s={s} name={names[s.symbol]} asof={push.asof} />)}
            </ul>
          )}
        </section>
      )}

      {t.folded.length > 0 && (
        <section className="fold-group">
          <button className="fold-head quiet" aria-expanded={showFold} onClick={() => setShowFold(!showFold)}>
            <span>{t.folded.reduce((n, s) => n + s.filings.length, 0)} routine filings, folded</span>
            <span className="chev" aria-hidden>{showFold ? '–' : '+'}</span>
          </button>
          {showFold && <FoldSummary stories={t.folded} names={names} />}
        </section>
      )}
    </main>
  )
}

function StoryCard({ s, name, asof, openCompany }: { s: Story; name: string; asof: string; openCompany: (s: string) => void }) {
  const f = s.lead
  const [rel, setRel] = useState(false)
  const others = s.filings.filter(x => x !== f)
  return (
    <article className={`card story cat-${s.category}`}>
      <header className="card-head">
        <button className="co" onClick={() => openCompany(s.symbol)}>{name}</button>
        <span className="meta">{CATEGORY_LABEL[s.category] || s.category}, {when(s.at, asof)}</span>
      </header>
      {f.results ? <ResultsBlock f={f} symbol={s.symbol} openCompany={openCompany} />
        : f.people?.length ? <PeopleBlock f={f} />
          : <p className="line">{f.line || tidySubject(f.subject)}{f.pct_rev != null && <span className="size"> {sizeWords(f)}</span>}</p>}
      <footer className="card-foot">
        <Src href={f.url}>Filing</Src>
        {others.length > 0 && <button className="src rel-toggle" aria-expanded={rel} onClick={() => setRel(!rel)}>
          {rel ? 'Hide' : 'and'} {others.length} related</button>}
      </footer>
      {rel && <ul className="related">{others.map((o, i) =>
        <li key={i}><Src href={o.url}>{tidySubject(o.subject)}</Src> <span className="sub">{when(o.at, asof)}</span></li>)}</ul>}
    </article>
  )
}

function sizeWords(f: { amount_cr?: number; pct_rev?: number }) {
  if (f.amount_cr == null || f.pct_rev == null) return ''
  const p = f.pct_rev < 0.1 ? 'under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`
  return `₹${cr(f.amount_cr)} cr, ${p} of a year's revenue.`
}

export function tidySubject(s: string) {
  return s.replace(/^.*? has (informed|submitted to) the Exchange( about| regarding)?[,\s]*(the\s+)?/i, '')
    .replace(/^'(.*)'\.?$/, '$1').replace(/^a press release dated .*?, titled\s*"?(.*?)"?\.?$/i, 'Press release: $1').replace(/\.-\s*/g, ' - ').replace(/\s{2,}/g, ' ').replace(/^./, c => c.toUpperCase())
}

function ResultsBlock({ f, symbol, openCompany }: { f: any; symbol: string; openCompany: (s: string) => void }) {
  const r = f.results
  const [co, setCo] = useState<Company | null>(null)
  useEffect(() => { getCompany(symbol).then(setCo) }, [symbol])
  // Promises about the headline numbers, to set the quarter against.
  const word = (co?.ledger || []).filter(p => p.hard && ['margin', 'revenue_growth', 'profit', 'volume'].includes(p.metric) && p.status !== 'unclear').slice(0, 2)
  return (
    <div className="results">
      <table className="figs">
        <caption>{r.quarter}, {r.basis}, ₹ crore</caption>
        <thead><tr><th /><th>Quarter</th><th>vs {r.compare.prev?.split(' ')[0] || 'prev'}</th><th>vs {r.compare.yago || 'year ago'}</th></tr></thead>
        <tbody>
          {r.lines.map((l: any) => (
            <tr key={l.key}>
              <th scope="row">{l.label}</th>
              <td className="num">{cr(l.value)}</td>
              <td className={`num ${tone(l.qoq)}`}>{pct(l.qoq)}</td>
              <td className={`num ${tone(l.yoy)}`}>{pct(l.yoy)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {r.ebitda_margin != null && (
        <p className="margin-line">EBITDA margin <b className="num">{r.ebitda_margin}%</b>
          <span className="sub">, from {r.prev_margin}% last quarter and {r.yago_margin}% a year ago</span></p>
      )}
      {r.one_offs?.length > 0 && (
        <p className="one-off sub">{r.one_offs.map((o: any) => `${o.q === r.quarter ? "This quarter's" : o.q} profit includes ${[o.tax_credit && `a ₹${cr(o.tax_credit)} cr tax credit`, o.exceptional && `₹${cr(Math.abs(o.exceptional))} cr of exceptional items`].filter(Boolean).join(' and ')}.`).join(' ')}</p>
      )}
      {word.length > 0 && (
        <div className="against">
          <h4>Against what they said</h4>
          {word.map((p, i) => (
            <button key={p.id} className="word-row" onClick={() => openCompany(symbol)}>
              <Mark status={p.status} delay={i * 80} />
              <span><b>{rupees(p.target.charAt(0).toUpperCase() + p.target.slice(1))}</b> <span className="sub">{[deadline(p), STATUS_WORD[p.status]].filter(Boolean).join('. ')}.</span></span>
            </button>
          ))}
        </div>
      )}
      <p className="src-line"><Src href={r.source.xbrl}>Exchange XBRL</Src>{/\.pdf$/i.test(r.source.pdf || '') && <> <Src href={r.source.pdf}>Results PDF</Src></>}
</p>
    </div>
  )
}

function PeopleBlock({ f }: { f: any }) {
  const order = { top: 0, board: 1, senior: 2, other: 3 } as Record<string, number>
  const ppl = [...f.people].sort((a: any, b: any) => (+reclass(a) - +reclass(b)) || (order[a.seniority] - order[b.seniority]) || (a.action === 'appointed' ? -1 : 1))
  return (
    <ul className="people">
      {ppl.slice(0, 3).map((p: any, i: number) => {
        const joining = ['appointed', 're-appointed', 'redesignated'].includes(p.action)
        const moved = reclass(p)
        return (
          <li key={i} className={joining || moved ? 'in' : 'out'}>
            <div className="who"><b>{p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')}</b>
              <span className="role">{moved ? `Stays ${p.role}, off the senior management list` : `${verb(p.action)} ${p.role}`}{/\d/.test(p.effective || '') ? `, from ${p.effective.replace(/(\d+)(st|nd|rd|th)/, '$1')}` : ''}</span></div>
            {joining && p.background && !/not stated|not provided|^$|^designated as|^.{0,60}\bhas (assumed|been appointed)/i.test(p.background) && <p className="bio">{p.background}</p>}
            {joining && p.previous?.length > 0 && <p className="prev">{p.previous.join('; ')}</p>}
            {!joining && !moved && p.reason && !/not stated|^leaving the company\.?$|no other material reason/i.test(p.reason) && <p className="bio">Reason given: {p.reason}</p>}
          </li>
        )
      })}
    </ul>
  )
}
// 'Changed from SMP to Non-SMP category': same job, just no longer reported as senior management
const reclass = (p: any) => p.action === 'ceased' && /non[- ]?smp|non[- ]senior management/i.test(p.reason || '')
const verb = (a: string) => ({ appointed: 'Joins as', resigned: 'Resigns as', retired: 'Retires as', ceased: 'Leaves as', redesignated: 'Now', 're-appointed': 'Re-appointed', died: 'Died,' } as any)[a] || a

function MoveCard({ m, name, lines, openCompany }: { m: Move; name: string; lines: Lines; openCompany: (s: string) => void }) {
  const d = new Date(m.d + 'T12:00:00').toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
  return (
    <article className="card move">
      <header className="card-head">
        <button className="co" onClick={() => openCompany(m.symbol)}>{name}</button>
        <span className="meta">Unusual day, {d}</span>
      </header>
      <div className="move-body">
        <div>
          <div className={`move-chg num ${tone(m.chg)}`}>{pct(m.chg)}</div>
          <div className="move-vol"><span className={m.why.includes('volume') ? 'hit num' : 'num'}>{m.volX.toFixed(1)}×</span> its 20-day volume</div>
        </div>
        <Spark series={m.series} />
      </div>
      <p className="line">{m.explainedBy
        ? m.explainedBy.category === 'results'
          ? <>{m.explainedBy.at.slice(0, 10) === m.d ? 'Results came out that day.' : 'Results came out after the previous close.'}</>
          : <>After: {(m.explainedBy.line || tidySubject(m.explainedBy.subject)).replace(/\.$/, '')}.</>
        : <>No filing explains it.</>}</p>
      <footer className="card-foot"><span className="sub">Your line: {m.why.includes('volume') ? `${lines.volX}× volume` : `±${lines.movePct}% move`}</span></footer>
    </article>
  )
}

function NoteRow({ s, name, asof }: { s: Story; name: string; asof: string }) {
  const f = s.lead
  const text = f.people?.length
    ? f.people.map((p: any) => `${p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')} ${verb(p.action).toLowerCase()} ${p.role}`).join('; ')
    : f.line || tidySubject(f.subject)
  return (
    <li>
      <a href={f.url} target="_blank" rel="noopener noreferrer">
        <span className="note-co">{name}</span>
        <span className="note-text">{text}{f.pct_rev != null && <span className="sub"> {sizeWords(f)}</span>}</span>
        <span className="note-when">{when(s.at, asof)}</span>
      </a>
    </li>
  )
}

function FoldSummary({ stories, names }: { stories: Story[]; names: Record<string, string> }) {
  const byDesc = new Map<string, { n: number; cos: Set<string> }>()
  for (const s of stories) for (const f of s.filings) {
    const k = f.desc.replace(/ under SEBI.*$/, '').replace(/\/Con\. Call Updates/, '')
    const e = byDesc.get(k) || { n: 0, cos: new Set() }
    e.n++; e.cos.add(names[f.symbol]); byDesc.set(k, e)
  }
  return (
    <ul className="folded">
      {[...byDesc.entries()].sort((a, b) => b[1].n - a[1].n).map(([k, v]) => (
        <li key={k}><span className="num">{v.n}</span> <span>{k}</span> <span className="sub">{[...v.cos].slice(0, 3).join(', ')}{v.cos.size > 3 ? ` and ${v.cos.size - 3} more` : ''}</span></li>
      ))}
    </ul>
  )
}

// The headline number rolls from the last window's count to this one, so switching windows reads as a change.
function Roll({ to }: { to: number }) {
  const [n, setN] = useState(to)
  const from = useRef(to)
  useEffect(() => {
    const a = from.current; from.current = to
    if (a === to || matchMedia('(prefers-reduced-motion: reduce)').matches) { setN(to); return }
    const t0 = performance.now(); let raf = 0
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 320)
      setN(Math.round(a + (to - a) * (1 - (1 - k) ** 3)))
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [to])
  return <>{n}</>
}
