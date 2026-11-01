// The brief: the few things that crossed the investor's lines, as notifications, and a way through them that ends.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { buildBrief, newsQuestion, type Brief, type Item } from './queue'
import { CATEGORY_LABEL, cr, dayMon, getCompany, rupees, sessionWhen, when, type Bar, type Lines, type Push } from './lib'
import { FoldSummary, NoteRow, Roll, few, moveWhy, reclass, resultLine, shortDay, sizeWords, sortPeople, tidySubject } from './items'
import { Chart, Fold, Masthead, Outcome, useKept } from './ui'
import { alertsBlocked, alertsOn, canAlert, disableAlerts, enableAlerts } from './alerts'

export const WINDOWS = [{ h: 24, label: '24 hours' }, { h: 72, label: '3 days' }, { h: 168, label: 'Week' }, { h: 720, label: 'Month' }]
const SPAN: Record<number, string> = { 24: 'in the last 24 hours', 72: 'in the last 3 days', 168: 'in the last week', 720: 'in the last month' }
const span = (h: number) => SPAN[h] || 'in the window'

// ---------- how an item reads ----------
const pct1 = (v: number) => `${Math.abs(v).toFixed(1)}%`
const strip = (n: string) => n.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')
// Headlines use the titles investors say: CFO, not Chief Financial Officer
const shortRole = (r: string) => r.replace(/\bChief Financial Officer\b/i, 'CFO').replace(/\bChief Executive Officer\b/i, 'CEO')
  .replace(/\bChief Operating Officer\b/i, 'COO').replace(/\bManaging Director\b/i, 'MD').replace(/\bCompany Secretary\b/i, 'company secretary')
// The management change riding with a results item, in one sentence: 'Its CFO, Deepak Jain, resigns.'
export function withLine(s: NonNullable<Item['with']>) {
  const p = sortPeople(s.lead.people || [])[0]
  if (!p) return ''
  const v = ({ appointed: 'joins', resigned: 'resigns', retired: 'retires', ceased: 'leaves', redesignated: 'takes a new role', 're-appointed': 'is re-appointed' } as any)[p.action] || p.action
  return p.action === 'appointed' ? `A new ${shortRole(p.role)}, ${strip(p.name)}, joins.` : `Its ${shortRole(p.role)}, ${strip(p.name)}, ${v}.`
}
// A management change riding with results: a CEO, CFO or MD change leads, anyone else follows. One fact to a line
function withLines(i: Item, body: string[]) {
  if (!i.with) return body
  return i.with.lead.people?.some(p => p.seniority === 'top') ? [withLine(i.with), ...body] : [...body, withLine(i.with)]
}
export function itemTitle(i: Item, name: string): string {
  const m = i.move, f = i.story?.lead
  if (i.kind === 'results' && f?.results) return `${name} reported ${f.results.quarter.replace(/ FY\d\d$/, '')}`
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0]
    const r = shortRole(p.role), role = r.length > 26 ? 'a director' : r
    return ['appointed', 're-appointed', 'redesignated'].includes(p.action) ? `${name} names a new ${role}` : `${name}: ${role} ${p.action === 'retired' ? 'retires' : 'leaves'}`
  }
  if (m) return m.why.includes('price') ? `${name} ${m.chg > 0 ? 'rose' : 'fell'} ${pct1(m.chg)}` : `${name} traded ${m.volX.toFixed(1)}× its usual volume`
  return `${name}: ${(CATEGORY_LABEL[i.story!.category] || i.story!.category).toLowerCase()}`
}
export function itemLine(i: Item): string {
  const f = i.story?.lead
  if (i.kind === 'results' && f?.results) return resultLine(f.results, f.results.lines.find((l: any) => l.key === 'pat'))
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0], more = f.people.length - 1
    const what = reclass(p) ? `stays ${p.role}, off the senior management list` : `${({ appointed: 'joins as', resigned: 'resigns as', retired: 'retires as', ceased: 'leaves as', redesignated: 'is now', 're-appointed': 'is re-appointed' } as any)[p.action] || p.action} ${p.role}`
    return `${strip(p.name)} ${what}.${more > 0 ? ` ${more} more ${more === 1 ? 'change' : 'changes'} in the filing.` : ''}`
  }
  if (i.move && !f) return i.move.why.includes('price')
    ? `On ${i.move.volX.toFixed(1)}× its usual volume. ${moveWhy(i.move)}`
    : `${i.move.chg >= 0 ? 'Up' : 'Down'} ${pct1(i.move.chg)} on the day. ${moveWhy(i.move)}`
  const t = (f?.line || tidySubject(f?.subject || '')).replace(/\.?$/, '.')
  return f?.pct_rev != null ? `${t} ${sizeWords(f)}` : t
}
// The line that set it off, in the investor's own terms
export function crossedText(i: Item, lines: Lines): string {
  const rank = { filing: 0, volume: 1, price: 2 }
  const parts = [...i.crossed].sort((a, b) => rank[a.line] - rank[b.line]).map(c => c.line === 'price' ? `a ±${lines.movePct}% day` : c.line === 'volume' ? `${lines.volX}× volume` : (CATEGORY_LABEL[c.category!] || c.category!).toLowerCase())
  const u = [...new Set(parts)]
  return `Your ${u.length > 1 ? 'lines' : 'line'}: ${u.length > 1 ? `${u.slice(0, -1).join(', ')} and ${u[u.length - 1]}` : u[0]}`
}

// The tag on an alert row: the thresholds the shares went past ('Past your ±4% and 2× lines'), else the kinds of filing.
// The reader's foot lists every line crossed
export function rowTag(i: Item, lines: Lines): string {
  const mk = [...new Set(i.crossed.filter(c => c.line !== 'filing').map(c => c.line))].sort((a, b) => a === 'price' ? -1 : b === 'price' ? 1 : 0)
  if (mk.length > 1) return `Past your ±${lines.movePct}% and ${lines.volX}× lines`
  if (mk.length) return `Past your ${mk[0] === 'price' ? `±${lines.movePct}%` : `${lines.volX}× volume`} line`
  const kinds = [...new Set(i.crossed.map(c => (CATEGORY_LABEL[c.category!] || c.category!).toLowerCase()))]
  return (kinds.length > 1 ? `${kinds.slice(0, -1).join(', ')} and ${kinds[kinds.length - 1]}` : kinds[0]).replace(/^./, c => c.toUpperCase())
}

// ---------- the screen ----------
const WIN_LABEL: Record<number, string> = { 24: '24h', 72: '3 days', 168: 'Week', 720: 'Month' }
const WIN_PHRASE: Record<number, string> = { 24: 'The last 24 hours', 72: 'Three days', 168: 'The week', 720: 'The month' }
const END: Record<number, string> = { 24: 'That’s the last 24 hours.', 72: 'That’s the last 3 days.', 168: 'That’s the week.', 720: 'That’s the month.' }

// Today, as v4 set it: the count of what needs you, one grey sentence, the window, a warm card for each thing,
// the rest folded, and a blue band where the window ends. Each card opens into its full view.
export function BriefScreen({ push, brief, fresh, lines, setLines, names, openItem, openLines }: {
  push: Push; brief: Brief; fresh: Set<string>; lines: Lines; setLines: (l: Lines) => void; names: Record<string, string>
  openItem: (key: string, el: HTMLElement | null) => void; openLines: () => void
}) {
  const [showNotes, setShowNotes] = useKept('today.notes', false)
  const [showFold, setShowFold] = useKept('today.fold', false)
  const n = brief.items.length, nNotes = brief.notes.length + brief.spill.length
  // A change of window says what it changed: who came in, or who dropped out, under the knob that did it
  const seen = useRef({ h: lines.hours, syms: brief.items.map(i => i.symbol) })
  const [delta, setDelta] = useState('')
  useEffect(() => {
    const was = seen.current, syms = brief.items.map(i => i.symbol)
    seen.current = { h: lines.hours, syms }
    if (was.h === lines.hours) return
    const nm = (xs: string[]) => few([...new Set(xs)].map(x => names[x] || x))
    const inn = syms.filter(x => !was.syms.includes(x)), out = was.syms.filter(x => !syms.includes(x))
    const w = WIN_PHRASE[lines.hours]
    // A wider window is read for what it adds, a narrower one for what it leaves out
    setDelta(lines.hours > was.h
      ? inn.length ? `${w} adds ${nm(inn)}.` : `${w} adds nothing that needs you.`
      : out.length ? `${w} leaves out ${nm(out)}.` : `${w} leaves out nothing.`)
  }, [brief, lines.hours, names])
  const asof = new Date(push.asof)
  const time = asof.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()
  // Today the time is what matters ('to 9:21 pm'); an older snapshot is dated by its day alone, so the sentence keeps to two lines
  const stamp = (asof.toDateString() === new Date().toDateString() ? time : dayMon(asof)).replace(' ', '\u00a0')
  // The sieve plays once a session: the count starts at every filing in the window and falls to what needs you
  const sieve = useRef(!sessionStorage.getItem('finn-sieved'))
  useEffect(() => { sessionStorage.setItem('finn-sieved', '1') }, [])
  const total = n + nNotes + brief.routine
  // Nothing crossed: point to the nearest wider window that has something, with its count
  const wider = n ? undefined : WINDOWS.filter(w => w.h > lines.hours).map(w => ({ ...w, n: buildBrief(push, { ...lines, hours: w.h }).items.length })).find(w => w.n > 0)

  return (
    <main className="screen today">
      <Masthead />
      <section className="hero" aria-labelledby="brief-h">
        {/* The roll is for the eye; a screen reader hears the settled count once */}
        <h1 id="brief-h" className="sr-only" aria-live="polite">{n ? `${n} ${n === 1 ? 'needs' : 'need'} you` : 'Nothing needs you'}</h1>
        <div className="hero-fig" aria-hidden="true">
          {n ? <Outcome size="l" value={<Roll to={n} start={sieve.current && total > n ? total : undefined} />} /> : <Outcome size="l" value="Nothing" />}
          <span className="hero-unit">{n === 1 || !n ? 'needs you' : 'need you'}</span>
        </div>
        {/* The sentence carries the time the filings run to, so the screen needs no dateline above the count */}
        <p className="hero-2">{n
          ? `${few([...new Set(brief.items.map(i => names[i.symbol]))])}, out of ${total} filings and moves to ${stamp}.`
          : `Nothing crossed your lines ${span(lines.hours)}, to ${stamp}.${nNotes ? ` ${nNotes} worth a look below.` : ''}`}</p>
        {wider && <button className="see hero-wider" onClick={() => setLines({ ...lines, hours: wider.h })}>{`${span(wider.h).replace(/^in the l/, 'L')}: ${wider.n} ${wider.n === 1 ? 'needs' : 'need'} you`}</button>}
        <div className="window" role="radiogroup" aria-label="Window">
          {WINDOWS.map(w => <button key={w.h} role="radio" aria-checked={lines.hours === w.h} className={lines.hours === w.h ? 'on' : ''} onClick={() => setLines({ ...lines, hours: w.h })}>{WIN_LABEL[w.h]}</button>)}
        </div>
        <p className="win-delta" aria-live="polite">{delta && <span key={delta}>{delta}</span>}</p>
      </section>

      {n > 0 && <ol className="cards">
        {brief.items.map(i => <li key={i.key}><ItemCard i={i} fresh={fresh.has(i.key)} name={names[i.symbol]} push={push} lines={lines} open={el => openItem(i.key, el)} /></li>)}
      </ol>}

      {nNotes > 0 && <Fold title="Worth a look" count={nNotes} open={showNotes} toggle={() => setShowNotes(!showNotes)}>
        <NotesList brief={brief} names={names} asof={push.asof} />
      </Fold>}
      {brief.routine > 0 && <Fold title="Routine filings" count={brief.routine} open={showFold} toggle={() => setShowFold(!showFold)}>
        <FoldSummary stories={brief.folded} names={names} />
      </Fold>}

      {/* Below the folds, the two quiet controls: the lines that decide what interrupts, and the brief read aloud */}
      <ul className="tools">
        <li><button className="tool" onClick={openLines}><span>Your lines<span className="fold-l">{`±${lines.movePct}% in a day, ${lines.volX}× volume, ${lines.interrupt.length} ${lines.interrupt.length === 1 ? 'kind' : 'kinds'} of filing`}</span></span><Chev /></button></li>
        <Listen push={push} brief={brief} names={names} />
      </ul>

      {/* The window ends on one blue band: it is done, the questions it leaves for the next calls, and the two next moves */}
      <section className="end-band" aria-label="End of the window">
        <div className="end-band-in">
          <h2 className="t-h1">{END[lines.hours] ?? 'That’s everything.'}</h2>
          <EndQuestions brief={brief} push={push} names={names} />
          <div className="end-band-btns">
            <a className="btn-light" href="#/book">Open your book</a>
            <button className="end-copy" onClick={openLines}>Change your lines</button>
          </div>
        </div>
      </section>
    </main>
  )
}

// A move is a day's close, dated the way filings are: 'At the close' on the snapshot's day, 'Yesterday at the close', else the date
export const closeWhen = (d: string, asof: string) => {
  const days = Math.round((Date.parse(asof.slice(0, 10)) - Date.parse(d)) / 864e5)
  return days === 0 ? 'At the close' : days === 1 ? 'Yesterday at the close' : dayMon(new Date(d + 'T12:00:00'))
}

export const Arrow = () => <svg className="arrow" viewBox="0 0 16 16" aria-hidden><path d="M6 3.5l4.5 4.5L6 12.5" /></svg>

// The session that first traded on a filing: the same day if it came before the 3:30 pm close, else the next one
function reaction(push: Push, symbol: string, at: string) {
  const d = at.slice(0, 10), after = at.slice(11, 16) >= '15:30'
  const b = (push.eod[symbol] || []).find(x => after ? x.d > d : x.d >= d)
  return b ? { b } : null
}
const signed = (v: number) => `${v >= 0 ? '+' : '−'}${pct1(v)}`
const pctWords = (v: number) => `${v >= 0 ? 'up' : 'down'} ${String(+Math.abs(v).toFixed(Math.abs(v) < 10 ? 1 : 0))}%`

// The figure column means one thing on every alert: how the shares took it, the day's change. The event is in the words.
// d is the session the figure and the month line end on.
export function alertFig(i: Item, name: string, push: Push): { v: string; c: string; body: string[]; t?: string; d: string } | null {
  const f = i.story?.lead, m = i.move
  // Anything that moved the shares leads with the day's change, whichever line it crossed. In a 24-hour window
  // results-day moves arrive as moves, in a wider one they ride with their results: same event, same figure, same words
  if (m && (i.kind === 'move' || (i.kind === 'results' && f?.results))) {
    // A move on results says what the results were, not just that they came out
    const res = f?.results ?? (m.explainedBy?.category === 'results' ? push.filings.filter(x => x.symbol === i.symbol && x.results && x.at.slice(0, 10) <= m.d).sort((a, b) => b.at.localeCompare(a.at))[0]?.results : undefined)
    const vol = `On ${m.volX.toFixed(1)}× its usual volume.`
    const body = res ? [...resultsWords(res), vol] : [vol, moveWhy(m)]
    // The caption names the session as the row's time does ('today', 'yesterday'), so the 24-hour row and the week's read alike
    return { v: signed(m.chg), c: sessionWhen(m.d, push.asof), t: name, body: withLines(i, body), d: m.d }
  }
  // Anything else: the session that first traded on the filing; before it has traded, the row keeps its headline
  const r = reaction(push, i.symbol, i.at)
  if (!r) return null
  const fig = (body: string[]) => ({ v: signed(r.b.chg), c: sessionWhen(r.b.d, push.asof), t: name, body, d: r.b.d })
  if (i.kind === 'results' && f?.results) return fig(withLines(i, resultsWords(f.results)))
  if (i.kind === 'filing' && f?.amount_cr != null && f.amount_cr >= 1 && f.pct_rev != null)
    return fig([(f.line || tidySubject(f.subject || '')).replace(/\.?$/, '.'), sizeWords(f)])
  return fig(itemLine(i).split(/(?<=\.) (?=[A-Z0-9])/))
}
// A quarter in a line or two: profit in rupees first (a turn from last quarter's loss said with it), then the margin
// on its own line when it moved a point or more
function resultsWords(r: any): string[] {
  const pat = r.lines.find((l: any) => l.key === 'pat'), q = r.quarter.replace(/ FY\d\d$/, '')
  const turn = pat?.prev != null && pat.prev < 0 && pat.value >= 0
  const yoy = pat?.yoy != null ? `, ${pctWords(pat.yoy)} on a year ago` : ''
  const profit = pat?.value == null ? `${q} results out.` : `${q} profit ₹${cr(pat.value)} crore${turn ? ' after last quarter’s loss' : ''}${yoy}.`
  const dm = r.ebitda_margin != null && r.yago_margin != null ? r.ebitda_margin - r.yago_margin : 0
  return Math.abs(dm) >= 1 ? [profit, `EBITDA margin ${dm > 0 ? 'up' : 'down'} ${Math.abs(dm).toFixed(1)} pp.`] : [profit]
}

// What the window leaves to ask: the news first (a CFO leaving, a margin that fell), else the company's own question
// from its calls. One for each company that needed you, to copy into the call notes
function EndQuestions({ brief, push, names }: { brief: Brief; push: Push; names: Record<string, string> }) {
  const [qs, setQs] = useState<{ symbol: string; q: string }[]>([])
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    let live = true
    const first = new Map<string, Item>(); brief.items.forEach(i => { if (!first.has(i.symbol)) first.set(i.symbol, i) })
    Promise.all([...first.values()].slice(0, 3).map(i => {
      const q = newsQuestion(i, push)
      return q ? { symbol: i.symbol, q } : getCompany(i.symbol).then(c => c?.questions?.[0] ? { symbol: i.symbol, q: rupees(c.questions[0]) } : null).catch(() => null)
    })).then(xs => live && setQs(xs.filter((x): x is { symbol: string; q: string } => !!x)))
    return () => { live = false }
  }, [brief, push])
  if (!qs.length) return null
  const copy = () => navigator.clipboard?.writeText(`For the next calls\n${qs.map((x, k) => `${k + 1}. ${names[x.symbol]}: ${x.q}`).join('\n')}`)
    .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return (
    <div className="end-qs">
      <h3 className="lbl">For the next calls</h3>
      <ol>{qs.map(x => <li key={x.symbol}><span className="end-co">{names[x.symbol]}</span>{x.q}</li>)}</ol>
      {navigator.clipboard && <button className="end-copy" onClick={copy} aria-live="polite">{copied ? 'Copied' : 'Copy the questions'}</button>}
    </div>
  )
}

// What kind of thing a card is, in the label above its name
export function kindLabel(i: Item, push: Push): string {
  const f = i.story?.lead
  // A results-day move and the results it rides with read alike in every window
  const res = f?.results ?? (i.move?.explainedBy?.category === 'results' ? push.filings.filter(x => x.symbol === i.symbol && x.results && x.at.slice(0, 10) <= i.move!.d).sort((a, b) => b.at.localeCompare(a.at))[0]?.results : undefined)
  // A move past a line on results says so; results the shares took quietly are just the results
  // A move names the line it crossed: the price, or only the volume ('Heavy trading on Q2 FY27 results')
  const moved = i.move && (i.move.why.includes('price') ? 'Price move' : 'Heavy trading')
  if (res && (i.kind === 'results' || i.kind === 'move')) return moved ? `${moved} on ${res.quarter} results` : `${res.quarter} results`
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0], r = shortRole(p.role)
    return ['appointed', 're-appointed', 'redesignated'].includes(p.action) ? (r.length > 20 ? 'New director' : `New ${r}`) : 'Management change'
  }
  if (i.kind === 'move') return moved || 'Unusual day'
  return CATEGORY_LABEL[i.story!.category] || 'Filing'
}

// The card's sentence: the news in one or two facts. Volume and the line crossed are under the figure.
// The full view opens on the same words, so nothing changes under the eye as the card grows
export const cardSentence = (i: Item, fig: { body: string[] } | null) =>
  (fig ? fig.body : [itemLine(i)]).filter(l => !/^On [\d.]+× its usual volume/.test(l)).slice(0, 2).join(' ')

// A card, as v4 set them: the month's price line on top, what kind of thing, the company, the day's move with the
// line it crossed, one grey sentence, and Read more. Everything else is in the full view it opens into.
function ItemCard({ i, fresh, name, push, lines, open }: { i: Item; fresh: boolean; name: string; push: Push; lines: Lines; open: (el: HTMLElement | null) => void }) {
  const ref = useRef<HTMLElement>(null)
  const fig = alertFig(i, name, push)
  const bars = (push.eod[i.symbol] || []).filter(b => b.d <= (fig?.d ?? i.at.slice(0, 10))).slice(-30)
  const body = cardSentence(i, fig)
  const [v, u] = fig ? [fig.v.replace('%', ''), '%'] : ['', '']
  const line = bars.length > 4
  return (
    <article className="card" ref={ref} data-key={i.key}>
      {/* One picture: the month's line, ending on the day's move under its last close */}
      {line && <PriceLine bars={bars} end={fig && <Outcome size="xxs" value={v} unit={u} />} />}
      <div className="card-info">
        <div className="card-lbl"><span className="lbl">{kindLabel(i, push)}</span>{fresh && <span className="lbl lbl-new" title="New since you last looked">New</span>}</div>
        <h2 className="card-title">{name}</h2>
        {fig && (line
          ? i.move && <p className="card-cap">On {i.move.volX.toFixed(1)}× its usual volume</p>
          : <div className="card-fig"><Outcome size="xs" value={v} unit={u} /><span className="card-cap">{figWhen(fig.d, i)}</span></div>)}
        <p className="card-desc">{body}</p>
        <p className="card-line">{rowTag(i, lines)}</p>
        <div className="card-foot">
          <button className="read-more" onClick={() => open(ref.current)} aria-label={`Read more about ${name}`}>Read more</button>
          {!fig && <span className="lbl lbl-quiet">{shortDay(i.at)}</span>}
        </div>
      </div>
    </article>
  )
}
// The card's picture: the month's closes, short. Its start says the period and what the month did ('Since 15 Sep,
// +4.1%'), so the big figure at its end reads as the one day it is dated to ('on 28 Oct'), not the month's return
export function PriceLine({ bars, end }: { bars: Bar[]; end?: ReactNode }) {
  const last = shortDay(bars[bars.length - 1].d)
  const month = `Since ${shortDay(bars[0].d)}, ${signed((bars[bars.length - 1].close / bars[0].close - 1) * 100)}`
  return <figure className="price"><div className="card-img"><Chart series={bars} /></div>
    <figcaption className="price-d"><span>{month}</span>{end ? <span className="price-end">{end}<span>on {last}</span></span> : <span>{last}</span>}</figcaption></figure>
}

// One date for a figure, the same in every window: the session it closed in, and the volume it closed on
export const figWhen = (d: string, i: Item) => `At the ${shortDay(d)} close${i.move ? `, on ${i.move.volX.toFixed(1)}× its usual volume` : ''}`

export function NotesList({ brief, names, asof }: { brief: Brief; names: Record<string, string>; asof: string }) {
  return (
    <ul className="notes">
      {brief.spill.map(i => i.story
        ? <NoteRow key={i.key} s={i.story} name={names[i.symbol]} asof={asof} />
        : <li key={i.key}><div className="note"><span className="note-co">{names[i.symbol]}</span><span className="note-text">{itemTitle(i, names[i.symbol]).replace(names[i.symbol] + ' ', '').replace(/^./, c => c.toUpperCase())}. {moveWhy(i.move!)}</span><span className="note-when">{when(i.at, asof)}</span></div></li>)}
      {brief.notes.map(s => <NoteRow key={s.key} s={s} name={names[s.symbol]} asof={asof} />)}
    </ul>
  )
}

// Listen: the brief read aloud by the browser's own voice. Free, and works offline.
function Listen({ push, brief, names }: { push: Push; brief: Brief; names: Record<string, string> }) {
  const [on, setOn] = useState(false)
  const ok = typeof window !== 'undefined' && 'speechSynthesis' in window
  const utter = useRef<SpeechSynthesisUtterance | null>(null)
  useEffect(() => () => { if (ok) speechSynthesis.cancel() }, [ok])
  if (!ok) return null
  const left = brief.items
  const say = () => {
    if (on) { speechSynthesis.cancel(); setOn(false); return }
    const said = (t: string) => t.replace(/₹/g, 'rupees ').replace(/\bcr\b/g, 'crore').replace(/×/g, ' times').replace(/±/g, 'plus or minus ').replace(/−/g, 'minus ').replace(/\+(?=\d)/g, 'plus ').replace(/%/g, ' percent')
    // Each item as its alert row reads: the name, its figure, the sentence. The lines it crossed are on screen
    const spoken = (i: Item) => {
      const n = names[i.symbol], f = alertFig(i, n, push)
      return f ? `${n}, ${f.v} ${f.c}. ${f.body.join(' ')}` : `${itemTitle(i, n)}. ${itemLine(i)}`
    }
    const text = left.length ? [`${left.length} ${left.length === 1 ? 'needs' : 'need'} you.`, ...left.map(spoken), 'That’s the brief.'].join(' ') : 'Nothing crossed your lines.'
    const u = new SpeechSynthesisUtterance(said(text)); u.lang = 'en-IN'; u.rate = 1.02
    u.onend = () => setOn(false); u.onerror = () => setOn(false)
    utter.current = u; speechSynthesis.cancel(); speechSynthesis.speak(u); setOn(true)
  }
  return <li><button className="tool" onClick={say} aria-pressed={on}>
    <span>{on ? 'Stop reading' : 'Listen'}<span className="fold-l">{on ? 'Reading the brief aloud' : `The ${left.length ? `${left.length} that need you` : 'brief'}, read aloud`}</span></span>
    <svg className="tool-i" viewBox="0 0 20 20" aria-hidden><path d="M3.5 7.5h3l4-3.5v12l-4-3.5h-3z" />{on ? <path d="M13.5 7.5v5M16 6v8" /> : <path d="M13.5 7.2a4 4 0 0 1 0 5.6M15.6 5.2a7 7 0 0 1 0 9.6" />}</svg>
  </button></li>
}

const Chev = () => <svg className="tool-i" viewBox="0 0 16 16" aria-hidden><path d="M6 3.5l4.5 4.5L6 12.5" /></svg>

// Alerts on this phone: asks the browser once; when on, the top item arrives as a real notification straight away
export function AlertsRow({ top, names, lines }: { top?: Item; names: Record<string, string>; lines: Lines }) {
  const [on, setOn] = useState(alertsOn)
  const [note, setNote] = useState('')
  if (!canAlert()) return null
  const flip = async () => {
    if (on) { disableAlerts(); setOn(false); setNote(''); return }
    const r = await enableAlerts(top && { key: top.key, title: itemTitle(top, names[top.symbol]), body: `${itemLine(top)} ${crossedText(top, lines)}.` })
    setOn(r === 'on')
    setNote(r === 'denied' ? 'The browser said no. Allow notifications for this site in its settings.' : r === 'on' && top ? 'Sent the top item so you can see one.' : '')
  }
  const sub = note || (on ? 'On. New items arrive as notifications when FINN opens on a newer snapshot' : alertsBlocked() ? 'Blocked in this browser’s settings' : 'Off. Get what crosses your lines as phone notifications')
  return <>
    <li><label className="row row-switch"><span>Alerts on this phone<span className="row-sub" aria-live="polite">{sub}</span></span>
      <input type="checkbox" role="switch" checked={on} onChange={flip} /></label></li>
    {/* The words an alert carries, set as the phone would show them, with the line that set it off: it changes as the lines do */}
    {top && <li className="alert-pre" aria-label="What an alert says">
      <p className="alert-app"><span>FINN</span><span>{shortDay(top.at)}</span></p>
      <p className="alert-t">{itemTitle(top, names[top.symbol])}</p>
      <p className="alert-b">{itemLine(top)} {crossedText(top, lines)}.</p>
    </li>}
  </>
}
