// The reader: the brief one item at a time. Read it, then keep it for later or clear it, and the next slides in.
// It ends on 'You're up to date'.
import { useEffect, useMemo, useRef, useState } from 'react'
import { act, newsQuestion, notesKey, remaining, type Brief, type Done, type Item } from './queue'
import { cr, getCompany, rupees, wordScore, when, type Company, type Lines, type Push } from './lib'
import { Answer, suggestions, useKnown } from './Ask'
import { Arrow, NotesList, crossedText, itemLine, itemTitle, withLine } from './Brief'
import { PeopleBlock, ResultsBlock, moveWhy, shortDay, tidySubject, useWord } from './items'
import { Chart, Src, StatusLabel } from './ui'
import { BeforeAfter, said } from './Word'
import { promiseLine, verdictText } from './Trail'
import { pace, yearToDate } from './question'

type Page = { kind: 'item'; item: Item } | { kind: 'notes' } | { kind: 'done' }

export function Reader({ push, brief, done, setDone, lines, names, start, close, openCompany, openLines }: {
  push: Push; brief: Brief; done: Done; setDone: (d: Done) => void; lines: Lines; names: Record<string, string>
  start?: string; close: () => void; openCompany: (s: string, pid?: number) => void; openLines: () => void
}) {
  // The queue is fixed when the reader opens, so clearing doesn't reshuffle what's ahead
  const [pages] = useState<Page[]>(() => {
    const left = remaining(brief, done)
    const opened = start ? brief.items.find(i => i.key === start) : undefined
    const items = opened && !left.items.includes(opened) ? [opened, ...left.items] : left.items
    const at = opened ? items.indexOf(opened) : 0
    const ordered = [...items.slice(at), ...items.slice(0, at)]
    return [...ordered.map(item => ({ kind: 'item' as const, item })), ...(left.notesLeft ? [{ kind: 'notes' as const }] : []), { kind: 'done' as const }]
  })
  const [at, setAt] = useState(0)
  const [leaving, setLeaving] = useState<'' | 'left' | 'right'>('')
  const page = pages[at]
  // Counted the way the brief counts them: the items to read, not the closing page of one-liners
  const segs = pages.filter(x => x.kind === 'item').length
  const scroller = useRef<HTMLDivElement>(null)
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches

  const advance = (how: 'clear' | 'keep', dir: 'left' | 'right') => {
    if (page.kind === 'item') setDone(act(done, page.item.key, how))
    if (page.kind === 'notes') setDone({ ...done, notes: [...done.notes, notesKey(brief.notes, brief.spill)] })
    if (still) { setAt(a => a + 1); return }
    setLeaving(dir)
    setTimeout(() => { setLeaving(''); setAt(a => a + 1); scroller.current?.scrollTo(0, 0) }, 180)
  }
  // Once the company's name has scrolled up out of view, the bar carries it in place of the progress segments
  const [named, setNamed] = useState(false)
  useEffect(() => { scroller.current?.scrollTo(0, 0); setNamed(false) }, [at])
  const onScroll = () => {
    const el = scroller.current, t = el?.querySelector('.r-page h1')
    setNamed(!!el && !!t && t.getBoundingClientRect().bottom < el.getBoundingClientRect().top)
  }
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    addEventListener('keydown', k); return () => removeEventListener('keydown', k)
  }, [close])

  // Swipe left to clear, right to keep. Vertical drags scroll as normal.
  const drag = useRef<{ x: number; y: number; dx: number; on: boolean } | null>(null)
  const [dx, setDx] = useState(0)
  const onDown = (e: React.PointerEvent) => { if (page.kind === 'done' || e.pointerType === 'mouse') return; drag.current = { x: e.clientX, y: e.clientY, dx: 0, on: false } }
  const onMove = (e: React.PointerEvent) => {
    const d = drag.current; if (!d) return
    const x = e.clientX - d.x, y = e.clientY - d.y
    if (!d.on) { if (Math.abs(y) > 10 && Math.abs(y) > Math.abs(x)) { drag.current = null; return } if (Math.abs(x) < 12) return; d.on = true }
    d.dx = x; setDx(x)
  }
  const onUp = () => {
    const d = drag.current; drag.current = null; setDx(0)
    if (!d?.on) return
    if (d.dx < -90) advance('clear', 'left')
    else if (d.dx > 90 && page.kind === 'item') advance('keep', 'right')
  }

  return (
    <div className="reader" role="dialog" aria-modal="true" aria-label="The brief">
      <header className={`r-top${named ? ' r-top-named' : ''}`} style={named ? { '--read': (at + 1) / segs } as React.CSSProperties : undefined}>
        {/* At the end the one way out is the button under the words; a close mark beside it would say the same */}
        {page.kind !== 'done' && <button className="icon-btn" onClick={close} aria-label="Close the brief"><svg viewBox="0 0 20 20" aria-hidden><path d="M5 5l10 10M15 5L5 15" /></svg></button>}
        {page.kind === 'item' && named ? <span className="r-name" aria-hidden>{names[page.item.symbol]}</span>
          : page.kind !== 'done' && <div className="progress r-progress" aria-hidden>{Array.from({ length: segs }, (_, k) => <span key={k} className={k < at ? 'on' : k === at ? 'now' : ''} />)}</div>}
        <span className="small r-count" aria-live="polite">{page.kind === 'item' ? `${at + 1} of ${segs}` : page.kind === 'notes' ? 'The rest' : ''}</span>
      </header>
      <div className="r-scroll" ref={scroller} onScroll={onScroll}>
        <article key={at} className={`r-page${leaving ? ` out-${leaving}` : ''}`} style={dx ? { transform: `translateX(${dx}px) rotate(${dx / 60}deg)`, transition: 'none' } : undefined}
          onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
          {page.kind === 'item' && <ItemPage i={page.item} push={push} lines={lines} names={names} openCompany={openCompany} openLines={openLines} />}
          {page.kind === 'notes' && <><p className="small kicker">The rest of the window</p><h1 className="title">Worth a line</h1><p className="lede">{brief.spill.length ? `${brief.spill.length} more crossed your lines; the rest didn’t.` : 'None of it crossed your lines.'} One line each.</p><NotesList brief={brief} names={names} asof={push.asof} /></>}
          {page.kind === 'done' && <DonePage brief={brief} push={push} done={done} names={names} close={close} openCompany={openCompany} />}
        </article>
      </div>
      {page.kind === 'item' && !done.cleared.length && !done.kept.length && <p className="small r-first">Keep it for later, or mark it done. Swiping works too.</p>}
      {page.kind !== 'done' && (
        <footer className="r-acts">
          {page.kind === 'item' && <button className="btn btn-line" onClick={() => advance('keep', 'right')}>Keep for later</button>}
          <button className="btn" onClick={() => advance('clear', 'left')}>{page.kind === 'notes' ? 'Mark all read' : 'Done'}</button>
        </footer>
      )}
      {dx !== 0 && <p className={`r-hint ${dx < 0 ? 'l' : 'r'}`} aria-hidden>{dx < 0 ? 'Done' : 'Keep'}</p>}
    </div>
  )
}

function ItemPage({ i, push, lines, names, openCompany, openLines }: { i: Item; push: Push; lines: Lines; names: Record<string, string>; openCompany: (s: string, pid?: number) => void; openLines: () => void }) {
  const name = names[i.symbol]
  const m = i.move
  // A move on results: the results that explain it, from the filing that carries the numbers
  const f = i.story?.lead ?? (m?.explainedBy?.category === 'results'
    ? push.filings.filter(x => x.symbol === i.symbol && x.results && x.at.slice(0, 10) <= m.d).sort((a, b) => b.at.localeCompare(a.at))[0] ?? m.explainedBy
    : undefined)
  const bars = m?.series ?? (push.eod[i.symbol] || []).filter(b => b.d <= i.at.slice(0, 10)).slice(-30)
  // The quarter is in the table's caption; the kicker says only what and when
  const kind = i.kind === 'results' ? 'Results' : i.kind === 'people' ? 'Management change' : i.kind === 'move' ? 'Unusual day' : 'Filing'
  const others = i.story?.filings.filter(x => x !== f) || []
  return <>
    <p className="small kicker">{kind}, {i.kind === 'move' ? shortDay(m!.d) : when(i.at, push.asof).replace(/^Yesterday/, 'yesterday')}</p>
    <h1 className="title"><button className="title-link" onClick={() => openCompany(i.symbol)}>{name}</button></h1>
    {/* Results open on the table: the numbers are the news. Their word follows it, the period named before the verdict */}
    {!f?.results && i.kind !== 'move' && i.kind !== 'people' && <p className="lede">{itemLine(i)}</p>}
    {/* A move on results day is here for the move: it opens the item, then the numbers behind it */}
    {m && f?.results && <p className="r-move-line"><b className={m.chg >= 0 ? 'up' : 'down'}>{m.chg >= 0 ? '+' : '−'}{Math.abs(m.chg).toFixed(1)}%</b> on the day, on {m.volX.toFixed(1)}× its 20‑day volume. Closed at ₹{m.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}.</p>}
    {/* A CEO, CFO or MD change on results day is said before the numbers; its detail follows them */}
    {f?.results && i.with?.lead.people?.some(p => p.seniority === 'top') && <p className="lede r-with">{withLine(i.with)}</p>}
    {f?.results && <><ResultsBlock f={f} />
      {i.with?.lead.people?.length ? <section className="r-sec" aria-label="Management change"><h2 className="head">Also that day</h2><PeopleBlock f={i.with.lead} all={push.filings} /></section> : null}
      <Held i={i} name={name} res={f.results} openCompany={openCompany} /></>}
    {m && !f?.results && (
      <div className="r-move">
        <span className={`fig fig-m ${m.chg >= 0 ? 'up' : 'down'}`}>{m.chg >= 0 ? '+' : '−'}{Math.abs(m.chg).toFixed(1)}<span className="fig-pc">%</span></span>
        <span className="small">{m.volX.toFixed(1)}× its 20‑day volume<br />Closed at ₹{m.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
      </div>)}
    {bars.length > 1 && i.kind !== 'people' && <figure className="r-chart"><Chart series={bars} h={f?.results ? 56 : 88} /><figcaption className="small">Last {bars.length} sessions</figcaption></figure>}
    {i.kind === 'move' && <p className="lede r-why">{moveWhy(m!)}</p>}
    {f?.people?.length ? <PeopleBlock f={f} all={push.filings} /> : null}
    {f && !f.results && f.amount_cr != null && f.amount_cr >= 1 && <p className="r-size"><span className="fig fig-s">₹{cr(f.amount_cr)}<span className="fig-pc"> cr</span></span>{f.pct_rev != null && <span className="small">{f.pct_rev < 0.1 ? 'Under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`} of a year’s revenue</span>}</p>}
    <p className="crossed"><span>{crossedText(i, lines)}.</span> <button className="link-inline" onClick={openLines}>Change</button></p>

    {!f?.results && <Held i={i} name={name} openCompany={openCompany} />}
    {/* Ask's questions are about promises and numbers; beside a management change they'd be off topic */}
    {i.kind !== 'people' && <AskHere push={push} symbol={i.symbol} name={name} openCompany={openCompany} />}

    <ul className="srcs small">
      {f?.results?.source?.xbrl && <li><Src href={f.results.source.xbrl}>Exchange XBRL</Src></li>}
      {/\.pdf$/i.test(f?.results?.source?.pdf || '') && <li><Src href={f!.results!.source.pdf}>Results PDF</Src></li>}
      {f && <li><Src href={f.url}>The filing</Src></li>}
      {i.with && <li><Src href={i.with.lead.url}>{tidySubject(i.with.lead.subject)}</Src></li>}
      {m?.explainedBy && m.explainedBy !== f && <li><Src href={m.explainedBy.url}>{tidySubject(m.explainedBy.subject)}</Src></li>}
      {others.slice(0, 4).map((o, k) => <li key={k}><Src href={o.url}>{tidySubject(o.subject)}</Src></li>)}
    </ul>
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
  const now = guide && ytd && ytd.fy === guide.fy && guide.g.metric === 'revenue_growth' && /revenue/i.test(guide.g.target)
    ? `${ytd.label} revenue ${ytd.growth >= 0 ? 'grew' : 'fell'} ${Math.abs(ytd.growth).toFixed(1)}% on a year ago. ` : ''
  const sofar = guide && ytd && ytd.fy === guide.fy ? pace(guide.g, ytd.growth) : null
  const record = s?.graded ? `${name} has kept ${Math.floor(s.kept)} of ${s.graded} promises that came due.` : s?.hard ? `None of ${name}’s dated promises is due yet.` : `No promise from ${name} with a number and a date yet.`
  return (
    <section className="r-sec" aria-label="Against their word">
      <h2 className="head">Against their word</h2>
      {guide && <div className="r-guide">
        <p className="lede">Guided for {guide.fy}: {rupees(guide.g.target).replace(new RegExp(`\\s+(in|by|for)\\s+${guide.fy}\\b`, 'i'), '')}. {sofar ? <span className="st st-pace">{sofar[0].toUpperCase() + sofar.slice(1)} so far</span> : <StatusLabel status="pending" />}</p>
        <p className="small">{now}Said on the {said(guide.g)} call.</p>
      </div>}
      {p && (p.status !== 'pending' && verdictText(p) ? <>
        <p className="lede r-verdict">{verdictText(p).replace(/\.?$/, '.')} <StatusLabel status={p.status} /></p>
        <p className="small r-promised">Their {said(p)} promise: {promiseLine(p).replace(/^./, c => c.toLowerCase())}.</p>
      </> : <p className="lede r-verdict">Promised {said(p)}: {promiseLine(p).replace(/^./, c => c.toLowerCase())}. <StatusLabel status={p.status} /></p>)}
      {p ? <BeforeAfter p={p} compact bare /> : null}
      <p className="r-record">{record}</p>
      <button className="link" onClick={() => openCompany(i.symbol, p?.id)}>Their record<Arrow /></button>
    </section>
  )
}

// Ask, in place: the questions this company's ledger can answer, answered here
export function AskHere({ push, symbol, name, openCompany, cls }: { push: Push; symbol: string; name: string; openCompany: (s: string, pid?: number) => void; cls?: string }) {
  const { known, names } = useKnown(push)
  const [c, setC] = useState<Company | null>(null)
  const [q, setQ] = useState('')
  useEffect(() => { getCompany(symbol).then(setC).catch(() => setC(null)) }, [symbol])
  const qs = useMemo(() => suggestions(c, name), [c, name])
  if (!qs.length) return null
  return (
    <section className={cls || 'r-sec'} aria-label={`Ask about ${name}`}>
      <h2 className="head">Ask FINN</h2>
      <div className="asks">{qs.map(x => <button key={x} className={`ask-chip${q === x ? ' on' : ''}`} aria-pressed={q === x} onClick={() => setQ(q === x ? '' : x)}>{x}</button>)}</div>
      {q && <Answer q={q} known={known} names={names} openCompany={openCompany} inline />}
    </section>
  )
}

// The end of the brief: the same tally the brief opened with, what was kept, and a question for each company's next call
function DonePage({ brief, push, done, names, close, openCompany }: { brief: Brief; push: Push; done: Done; names: Record<string, string>; close: () => void; openCompany: (s: string) => void }) {
  const kept = brief.items.filter(i => done.kept.includes(i.key))
  const read = brief.items.filter(i => done.cleared.includes(i.key)).length
  const worth = brief.notes.length + brief.spill.length
  const [qs, setQs] = useState<{ symbol: string; q: string }[]>([])
  // The news asks first (a CFO leaving, a margin that fell); the company's own question from its calls otherwise
  useEffect(() => {
    const first = new Map<string, Item>(); brief.items.forEach(i => { if (!first.has(i.symbol)) first.set(i.symbol, i) })
    Promise.all([...first.values()].slice(0, 3).map(i => {
      const q = newsQuestion(i, push)
      return q ? { symbol: i.symbol, q } : getCompany(i.symbol).then(c => c?.questions?.[0] ? { symbol: i.symbol, q: rupees(c.questions[0]) } : null).catch(() => null)
    })).then(xs => setQs(xs.filter((x): x is { symbol: string; q: string } => !!x)))
  }, [brief, push])
  const aside = [worth && `${worth} more worth a line`, brief.routine && `${brief.routine} routine ${brief.routine === 1 ? 'filing' : 'filings'} set aside`].filter(Boolean).join('; ')
  return (
    <div className="r-done">
      <h1 className="title done-t">You’re up to date</h1>
      <p className="lede">{read} of {brief.items.length} read{kept.length ? `, ${kept.length} kept for later` : ''}.{aside && ` ${aside[0].toUpperCase()}${aside.slice(1)}.`}</p>
      {kept.length > 0 && <>
        <h2 className="head">Kept for later</h2>
        <ul className="rows">{kept.map(i => <li key={i.key}><span className="row row-static">{itemTitle(i, names[i.symbol])}</span></li>)}</ul>
      </>}
      {qs.length > 0 && <>
        <h2 className="head">For the next call</h2>
        <ul className="rows done-qs">{qs.map(x => <li key={x.symbol}><button className="row" onClick={() => openCompany(x.symbol)}>
          <span><span className="done-co">{names[x.symbol]}</span>{x.q}</span><Arrow /></button></li>)}</ul>
        <CopyQs qs={qs.map(x => `${names[x.symbol]}: ${x.q}`)} />
      </>}
      <button className="btn btn-wide" onClick={close}>Back to the brief</button>
    </div>
  )
}

// For the call-prep notes: the questions as plain numbered text
function CopyQs({ qs }: { qs: string[] }) {
  const [copied, setCopied] = useState(false)
  if (!navigator.clipboard) return null
  const copy = () => navigator.clipboard.writeText(`For the next calls\n${qs.map((q, i) => `${i + 1}. ${q}`).join('\n')}`)
    .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return <button className="text-btn done-copy" onClick={copy} aria-live="polite">{copied ? 'Copied' : 'Copy the questions'}</button>
}
