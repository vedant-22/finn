// Ask: type or say a question about a company or the book. Answered from the ledgers FINN has built, with pages.
// A company FINN hasn't read yet is one tap from live research.
import { useEffect, useMemo, useRef, useState } from 'react'
import { aliases, matching, pace, parse, runningGuide, tally, verdictHead, yearToDate, type Known, type Parsed } from './question'
import { wordScore, getCompany, rupees, shortName, type Company, type Promise_, type Push } from './lib'
import { promiseLine } from './Trail'
import { Fold, Masthead, StatusLabel } from './ui'
import { BeforeAfter } from './Word'

// Every company FINN has a ledger for, with the names a question might use
let builtP: Promise<Record<string, string>> | null = null
const built = () => (builtP ??= fetch('/data/companies.json').then(r => r.json()).then(d => Array.isArray(d) ? Object.fromEntries(d.map((s: string) => [s, s])) : d).catch(() => ({})))
export function useKnown(push: Push) {
  const [b, setB] = useState<Record<string, string>>({})
  useEffect(() => { built().then(setB) }, [])
  return useMemo(() => {
    const names: Record<string, string> = {}
    const known: Known[] = []
    for (const p of push.portfolio) { names[p.symbol] = p.short || shortName(p.name); known.push({ symbol: p.symbol, names: aliases(p.symbol, p.name, p.short), held: true }) }
    for (const [s, n] of Object.entries(b)) if (!names[s]) { names[s] = shortName(n); known.push({ symbol: s, names: aliases(s, n) }) }
    return { known, names, ready: Object.keys(b).length > 0 }
  }, [push, b])
}

// Questions worth asking about one company, from what its ledger actually holds
export function suggestions(c: Company | null, name: string): string[] {
  if (!c) return []
  const hard = c.ledger.filter(p => p.hard && p.status !== 'unclear')
  const has = (m: string) => hard.some(p => p.metric === m)
  const out: string[] = []
  if (has('margin')) out.push(`Did ${name} deliver on margins?`)
  if (has('revenue_growth')) out.push(`Did ${name} deliver on revenue growth?`)
  if (hard.some(p => ['missed', 'partly', 'quiet'].includes(p.status))) out.push(`What has ${name} missed?`)
  const fy = hard.filter(p => p.status === 'pending').map(p => p.by_when.match(/FY ?(\d\d)/)?.[1]).find(Boolean)
  if (fy) out.push(`What has ${name} promised for FY${fy}?`)
  if (has('capacity') || has('capex')) out.push(`Did ${name} deliver on capacity?`)
  return out.slice(0, 3)
}

// Look up, as v4 had it: one big field for a symbol or a name, and the companies ready to open as warm tiles.
// A question typed in the same field is answered here, from the ledgers, with pages.
const QUESTION = /\?\s*$|^(who|what|which|did|has|have|is|are|how|when|why|does|do)\b/i
export function AskScreen({ push, q0, openCompany }: { push: Push; q0?: string; openCompany: (s: string, pid?: number) => void }) {
  const { known, names } = useKnown(push)
  const [q, setQ] = useState('')
  const [asked, setAsked] = useState(q0 || '')
  const [more, setMore] = useState(false)
  const inRef = useRef<HTMLInputElement>(null)
  useEffect(() => { if (q0) { setQ(''); setAsked(q0) } }, [q0])
  const recent: string[] = JSON.parse(localStorage.getItem('finn.recent') || '[]')
  const held = new Set(push.portfolio.map(p => p.symbol))
  const all = Object.keys(names)
  const others = all.filter(s => !held.has(s)).sort((a, b) => names[a].localeCompare(names[b]))
  // Typing a name ('pidilite') finds the symbol FINN already knows (PIDILITIND); 'Ltd' and friends match nothing
  const isQ = (t: string) => QUESTION.test(t.trim()) || t.trim().split(/\s+/).length >= 4
  const want = q.trim().toUpperCase().replace(/\.(NS|BO)$/, '')
  const fold = (x: string) => x.toUpperCase().replace(/[^A-Z0-9]/g, '')
  const FILLER_WORDS = new Set(['LTD', 'LIMITED', 'THE', 'OF', 'AND', 'CO', 'PVT'])
  const full = (s: string) => known.find(k => k.symbol === s)?.names.join(' ') || names[s] || ''
  const matches = isQ(q) || fold(want).length < 2 ? [] : all.filter(s => s !== want && [s, fold(names[s] || ''), ...full(s).toUpperCase().split(/[^A-Z0-9]+/).filter(w => !FILLER_WORDS.has(w))].some(x => x.startsWith(fold(want))))
  const submit = (text: string) => {
    const t = text.trim()
    if (!t) { inRef.current?.focus(); return }
    if (isQ(t)) { setQ(''); setAsked(t); inRef.current?.blur(); return }
    const sym = t.toUpperCase().replace(/\.(NS|BO)$/, '').replace(/\s+/g, '')
    openCompany(!all.includes(sym) && matches.length === 1 && fold(sym).length >= 4 ? matches[0] : sym)
  }
  const starters = ['Who missed a promise?', 'Who has gone quiet?', 'Did L&T deliver on revenue growth?', 'What has Syngene promised for FY27?']
  return (
    <main className="screen look">
      <Masthead />
      <header className="banner">
        <h1>Look up any NSE company</h1>
        <p>FINN reads its last five earnings calls and filed results, and checks each promise against what happened.</p>
      </header>
      <form className="look-form" onSubmit={e => { e.preventDefault(); submit(q) }}>
        <label htmlFor="sym" className="lbl lbl-quiet">NSE symbol, name or a question</label>
        <div className="look-row">
          <div className="look-field">
            <input id="sym" ref={inRef} value={q} onChange={e => setQ(e.target.value)} placeholder={asked ? 'Ask another' : 'ASTRAL, or a question'} autoComplete="off" autoCorrect="off" spellCheck={false} enterKeyHint="search" className={isQ(q) ? 'is-q' : ''} />
            <Mic onText={t => { setQ(t); submit(t) }} />
          </div>
          <button type="submit" className="btn-primary">{isQ(q) || (asked && !q) ? 'Ask' : 'Check their word'}</button>
        </div>
      </form>
      {matches.length > 0 && <section className="chips-sec"><h2 className="lbl lbl-quiet">{matches.length === 1 && !all.includes(want) ? 'Did you mean' : 'Matches'}</h2>
        <div className="chips">{matches.slice(0, 6).map(s => <button key={s} className="btn-outline" onClick={() => openCompany(s)}>{names[s] || s}</button>)}</div></section>}
      {asked && <section className="look-answer"><Answer key={asked} q={asked} known={known} names={names} openCompany={openCompany} /></section>}
      {!asked && recent.length > 0 && <Tiles title="Recent" syms={recent.slice(0, 4)} open={openCompany} names={names} />}
      {!asked && others.length > 0 && <Tiles title="Ready to open" syms={others} open={openCompany} names={names} />}
      {!asked && <Fold title="Ask about your book" open={more} toggle={() => setMore(!more)}>
        <ul className="notes">{starters.map(x => <li key={x}><button className="note note-q" onClick={() => submit(x)}><span className="note-co">{x}</span></button></li>)}</ul>
      </Fold>}
    </main>
  )
}

// A hairline row for each company FINN has read: its name over its symbol, and its word in one figure
function Tiles({ title, syms, open, names }: { title: string; syms: string[]; open: (s: string) => void; names: Record<string, string> }) {
  const [rec, setRec] = useState<Record<string, string>>({})
  useEffect(() => {
    let live = true
    syms.forEach(s => getCompany(s).then(c => {
      const w = wordScore(c ?? undefined)
      if (!live || !w) return
      setRec(r => ({ ...r, [s]: w.graded ? `${Math.floor(w.kept)} of ${w.graded} kept` : w.hard ? 'None due yet' : 'Nothing to grade' }))
    }).catch(() => {}))
    return () => { live = false }
  }, [syms.join()])  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="tiles-sec"><h2 className="sec-head">{title}</h2>
      <ul className="tiles">{syms.map(s => <li key={s}><button className="tile" onClick={() => open(s)}><span className="tile-txt"><span className="tile-name">{names[s] || s}</span><span className="lbl lbl-quiet">{s}</span></span><span className="tile-rec">{rec[s] || '\u00a0'}</span></button></li>)}</ul>
    </section>
  )
}


// Speech in, where the browser has it (Chrome, Safari). Hidden where it doesn't.
function Mic({ onText }: { onText: (t: string) => void }) {
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  const [on, setOn] = useState(false)
  const rec = useRef<any>(null)
  if (!SR) return null
  const start = () => {
    if (on) { rec.current?.stop(); return }
    const r = new SR(); rec.current = r
    r.lang = 'en-IN'; r.interimResults = false; r.maxAlternatives = 1
    r.onresult = (e: any) => onText(e.results[0][0].transcript)
    r.onend = () => setOn(false); r.onerror = () => setOn(false)
    setOn(true); r.start()
  }
  return <button type="button" className={`ask-mic${on ? ' on' : ''}`} aria-label={on ? 'Stop listening' : 'Ask by voice'} aria-pressed={on} onClick={start}>
    <svg viewBox="0 0 20 20" aria-hidden><rect x="7.5" y="2.5" width="5" height="9.5" rx="2.5" /><path d="M4.5 9.5a5.5 5.5 0 0 0 11 0M10 15v2.5" /></svg>
  </button>
}

// One answer. A company question shows that company's promises on the topic as before-and-afters;
// a book question lists the promises across every holding; an unknown symbol offers to read it.
// The question stays in view above its answer: the field scrolls it out of sight
export function Answer(props: { q: string; known: Known[]; names: Record<string, string>; openCompany: (s: string, pid?: number) => void; inline?: boolean }) {
  return <>{!props.inline && <p className="small answer-q">{props.q}</p>}<Answered {...props} /></>
}
function Answered({ q, known, names, openCompany, inline }: { q: string; known: Known[]; names: Record<string, string>; openCompany: (s: string, pid?: number) => void; inline?: boolean }) {
  const p = useMemo(() => parse(q, known), [q, known])
  if (p.symbol) return <CompanyAnswer p={p} name={names[p.symbol] || p.symbol} openCompany={openCompany} inline={inline} />
  if (p.ticker) return (
    <section className="answer" aria-live="polite">
      <h2 className="t-b1">FINN hasn’t read {p.ticker} yet</h2>
      <p>Reading its last earnings calls and filed results takes about a minute. Every promise comes back graded, with its page.</p>
      <button className="btn-primary" onClick={() => openCompany(p.ticker!)}>Read {p.ticker}</button>
    </section>
  )
  return <BookAnswer p={p} known={known} names={names} openCompany={openCompany} />
}

function CompanyAnswer({ p, name, openCompany, inline }: { p: Parsed; name: string; openCompany: (s: string, pid?: number) => void; inline?: boolean }) {
  const [c, setC] = useState<Company | null | undefined>(undefined)
  useEffect(() => { getCompany(p.symbol!).then(setC).catch(() => setC(null)) }, [p.symbol])
  if (c === undefined) return <section className="answer"><div className="skel skel-line" /><div className="skel skel-block" /></section>
  if (c === null) return (
    <section className="answer" aria-live="polite">
      <h2 className="t-b1">{name}</h2>
      <p>FINN hasn’t read {name}’s calls yet. It takes about a minute.</p>
      <button className="btn-primary" onClick={() => openCompany(p.symbol!)}>Read {name}</button>
    </section>
  )
  // A question about something no topic covers is answered only by promises that name it; none, and it says so
  const restRe = !p.topic && p.rest ? new RegExp(p.rest.split(' ').map(w => w.replace(/s$/, '')).join('|'), 'i') : null
  const xs = matching(c.ledger, p).filter(x => !restRe || restRe.test(`${x.topic} ${x.target}`))
  const about = p.topic ? ` on ${p.topic.label}` : p.rest ? ` on ${p.rest}` : ''
  const fy = p.fy ? ` for ${p.fy}` : ''
  const shown = xs.slice(0, inline ? 2 : 4)
  const calls = c.calls.filter(x => !x.error).length
  // Settled promises answer 'did they deliver'; this year's revenue guide says how the running one is going
  const due = xs.length > 0 && xs.every(x => x.status !== 'pending')
  const last = c.quarters?.[c.quarters.length - 1]
  const run = p.intent !== 'due' && (!p.topic || p.topic.metrics.includes('revenue_growth')) ? runningGuide(c.ledger, last?.q) : undefined
  // The running guide, read against revenue for the year so far
  const ytd = yearToDate(c.quarters || [])
  const sofar = run && ytd && ytd.fy === run.fy && !xs.includes(run.g) ? pace(run.g, ytd.growth) : null
  const range = run ? rupees(run.g.target).match(/[\d.]+(?:–\u2060?[\d.]+)?%/)?.[0] : ''
  const runLine = run && ytd && sofar ? `Revenue is ${sofar} so far for their ${run.fy} guide of ${range} growth: up ${ytd.growth.toFixed(1)}% in ${ytd.label}. ` : ''
  return (
    <section className="answer" aria-live="polite">
      <h2 className="t-b1">{name}{about}{fy}{xs.length ? `: ${verdictHead(xs)}${sofar ? `; ${run!.fy} ${sofar} so far` : ''}` : ''}</h2>
      {xs.length
        ? <p className="sub">{due ? (xs.length === 1 ? 'One promise on this has come due' : `${xs.length} promises on this have come due`) : xs.length === 1 ? 'One promise on this' : `${xs.length} promises on this`}: {xs.length === 1 ? tally(xs).replace(/^1 /, '') : tally(xs)}. {runLine}{(s => s?.graded ? `Over their last ${calls} calls they’ve kept ${Math.floor(s.kept)} of ${s.graded} promises that came due.` : `From their last ${calls} calls.`)(wordScore(c))}</p>
        : <p><b className="not-found">Not found in the filings.</b> Nothing{about}{fy} with a number and a date in {name}’s last {c.calls.filter(x => !x.error).length} calls. FINN answers only from what management put on record.</p>}
      {shown.map(x => <BeforeAfter key={x.id} p={x} compact={inline} lead src={c.source} />)}
      {!xs.length && <Others c={c} open={pid => openCompany(c.symbol, pid)} />}
      <button className="see" onClick={() => openCompany(c.symbol, shown[0]?.id)}>{xs.length > shown.length ? `All ${xs.length}, and the rest of their record` : `${name}’s full record`}</button>
    </section>
  )
}

// When the question has no answer, what they did promise: three, weakest first
function Others({ c, open }: { c: Company; open: (pid: number) => void }) {
  const xs = matching(c.ledger, { intent: null }).slice(0, 3)
  if (!xs.length) return null
  return <>
    <h3 className="lbl lbl-quiet ask-other">What they did promise</h3>
    <ul className="rows">{xs.map(x => <li key={x.id}><button className="row row-2" onClick={() => open(x.id)}><span>{promiseLine(x)}</span><StatusLabel status={x.status} /></button></li>)}</ul>
  </>
}

function BookAnswer({ p, known, names, openCompany }: { p: Parsed; known: Known[]; names: Record<string, string>; openCompany: (s: string, pid?: number) => void }) {
  const [rows, setRows] = useState<{ sym: string; x: Promise_ }[] | null>(null)
  useEffect(() => {
    let live = true
    Promise.all(known.map(k => getCompany(k.symbol).catch(() => null))).then(cs => {
      if (!live) return
      // A book question with no verdict word asks what's gone wrong
      const want = { ...p, intent: p.intent ?? 'missed' as const }
      setRows(cs.flatMap(c => c ? matching(c.ledger, want).map(x => ({ sym: c.symbol, x })) : []))
    })
    return () => { live = false }
  }, [p, known])
  if (!rows) return <section className="answer"><div className="skel skel-line" /><div className="skel skel-block" /></section>
  // 'Your whole book' means the holdings: they come first and in full; companies read beyond the book follow
  const held = new Set(known.filter(k => k.held).map(k => k.symbol))
  const mine = rows.filter(r => held.has(r.sym)), other = rows.filter(r => !held.has(r.sym))
  const cos = new Set(mine.map(r => r.sym)).size
  const what = p.intent === 'quiet' ? 'gone quiet' : p.intent === 'due' ? 'still due' : p.intent === 'delivered' ? 'settled' : 'missed or partly kept'
  const on = p.topic ? ` on ${p.topic.label}` : ''
  const row = ({ sym, x }: { sym: string; x: Promise_ }) => (
    <li key={sym + x.id}><button className="row row-2" onClick={() => openCompany(sym, x.id)}>
      <span><b className="row-co">{names[sym] || sym}</b> {promiseLine(x)}</span><StatusLabel status={x.status} />
    </button></li>
  )
  return (
    <section className="answer" aria-live="polite">
      <h2 className="t-b1">{mine.length ? `${mine.length} ${mine.length === 1 ? 'promise' : 'promises'} ${what}${on}` : `Nothing ${what}${on} in your book`}</h2>
      <p className="sub">{mine.length ? `At ${cos} of your ${held.size} holdings.` : `Across your ${held.size} holdings.`}</p>
      {mine.length > 0 && <ul className="rows">{mine.map(row)}</ul>}
      {other.length > 0 && <>
        <h3 className="lbl lbl-quiet ask-other">Outside your book</h3>
        <ul className="rows">{other.slice(0, 6).map(row)}</ul>
        {other.length > 6 && <p className="small">{other.length - 6} more at companies outside your book.</p>}
      </>}
    </section>
  )
}
