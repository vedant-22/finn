// The reader: the brief one item at a time. Read it, then keep it for later or clear it, and the next slides in.
// It ends on 'You're up to date'.
import { useEffect, useMemo, useRef, useState } from 'react'
import { act, notesKey, remaining, type Brief, type Done, type Item } from './queue'
import { cr, getCompany, wordScore, when, type Company, type Lines, type Push } from './lib'
import { Answer, suggestions, useKnown } from './Ask'
import { Arrow, NotesList, crossedText, itemLine, itemTitle } from './Brief'
import { PeopleBlock, ResultsBlock, moveWhy, shortDay, tidySubject, useWord } from './items'
import { Chart, Src } from './ui'
import { BeforeAfter } from './Word'

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
  const segs = pages.length - 1
  const scroller = useRef<HTMLDivElement>(null)
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches

  const advance = (how: 'clear' | 'keep', dir: 'left' | 'right') => {
    if (page.kind === 'item') setDone(act(done, page.item.key, how))
    if (page.kind === 'notes') setDone({ ...done, notes: [...done.notes, notesKey(brief.notes, brief.spill)] })
    if (still) { setAt(a => a + 1); return }
    setLeaving(dir)
    setTimeout(() => { setLeaving(''); setAt(a => a + 1); scroller.current?.scrollTo(0, 0) }, 180)
  }
  useEffect(() => { scroller.current?.scrollTo(0, 0) }, [at])
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
      <header className="r-top">
        <button className="icon-btn" onClick={close} aria-label="Close the brief"><svg viewBox="0 0 20 20" aria-hidden><path d="M5 5l10 10M15 5L5 15" /></svg></button>
        {page.kind !== 'done' && <div className="progress r-progress" aria-hidden>{Array.from({ length: segs }, (_, k) => <span key={k} className={k < at ? 'on' : k === at ? 'now' : ''} />)}</div>}
        <span className="small r-count" aria-live="polite">{page.kind === 'done' ? '' : `${at + 1} of ${segs}`}</span>
      </header>
      <div className="r-scroll" ref={scroller}>
        <article key={at} className={`r-page${leaving ? ` out-${leaving}` : ''}`} style={dx ? { transform: `translateX(${dx}px) rotate(${dx / 60}deg)`, transition: 'none' } : undefined}
          onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
          {page.kind === 'item' && <ItemPage i={page.item} push={push} lines={lines} names={names} openCompany={openCompany} openLines={openLines} />}
          {page.kind === 'notes' && <><p className="small kicker">Under your lines</p><h1 className="title">Worth a line</h1><p className="lede">Filed in the window, none of it past your lines. One line each.</p><NotesList brief={brief} names={names} asof={push.asof} /></>}
          {page.kind === 'done' && <DonePage brief={brief} done={done} names={names} close={close} />}
        </article>
      </div>
      {page.kind !== 'done' && (
        <footer className="r-acts">
          {page.kind === 'item' && <button className="btn btn-line" onClick={() => advance('keep', 'right')}>Keep for later</button>}
          <button className="btn" onClick={() => advance('clear', 'left')}>{page.kind === 'notes' ? 'Mark all read' : 'Clear'}</button>
        </footer>
      )}
      {dx !== 0 && <p className={`r-hint ${dx < 0 ? 'l' : 'r'}`} aria-hidden>{dx < 0 ? 'Clear' : 'Keep'}</p>}
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
  const kind = i.kind === 'results' ? `Results, ${f?.results?.quarter}` : i.kind === 'people' ? 'Management change' : i.kind === 'move' ? 'Unusual day' : 'Filing'
  const others = i.story?.filings.filter(x => x !== f) || []
  return <>
    <p className="small kicker">{kind}, {i.kind === 'move' ? shortDay(m!.d) : when(i.at, push.asof)}</p>
    <h1 className="title"><button className="title-link" onClick={() => openCompany(i.symbol)}>{name}</button></h1>
    {i.kind !== 'move' && <p className="lede">{itemLine(i)}</p>}
    {m && <div className="r-move">
      <span className={`fig fig-m ${m.chg >= 0 ? 'up' : 'down'}`}>{m.chg >= 0 ? '+' : '−'}{Math.abs(m.chg).toFixed(1)}<span className="fig-pc">%</span></span>
      <span className="small">{m.volX.toFixed(1)}× its 20-day volume<br />Closed at ₹{m.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
    </div>}
    {bars.length > 1 && <figure className="r-chart"><Chart series={bars} h={88} /><figcaption className="small">Last {bars.length} sessions</figcaption></figure>}
    {i.kind === 'move' && <p className="lede r-why">{moveWhy(m!)}</p>}
    {f?.results && <ResultsBlock f={f} />}
    {f?.people?.length ? <PeopleBlock f={f} /> : null}
    {f && !f.results && f.amount_cr != null && f.amount_cr >= 1 && <p className="r-size"><span className="fig fig-s">₹{cr(f.amount_cr)}<span className="fig-pc"> cr</span></span>{f.pct_rev != null && <span className="small">{f.pct_rev < 0.1 ? 'Under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`} of a year’s revenue</span>}</p>}
    <p className="crossed"><span>{crossedText(i, lines)}.</span> <button className="link-inline" onClick={openLines}>Change</button></p>

    <Held i={i} name={name} openCompany={openCompany} />
    <AskHere push={push} symbol={i.symbol} name={name} openCompany={openCompany} />

    <ul className="srcs small">
      {f?.results?.source?.xbrl && <li><Src href={f.results.source.xbrl}>Exchange XBRL</Src></li>}
      {/\.pdf$/i.test(f?.results?.source?.pdf || '') && <li><Src href={f!.results!.source.pdf}>Results PDF</Src></li>}
      {f && <li><Src href={f.url}>The filing</Src></li>}
      {m?.explainedBy && m.explainedBy !== f && <li><Src href={m.explainedBy.url}>{tidySubject(m.explainedBy.subject)}</Src></li>}
      {others.slice(0, 4).map((o, k) => <li key={k}><Src href={o.url}>{tidySubject(o.subject)}</Src></li>)}
    </ul>
  </>
}

// Held against their word: for results, the promise this quarter answers to; otherwise their record in one line
function Held({ i, name, openCompany }: { i: Item; name: string; openCompany: (s: string, pid?: number) => void }) {
  const word = useWord(i.symbol)
  const [c, setC] = useState<Company | null>(null)
  useEffect(() => { getCompany(i.symbol).then(setC).catch(() => setC(null)) }, [i.symbol])
  const s = wordScore(c ?? undefined)
  const p = (i.kind === 'results' || i.move?.explainedBy?.category === 'results') ? word[0] : undefined
  if (!c) return null
  const record = s?.graded ? `${name} has kept ${Math.floor(s.kept)} of ${s.graded} dated promises it has been tested on.` : s?.hard ? `None of ${name}’s dated promises is due yet.` : `No promise from ${name} with a number and a date yet.`
  return (
    <section className="r-sec" aria-label="Against their word">
      <h2 className="head">Against their word</h2>
      {p ? <BeforeAfter p={p} compact /> : null}
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

function DonePage({ brief, done, names, close }: { brief: Brief; done: Done; names: Record<string, string>; close: () => void }) {
  const kept = brief.items.filter(i => done.kept.includes(i.key))
  const cleared = brief.items.filter(i => done.cleared.includes(i.key)).length
  const aside = brief.notes.length + brief.spill.length + brief.routine
  return (
    <div className="r-done">
      <h1 className="title done-t">You’re up to date</h1>
      <p className="lede">{cleared + kept.length} read{kept.length ? `, ${kept.length} kept for later` : ''}. {aside} more {aside === 1 ? 'filing' : 'filings'} set aside, each a tap away on the brief.</p>
      {kept.length > 0 && <>
        <h2 className="head">Kept for later</h2>
        <ul className="rows">{kept.map(i => <li key={i.key}><span className="row row-static">{itemTitle(i, names[i.symbol])}</span></li>)}</ul>
      </>}
      <button className="btn btn-wide" onClick={close}>Back to the brief</button>
    </div>
  )
}
