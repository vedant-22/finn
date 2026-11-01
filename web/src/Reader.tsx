// An item's full view: the card it opened from, grown into a page. Back shrinks it into the card again.
import { useEffect, useMemo, useRef, useState } from 'react'
import { type Brief, type Item } from './queue'
import { cr, getCompany, rupees, wordScore, type Company, type Lines, type Push } from './lib'
import { Answer, suggestions, useKnown } from './Ask'
import { PriceLine, alertFig, cardSentence, crossedText, figWhen, kindLabel } from './Brief'
import { PeopleBlock, ResultsBlock, shortDay, tidySubject, useWord } from './items'
import { Outcome, Src, StatusLabel } from './ui'
import { BeforeAfter, said } from './Word'
import { promiseLine, verdictText } from './Trail'
import { pace, yearToDate } from './question'

export function ItemView({ push, brief, k, lines, names, close, openCompany, openLines }: {
  push: Push; brief: Brief; k: string; lines: Lines; names: Record<string, string>
  close: () => void; openCompany: (s: string, pid?: number) => void; openLines: () => void
}) {
  const i = brief.items.find(x => x.key === k) ?? brief.spill.find(x => x.key === k)
  const scroller = useRef<HTMLDivElement>(null)
  // Once the name has scrolled up out of view, the bar carries it
  const [named, setNamed] = useState(false)
  const onScroll = () => {
    const el = scroller.current, t = el?.querySelector('.iv-top h1')
    setNamed(!!el && !!t && t.getBoundingClientRect().bottom < el.getBoundingClientRect().top + 56)
  }
  useEffect(() => {
    const on = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    addEventListener('keydown', on); return () => removeEventListener('keydown', on)
  }, [close])
  useEffect(() => { scroller.current?.focus({ preventScroll: true }) }, [])
  // The window changed under a deep link and the item is gone: say so, and go back
  if (!i) return (
    <div className="item-view" role="dialog" aria-modal="true" aria-label="Not in this window">
      <header className="bar iv-bar"><button className="back" onClick={close}>Back</button></header>
      <div className="iv-scroll"><div className="iv-page iv-gone"><h1 className="t-h1">Not in this window</h1><p className="serif-line">It may have moved to a wider window, or out of it.</p></div></div>
    </div>)
  const name = names[i.symbol]
  return (
    <div className="item-view" role="dialog" aria-modal="true" aria-label={name}>
      <header className={`bar iv-bar${named ? ' past' : ''}`}>
        <button className="back" onClick={close}>Back</button>
        {named && <span className="bar-name">{name}</span>}
      </header>
      <div className="iv-scroll" ref={scroller} onScroll={onScroll} tabIndex={-1}>
        <article className="iv-page"><ItemPage i={i} push={push} lines={lines} name={name} openCompany={openCompany} openLines={openLines} /></article>
      </div>
    </div>
  )
}

function ItemPage({ i, push, lines, name, openCompany, openLines }: { i: Item; push: Push; lines: Lines; name: string; openCompany: (s: string, pid?: number) => void; openLines: () => void }) {
  const m = i.move
  // A move on results: the results that explain it, from the filing that carries the numbers
  const f = i.story?.lead ?? (m?.explainedBy?.category === 'results'
    ? push.filings.filter(x => x.symbol === i.symbol && x.results && x.at.slice(0, 10) <= m.d).sort((a, b) => b.at.localeCompare(a.at))[0] ?? m.explainedBy
    : undefined)
  const fig = alertFig(i, name, push)
  const bars = (push.eod[i.symbol] || []).filter(b => b.d <= (fig?.d ?? i.at.slice(0, 10))).slice(-30), line = bars.length > 4
  const others = i.story?.filings.filter(x => x !== f) || []
  const top = !!i.with?.lead.people?.some(p => p.seniority === 'top')
  const withPeople = i.with?.lead.people?.length
    ? <section className="iv-sec" aria-label="Management change"><h2 className="t-b1">{top ? 'Management change' : 'Also that day'}</h2><PeopleBlock f={i.with.lead} all={push.filings} /></section> : null
  // The sentence under the name is the card's, word for word, so it travels as one picture; where it closed goes with the lines
  const closed = m ? `Closed at ₹${m.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}. ` : ''
  const lede = cardSentence(i, fig)
  return <>
    {/* The card's own top, grown: the price line, what kind, the name, the day's move */}
    <div className="iv-top">
      {line && <PriceLine bars={bars} end={fig && <Outcome size="xxs" value={fig.v.replace('%', '')} unit="%" />} />}
      <div className="card-lbl"><span className="lbl">{kindLabel(i, push)}</span>{!fig && <span className="lbl lbl-quiet">{shortDay(i.at)}</span>}</div>
      <h1 className="t-h1 iv-name"><button onClick={() => openCompany(i.symbol)}>{name}</button></h1>
      {fig && (line
        ? m && <p className="card-cap">On {m.volX.toFixed(1)}× its usual volume</p>
        : <div className="card-fig"><Outcome size="xs" value={fig.v.replace('%', '')} unit="%" /><span className="card-cap">{figWhen(fig.d, i)}</span></div>)}
      {f && !f.results && f.amount_cr != null && f.amount_cr >= 1 && <div className="card-fig"><Outcome size="xs" value={`₹${cr(f.amount_cr)}`} unit="cr" />{f.pct_rev != null && <span className="card-cap">{f.pct_rev < 0.1 ? 'Under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`} of a year’s revenue</span>}</div>}
      <p className="card-desc iv-lede">{lede}</p>
      <p className="iv-line"><span>{closed}{crossedText(i, lines)}.</span> <button className="see" onClick={openLines}>Change</button></p>
    </div>

    {/* A CEO, CFO or MD leaving with the results leads the card, so it leads the view too; anyone else follows the table */}
    {f?.results && top && withPeople}
    {f?.results && <section className="iv-sec" aria-label="Results"><ResultsBlock f={f} /></section>}
    {f?.results && !top && withPeople}
    {f?.people?.length ? <section className="iv-sec" aria-label="Management change"><PeopleBlock f={f} all={push.filings} /></section> : null}
    <Held i={i} name={name} res={f?.results} openCompany={openCompany} />
    {/* Ask's questions are about promises and numbers; beside a management change they'd be off topic */}
    {i.kind !== 'people' && <AskHere push={push} symbol={i.symbol} name={name} openCompany={openCompany} />}

    <section className="iv-sec" aria-label="Sources">
      <h2 className="lbl lbl-quiet">Sources</h2>
      <ul className="srcs">
        {f?.results?.source?.xbrl && <li><Src href={f.results.source.xbrl}>Exchange XBRL</Src></li>}
        {/\.pdf$/i.test(f?.results?.source?.pdf || '') && <li><Src href={f!.results!.source.pdf}>Results PDF</Src></li>}
        {f && <li><Src href={f.url}>The filing</Src></li>}
        {i.with && <li><Src href={i.with.lead.url}>{tidySubject(i.with.lead.subject)}</Src></li>}
        {m?.explainedBy && m.explainedBy !== f && <li><Src href={m.explainedBy.url}>{tidySubject(m.explainedBy.subject)}</Src></li>}
        {others.slice(0, 4).map((o, k) => <li key={k}><Src href={o.url}>{tidySubject(o.subject)}</Src></li>)}
      </ul>
    </section>
  </>
}

// Held against their word: for results, the promise this quarter answers to; otherwise their record in one line
// The guidance this quarter counts toward: a dated promise still running for this financial year, on revenue,
// margin or profit. Order books, loan books and multi-year plans are left to the company page
function guidance(c: Company | null, quarter?: string) {
  const fy = quarter?.match(/FY\d\d/)?.[0], rank = ['revenue_growth', 'margin', 'profit']
  if (!c || !fy) return undefined
  const g = (c.ledger || []).filter(p => p.hard && p.status === 'pending' && (p.by_when || '').includes(fy) && rank.includes(p.metric) && !/order|loan|book|inflow|cagr/i.test(p.target))
    .sort((a, b) => rank.indexOf(a.metric) - rank.indexOf(b.metric))[0]
  return g && { g, fy }
}

function Held({ i, name, res, openCompany }: { i: Item; name: string; res?: any; openCompany: (s: string, pid?: number) => void }) {
  const word = useWord(i.symbol)
  const [c, setC] = useState<Company | null>(null)
  useEffect(() => { getCompany(i.symbol).then(setC).catch(() => setC(null)) }, [i.symbol])
  const s = wordScore(c ?? undefined)
  const p = (i.kind === 'results' || i.move?.explainedBy?.category === 'results') ? word[0] : undefined
  if (!c) return null
  const guide = guidance(c, res?.quarter)
  // Revenue guidance sits next to this quarter's revenue growth; a segment margin or a return doesn't map onto the table
  // A year's guide is read against the year so far (Q1, H1, 9M), not one quarter
  const ytd = yearToDate(c.quarters || [])
  const sofar = guide && ytd && ytd.fy === guide.fy ? pace(guide.g, ytd.growth) : null
  // The status stays one of the four words (Not due); how the year is pacing is the evidence under it
  const where = sofar === 'ahead' ? 'above the range so far' : sofar === 'behind' ? 'below the range so far' : sofar ? 'inside the range so far' : ''
  const now = guide && ytd && ytd.fy === guide.fy && guide.g.metric === 'revenue_growth' && /revenue/i.test(guide.g.target)
    ? `${ytd.label} revenue ${ytd.growth >= 0 ? 'grew' : 'fell'} ${Math.abs(ytd.growth).toFixed(1)}% on a year ago${where ? `, ${where}` : ''}. ` : ''
  const record = s?.graded ? `${name} has kept ${Math.floor(s.kept)} of ${s.graded} promises that came due.` : s?.hard ? `None of ${name}’s dated promises is due yet.` : `No promise from ${name} with a number and a date yet.`
  return (
    <section className="iv-sec" aria-label="Against their word">
      <h2 className="t-b1">Against their word</h2>
      {/* One order everywhere: the status word, the promise, then what the filings showed and the page it was said on */}
      {guide && <div className="word-item">
        <StatusLabel status="pending" />
        <p className="word-p">{guide.fy} guide: {rupees(guide.g.target).replace(new RegExp(`\\s+(in|by|for)\\s+${guide.fy}\\b`, 'i'), '')}.</p>
        <p className="sub">{now}Said on the <Src href={`${guide.g.url}#page=${guide.g.page}`}>{said(guide.g)} call, page {guide.g.page}</Src>.</p>
      </div>}
      {p && <div className="word-item">
        <StatusLabel status={p.status} />
        <p className="word-p">{promiseLine(p)}.</p>
        {p.status !== 'pending' && verdictText(p) && <p className="sub">{verdictText(p).replace(/\.?$/, '.')}</p>}
        <BeforeAfter p={p} compact bare />
      </div>}
      <p className="word-record">{record}</p>
      <button className="see" onClick={() => openCompany(i.symbol, p?.id)}>Their record</button>
    </section>
  )
}

// Ask, in place: the questions this company's ledger can answer, answered here
export function AskHere({ push, symbol, name, openCompany, bare }: { push: Push; symbol: string; name: string; openCompany: (s: string, pid?: number) => void; bare?: boolean }) {
  const { known, names } = useKnown(push)
  const [c, setC] = useState<Company | null>(null)
  const [q, setQ] = useState('')
  useEffect(() => { getCompany(symbol).then(setC).catch(() => setC(null)) }, [symbol])
  const qs = useMemo(() => suggestions(c, name), [c, name])
  if (!qs.length) return null
  return (
    <section className={bare ? 'ask-here' : 'iv-sec ask-here'} aria-label={`Ask about ${name}`}>
      {!bare && <h2 className="t-b1">Ask FINN</h2>}
      <div className="asks">{qs.map(x => <button key={x} className={`ask-chip${q === x ? ' on' : ''}`} aria-pressed={q === x} onClick={() => setQ(q === x ? '' : x)}>{x}</button>)}</div>
      {q && <Answer q={q} known={known} names={names} openCompany={openCompany} inline />}
    </section>
  )
}
