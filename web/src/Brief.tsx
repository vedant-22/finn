// The brief: the few things that crossed the investor's lines, as notifications, and a way through them that ends.
import { NetAskFirst, NetCardLine, NetNoticed, NetSyntheticNote, netTitle } from './Network'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { tagClick, useDrift } from './motion'
import { buildBrief, newsQuestion, newsTopic, questionKind, topicOf, type Brief, type Item, type Kind, type Topic } from './queue'
import { CATEGORY_LABEL, cr, dayMon, getCompany, plainTerms, quarterMonths, rupees, sessionWhen, when, type Bar, type Lines, type Push } from './lib'
import { FoldSummary, NoteRow, Roll, few, moveWhy, reclass, resultLine, shortDay, sizeWords, sortPeople, tidySubject } from './items'
import { Chart, Fold, Masthead, Outcome, SettleImg, useKept } from './ui'
import { alertsBlocked, alertsOn, canAlert, disableAlerts, enableAlerts } from './alerts'
import { load, save } from './storage'
import { DemoPill } from './Trust'

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
  if (i.kind === 'results' && f?.results) return `${name} reported its ${quarterMonths(f.results.quarter) || f.results.quarter} results`
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0]
    const r = shortRole(p.role), role = r.length > 26 ? 'a director' : r
    return ['appointed', 're-appointed', 'redesignated'].includes(p.action) ? `${name} names a new ${role}` : `${name}: ${role} ${p.action === 'retired' ? 'retires' : 'leaves'}`
  }
  if (m) return m.why.includes('price') ? `${name} ${m.chg > 0 ? 'rose' : 'fell'} ${pct1(m.chg)}` : `${name} traded ${m.volX.toFixed(1)} times its usual amount`
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
    ? `${traded(i.move.volX)} ${moveWhy(i.move)}`
    : `${i.move.chg >= 0 ? 'Up' : 'Down'} ${pct1(i.move.chg)} on the day. ${moveWhy(i.move)}`
  const t = plainTerms(f?.line || tidySubject(f?.subject || '')).replace(/\.?$/, '.')
  return f?.pct_rev != null ? `${t} ${sizeWords(f)}` : t
}
// How much a share traded against its usual day, said the way you would say it: 'It traded 43.5 times its usual amount.'
export const traded = (x: number) => `It traded ${x.toFixed(1)} times its usual amount.`
// An alert level, in words: a price move in a day, or trading against the usual
const level = (line: 'price' | 'volume', lines: Lines) => line === 'price' ? `a ${lines.movePct}% move in a day` : `${lines.volX} times the usual trading`
const and = (xs: string[]) => xs.length > 1 ? `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}` : xs[0]
// The alert level that set it off, in the investor's own terms. No full stop: the caller ends the sentence
export function crossedText(i: Item, lines: Lines): string {
  const rank = { filing: 0, price: 1, volume: 2 }
  const marks = i.crossed.filter(c => c.line !== 'filing')
  const parts = [...i.crossed].sort((a, b) => rank[a.line] - rank[b.line]).map(c => c.line === 'filing' ? (CATEGORY_LABEL[c.category!] || c.category!).toLowerCase() : level(c.line, lines))
  const u = [...new Set(parts)]
  return marks.length ? `Past your alert ${u.length > 1 ? 'levels' : 'level'}: ${and(u)}` : `On your alert list: ${and(u)}`
}

// Why a card is on Today, in one sentence: the alert levels the shares went past, else the kinds of announcement
// the investor asked to be told about. The full view lists every one
export function rowTag(i: Item, lines: Lines): string {
  const mk = [...new Set(i.crossed.filter(c => c.line !== 'filing').map(c => c.line))].sort((a, b) => a === 'price' ? -1 : b === 'price' ? 1 : 0) as ('price' | 'volume')[]
  if (mk.length > 1) return `Past both your alert levels: ${level('price', lines)}, and ${level('volume', lines)}.`
  if (mk.length) return `Past your alert level of ${level(mk[0], lines)}.`
  const kinds = [...new Set(i.crossed.map(c => (CATEGORY_LABEL[c.category!] || c.category!).toLowerCase()))]
  return `On your alert list: ${and(kinds)}.`
}

// ---------- the screen ----------
const WIN_LABEL: Record<number, string> = { 24: '24 hours', 72: '3 days', 168: 'Week', 720: 'Month' }
const WIN_PHRASE: Record<number, string> = { 24: 'The last 24 hours', 72: 'Three days', 168: 'The week', 720: 'The month' }
const END: Record<number, string> = { 24: 'That’s everything from the last 24 hours.', 72: 'That’s everything from the last 3 days.', 168: 'That’s everything from the last week.', 720: 'That’s everything from the last month.' }

// Today, as v4 set it: how many companies need a look, one grey sentence saying which, the window, a warm card for each thing,
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
      ? inn.length ? `${w} adds ${nm(inn)}.` : `${w} adds nothing that needs a look.`
      : out.length ? `${w} leaves out ${nm(out)}.` : `${w} leaves out nothing.`)
  }, [brief, lines.hours, names])
  const asof = new Date(push.asof)
  const time = asof.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()
  // What FINN checked runs up to a time: 'up to 9:21 pm' today, 'up to 9:21 pm on 28 Oct' on an older snapshot
  const stamp = asof.toDateString() === new Date().toDateString() ? time : `${time} on ${dayMon(asof).replace(' ', '\u00a0')}`
  // The sieve plays once a session: the count starts at every filing in the window and falls to what needs you
  const sieve = useRef(!load('sieved'))
  useEffect(() => { save('sieved', '1') }, [])
  const total = n + nNotes + brief.routine
  const heroRef = useRef<HTMLElement>(null)
  useDrift(heroRef)
  // The count is of companies, as its words say: two cards about one company are one company
  const cos = [...new Set(brief.items.map(i => i.symbol))]
  // Nothing crossed: point to the nearest wider window that has something, with its count
  const wider = n ? undefined : WINDOWS.filter(w => w.h > lines.hours).map(w => ({ ...w, n: buildBrief(push, { ...lines, hours: w.h }).items.length })).find(w => w.n > 0)

  return (
    <main className="screen today">
      <Masthead right={<DemoPill push={push} />} />
      <section className="hero" ref={heroRef} aria-labelledby="brief-h">
        {/* The roll is for the eye; a screen reader hears the settled count once */}
        <h1 id="brief-h" className="sr-only" aria-live="polite">{n ? `${cos.length} of your companies ${cos.length === 1 ? 'needs' : 'need'} a look today` : 'Nothing needs a look today'}</h1>
        <div className="hero-fig" aria-hidden="true">
          {n ? <Outcome size="l" value={<Roll to={cos.length} start={sieve.current && total > cos.length ? total : undefined} />} /> : <Outcome size="l" value="Nothing" />}
          <span className="hero-unit">{n ? <>of your companies<br />{cos.length === 1 ? 'needs' : 'need'} a look today</> : <>needs a look<br />today</>}</span>
        </div>
        {/* The sentence carries the time FINN checked up to, so the screen needs no dateline above the count */}
        {/* A card about people you know is not in the count: it passed none of the alert levels, so the sentence names it apart */}
        <p className="hero-2">{n
          ? `${few(cos.map(s => names[s]))}. FINN checked ${total} ${total === 1 ? 'announcement or price move' : 'announcements and price moves'}, up to ${stamp}.${brief.net ? ' One more is about people you know.' : ''}`
          : `Nothing passed your alert levels ${span(lines.hours)}, up to ${stamp}.${brief.net ? ' One below is about people you know.' : nNotes ? ` ${nNotes} worth a look below.` : ''}`}</p>
        {wider && <button className="see hero-wider" onClick={() => setLines({ ...lines, hours: wider.h })}>{`${span(wider.h).replace(/^in the l/, 'In the l')}: ${wider.n} ${wider.n === 1 ? 'needs' : 'need'} a look`}</button>}
        <div className="window" role="radiogroup" aria-label="Window">
          {WINDOWS.map(w => <button key={w.h} role="radio" aria-checked={lines.hours === w.h} className={lines.hours === w.h ? 'on' : ''} onClick={() => setLines({ ...lines, hours: w.h })}>{WIN_LABEL[w.h]}</button>)}
        </div>
        <p className="win-delta" aria-live="polite">{delta && <span key={delta}>{delta}</span>}</p>
      </section>

      {(n > 0 || brief.net) && <ol className="cards">
        {brief.items.map(i => <li key={i.key}><ItemCard i={i} fresh={fresh.has(i.key)} name={names[i.symbol]} push={push} lines={lines} open={el => openItem(i.key, el)} /></li>)}
        {brief.net && <li key={brief.net.key}><NetItemCard i={brief.net} title={netTitle(brief.net.notice!, names)} open={el => openItem(brief.net!.key, el)} /></li>}
      </ol>}
      {(n > 0 || brief.net) && <NetSyntheticNote />}

      {nNotes > 0 && <Fold title="Worth a look" count={nNotes} open={showNotes} toggle={() => setShowNotes(!showNotes)}>
        <NotesList brief={brief} names={names} asof={push.asof} />
      </Fold>}
      {brief.routine > 0 && <Fold title="Routine announcements" count={brief.routine} open={showFold} toggle={() => setShowFold(!showFold)}>
        <FoldSummary stories={brief.folded} names={names} />
      </Fold>}
      <NetNoticed hours={lines.hours} asof={push.asof} skip={brief.items.map(i => i.symbol)} raised={brief.net?.notice} />

      {/* The window ends on one blue band: it is done, the questions it leaves for the next calls, and the two next moves */}
      <section className="end-band" aria-label="End of the window">
        <div className="end-band-in">
          <h2 className="t-h1">{END[lines.hours] ?? 'That’s everything.'}</h2>
          <EndQuestions brief={brief} push={push} names={names} />
          {/* One button, and the two quiet controls as links: the lines that decide what interrupts, and the brief read aloud */}
          <div className="end-band-btns">
            <a className="btn-light" href="#/book">See your holdings</a>
          </div>
          <div className="end-links">
            <button className="end-copy" onClick={openLines}>Change alert levels</button>
            <Listen push={push} brief={brief} names={names} />
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
    const vol = traded(m.volX)
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
    return fig([plainTerms(f.line || tidySubject(f.subject || '')).replace(/\.?$/, '.'), sizeWords(f)])
  return fig(itemLine(i).split(/(?<=\.) (?=[A-Z0-9])/))
}
// A quarter in a line or two: profit in rupees first (a turn from last quarter's loss said with it), then the margin
// on its own line when it moved a point or more
function resultsWords(r: any): string[] {
  // The quarter by its months ('July–September'), for a reader who doesn't count in fiscal quarters
  const pat = r.lines.find((l: any) => l.key === 'pat'), q = quarterMonths(r.quarter) || r.quarter.replace(/ FY\d\d$/, '')
  const turn = pat?.prev != null && pat.prev < 0 && pat.value >= 0
  const yoy = pat?.yoy != null ? `, ${pctWords(pat.yoy)} from a year earlier` : ''
  const profit = pat?.value == null ? `${q} results are out.` : `${q} profit was ₹${cr(pat.value)} crore${turn ? ' after a loss the quarter before' : ''}${yoy}.`
  const dm = r.ebitda_margin != null && r.yago_margin != null ? r.ebitda_margin - r.yago_margin : 0
  return Math.abs(dm) >= 1 ? [profit, `Operating margin (EBITDA margin) ${dm > 0 ? 'up' : 'down'} ${Math.abs(dm).toFixed(1)} percentage points.`] : [profit]
}

// What the window leaves to ask: the news first (a CFO leaving, a margin that fell), else the company's own question
// from its calls. One for each company that needed you, to copy into the call notes
function EndQuestions({ brief, push, names }: { brief: Brief; push: Push; names: Record<string, string> }) {
  const [qs, setQs] = useState<{ symbol: string; q: string; kind: Kind; topic?: Topic | null }[]>([])
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    let live = true
    const first = new Map<string, Item>(); brief.items.forEach(i => { if (!first.has(i.symbol)) first.set(i.symbol, i) })
    Promise.all([...first.values()].slice(0, 3).map(i => {
      // The news's question is a departure's or the numbers'; the company's own question from its calls is about guidance
      const q = newsQuestion(i, push)
      return q ? { symbol: i.symbol, q, kind: questionKind(i) ?? 'numbers' as Kind, topic: newsTopic(i, push) }
        : getCompany(i.symbol).then(c => c?.questions?.[0] ? { symbol: i.symbol, q: rupees(c.questions[0]), kind: 'numbers' as Kind, topic: topicOf(c.questions[0]) } : null).catch(() => null)
    })).then(xs => live && setQs(xs.filter((x): x is { symbol: string; q: string; kind: Kind; topic: Topic | null } => !!x)))
    return () => { live = false }
  }, [brief, push])
  if (!qs.length) return null
  const copy = () => navigator.clipboard?.writeText(`Questions worth asking\n${qs.map((x, k) => `${k + 1}. ${names[x.symbol]}: ${plainTerms(x.q)}`).join('\n')}`)
    .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return (
    <div className="end-qs">
      <h3 className="lbl">Questions worth asking</h3>
      <ol>{qs.map(x => <li key={x.symbol}><span className="end-co">{names[x.symbol]}</span><span>{plainTerms(x.q)}</span><NetAskFirst sym={x.symbol} kind={x.kind} topic={x.topic} /></li>)}</ol>
      {navigator.clipboard && <button className="end-copy" onClick={copy} aria-live="polite">{copied ? 'Copied' : 'Copy the questions'}</button>}
    </div>
  )
}

// What kind of thing a card is, in the label above its name
export function kindLabel(i: Item, push: Push): string {
  const f = i.story?.lead
  // A results-day move and the results it rides with read alike in every window
  const res = f?.results ?? (i.move?.explainedBy?.category === 'results' ? push.filings.filter(x => x.symbol === i.symbol && x.results && x.at.slice(0, 10) <= i.move!.d).sort((a, b) => b.at.localeCompare(a.at))[0]?.results : undefined)
  // Why it is here, as you would say it: the share price jumped or fell, or it only traded far more than usual.
  // The quarter is named in the sentence under the name, so the label leaves it out
  const moved = i.move && (i.move.why.includes('price') ? `Share price ${i.move.chg >= 0 ? 'jumped' : 'fell'}` : 'Unusually heavy trading')
  // Results that came with a CEO, CFO or MD change say so in the label ('Results, and a new CFO'); the months are
  // then left to the sentence, so the label stays on one line at 320
  const top = i.with?.lead.people && sortPeople(i.with.lead.people).find(p => p.seniority === 'top' && !reclass(p))
  const seat = top && shortRole(top.role).length <= 12 ? shortRole(top.role) : ''
  const more = seat ? (['appointed', 're-appointed', 'redesignated'].includes(top!.action) ? `, and a new ${seat}` : `, and the ${seat} leaves`) : ''
  if (res && (i.kind === 'results' || i.kind === 'move')) return moved ? `${moved === 'Unusually heavy trading' ? 'Heavy trading' : moved} after its results` : more ? `Results${more}` : `Results for ${quarterMonths(res.quarter) || res.quarter}`
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0], r = shortRole(p.role)
    return ['appointed', 're-appointed', 'redesignated'].includes(p.action) ? (r.length > 20 ? 'New director' : `New ${r}`) : 'A change in management'
  }
  if (i.kind === 'move') return moved || 'An unusual day'
  return CATEGORY_LABEL[i.story!.category] || 'Announcement'
}

// The card's sentence: the news in one or two facts. Volume and the line crossed are under the figure.
// The full view opens on the same words, so nothing changes under the eye as the card grows
export const cardSentence = (i: Item, fig: { body: string[] } | null) =>
  plainTerms((fig ? fig.body : [itemLine(i)]).filter(l => !/^It traded [\d.]+ times its usual amount/.test(l)).slice(0, 2).join(' '))

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
    <article className="card" ref={ref} data-key={i.key} onClick={tagClick(() => open(ref.current))}>
      {/* One picture: the month's line, ending on the day's move under its last close */}
      {line && <PriceLine bars={bars} end={fig && <Outcome size="xxs" value={v} unit={u} />} />}
      <div className="card-info">
        <div className="card-lbl"><span className="lbl">{kindLabel(i, push)}</span>{fresh && <span className="lbl lbl-new" title="New since you last looked">New</span>}</div>
        <h2 className="card-title">{name}</h2>
        {fig && !line && <div className="card-fig"><Outcome size="xs" value={v} unit={u} /><span className="card-cap">{figWhen(fig.d, i)}</span></div>}
        <p className="card-desc">{body}</p>
        {/* one grey line under the sentence: the alert level it passed, and how heavily it traded */}
        <p className="card-line">{rowTag(i, lines)}{line && i.move ? ` ${traded(i.move.volX)}` : ''}</p>
        <NetCardLine ids={[i.story?.lead?.id, i.with?.lead.id, i.move?.explainedBy?.id, ...(i.story?.filings.map(x => x.id) || [])]} sym={i.symbol} kind={questionKind(i)} />
        <div className="card-foot">
          <button className="read-more" onClick={() => open(ref.current)} aria-label={`Read more about ${name}`}>Read more</button>
          {!fig && <span className="lbl lbl-quiet">{shortDay(i.at)}</span>}
        </div>
      </div>
    </article>
  )
}
// A card the network raised: what it noticed across filings, titled with the companies, the person in the sentence.
// No price line and no figure: nothing moved. Last in the list, and outside the count of what needs you
function NetItemCard({ i, title, open }: { i: Item; title: string; open: (el: HTMLElement | null) => void }) {
  const ref = useRef<HTMLElement>(null)
  return (
    <article className="card card-netcard" ref={ref} data-key={i.key} onClick={tagClick(() => open(ref.current))}>
      <div className="card-info">
        <div className="card-lbl"><span className="lbl">People you know</span></div>
        <h2 className="card-title">{title}</h2>
        <p className="card-desc">{i.notice!.card!.line}</p>
        <div className="card-foot">
          <button className="read-more" onClick={() => open(ref.current)} aria-label={`Read more about ${title}`}>Read more</button>
          <span className="lbl lbl-quiet">{shortDay(i.at)} · Sample contacts</span>
        </div>
      </div>
    </article>
  )
}
// The card's picture: the month's closes, short. Its start says the period and what the month did ('Since 15 Sep,
// +4.1%'), so the big figure at its end reads as the one day it is dated to ('on 28 Oct'), not the month's return
// One label for one period, on a card and on its company's page alike
export const monthLabel = (bars: Bar[]) => `Since ${shortDay(bars[0].d)}, ${signed((bars[bars.length - 1].close / bars[0].close - 1) * 100)}`
export function PriceLine({ bars, end }: { bars: Bar[]; end?: ReactNode }) {
  const last = shortDay(bars[bars.length - 1].d)
  const month = monthLabel(bars)
  return <figure className="price"><SettleImg><Chart series={bars} /></SettleImg>
    <figcaption className="price-d"><span>{month}</span>{end ? <span className="price-end">{end}<span>on {last}</span></span> : <span>{last}</span>}</figcaption></figure>
}

// One date for a figure, the same in every window: the session it closed in, and how heavily it traded
export const figWhen = (d: string, i: Item) => `At the close on ${shortDay(d)}${i.move ? `. ${traded(i.move.volX)}` : ''}`

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
    // The network's card is read last, said as apart from what needs you
    const net = brief.net ? [`And one about people you know: ${netTitle(brief.net.notice!, names)}. ${brief.net.notice!.card!.line}`] : []
    const nCo = new Set(left.map(i => i.symbol)).size
    const text = left.length ? [`${nCo} of your companies ${nCo === 1 ? 'needs' : 'need'} a look today.`, ...left.map(spoken), ...net, 'That’s everything.'].join(' ') : ['Nothing passed your alert levels.', ...net].join(' ')
    const u = new SpeechSynthesisUtterance(said(text)); u.lang = 'en-IN'; u.rate = 1.02
    u.onend = () => setOn(false); u.onerror = () => setOn(false)
    utter.current = u; speechSynthesis.cancel(); speechSynthesis.speak(u); setOn(true)
  }
  return <button className="end-copy" onClick={say} aria-pressed={on} aria-label={on ? 'Stop reading aloud' : `Listen: ${left.length ? 'what needs a look' : 'today'}, read aloud`}>
    {on ? 'Stop reading' : 'Listen'}
  </button>
}


// Alerts on this phone: asks the browser once; when on, the top item arrives as a real notification straight away
export function AlertsRow({ top, names, lines }: { top?: Item; names: Record<string, string>; lines: Lines }) {
  const [on, setOn] = useState(alertsOn)
  const [note, setNote] = useState('')
  if (!canAlert()) return null
  const flip = async () => {
    if (on) { disableAlerts(); setOn(false); setNote(''); return }
    const r = await enableAlerts(top && { key: top.key, title: itemTitle(top, names[top.symbol]), body: `${itemLine(top)} ${crossedText(top, lines)}.` })
    setOn(r === 'on')
    setNote(r === 'denied' ? 'The browser said no. Allow notifications for this site in its settings.' : r === 'on' && top ? 'Sent the first one so you can see it.' : '')
  }
  const sub = note || (on ? 'On. New items arrive as notifications when FINN next opens with newer data' : alertsBlocked() ? 'Blocked in this browser’s settings' : 'Off. Turn on to get what passes your alert levels as notifications')
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
