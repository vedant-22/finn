// Ask: type or say a question about a company or the book. Answered from the ledgers FINN has built, with pages.
// A company FINN hasn't read yet is one tap from live research.
import { useEffect, useMemo, useRef, useState } from 'react'
import { aliases, matching, pace, parse, runningGuide, tally, verdictHead, yearToDate, type Known, type Parsed } from './question'
import { wordScore, getCompany, rupees, shortName, type Company, type Promise_, type Push } from './lib'
import { promiseLine } from './Trail'
import { StatusLabel } from './ui'
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

export function AskScreen({ push, q0, openCompany }: { push: Push; q0?: string; openCompany: (s: string, pid?: number) => void }) {
  const { known, names } = useKnown(push)
  const [q, setQ] = useState('')
  const [asked, setAsked] = useState(q0 || '')
  const inRef = useRef<HTMLInputElement>(null)
  useEffect(() => { if (q0) { setQ(''); setAsked(q0) } }, [q0])
  // Asked, the question moves out of the field to sit whole above its answer; the field is ready for the next one
  const submit = (text: string) => { const t = text.trim(); if (!t) { inRef.current?.focus(); return } setQ(''); setAsked(t); inRef.current?.blur() }
  const starters = ['Who missed a promise?', 'Who has gone quiet?', 'Did L&T deliver on revenue growth?', 'What has Syngene promised for FY27?']
  // When an idea comes up: the companies FINN has read beyond the book, then one it hasn't, to show any symbol works
  const outside = Object.keys(names).filter(s => !push.portfolio.some(p => p.symbol === s)).sort((a, b) => names[a].localeCompare(names[b]))
  return (
    <main className="screen ask-screen">
      <div className="band band-top">
        <header className="page-head">
          <h1 className="title">Ask</h1>
          <p className="sub">About a company or your whole book. Answers come from earnings calls and filed results, with the page.</p>
        </header>
        <form className="ask-form" onSubmit={e => { e.preventDefault(); submit(q) }}>
          <label htmlFor="ask" className="sr-only">Your question</label>
          <input id="ask" ref={inRef} value={q} onChange={e => setQ(e.target.value)} placeholder={asked ? 'Ask another question' : 'Did L&T deliver on margins?'} autoComplete="off" autoCorrect="off" spellCheck={false} enterKeyHint="search" />
          <Mic onText={t => { setQ(t); submit(t) }} />
          <button type="submit" className="ask-go" aria-label="Ask"><svg viewBox="0 0 16 16" aria-hidden><path d="M3 8h9.5M8.5 3.5L13 8l-4.5 4.5" /></svg></button>
        </form>
      </div>
      {asked
        ? <Answer key={asked} q={asked} known={known} names={names} openCompany={openCompany} />
        : <section className="ask-try" aria-label="Try">
            <h2 className="head">Try</h2>
            <ul className="rows">{starters.map(s => <li key={s}><button className="row" onClick={() => submit(s)}><span>{s}</span><Arrow /></button></li>)}</ul>
            {outside.length > 0 && <>
              <h2 className="head ask-out">Outside your book</h2>
              <p className="sub">Any NSE symbol works. One FINN hasn’t read takes about a minute.</p>
              <ul className="rows">
                {outside.map(s => <li key={s}><button className="row" onClick={() => openCompany(s)}><span>{names[s]}</span><span className="small">{s}</span><Arrow /></button></li>)}
                <li><button className="row" onClick={() => submit('ASTRAL')}><span>ASTRAL</span><span className="small">Not read yet</span><Arrow /></button></li>
              </ul>
            </>}
          </section>}
    </main>
  )
}

const Arrow = () => <svg className="arrow" viewBox="0 0 16 16" aria-hidden><path d="M6 3.5l4.5 4.5L6 12.5" /></svg>

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
      <h2 className="head">FINN hasn’t read {p.ticker} yet</h2>
      <p>Reading its last earnings calls and filed results takes about a minute. Every promise comes back graded, with its page.</p>
      <button className="btn" onClick={() => openCompany(p.ticker!)}>Read {p.ticker}</button>
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
      <h2 className="head">{name}</h2>
      <p>FINN hasn’t read {name}’s calls yet. It takes about a minute.</p>
      <button className="btn" onClick={() => openCompany(p.symbol!)}>Read {name}</button>
    </section>
  )
  const xs = matching(c.ledger, p)
  const about = p.topic ? ` on ${p.topic.label}` : ''
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
      <h2 className="head">{name}{about}{fy}{xs.length ? `: ${verdictHead(xs)}${sofar ? `; ${run!.fy} ${sofar} so far` : ''}` : ''}</h2>
      {xs.length
        ? <p className="sub">{due ? (xs.length === 1 ? 'One promise on this has come due' : `${xs.length} promises on this have come due`) : xs.length === 1 ? 'One promise on this' : `${xs.length} promises on this`}: {xs.length === 1 ? tally(xs).replace(/^1 /, '') : tally(xs)}. {runLine}{(s => s?.graded ? `Over their last ${calls} calls they’ve kept ${Math.floor(s.kept)} of ${s.graded} promises that came due.` : `From their last ${calls} calls.`)(wordScore(c))}</p>
        : <p>Nothing{about}{fy} with a number and a date in {name}’s last {c.calls.filter(x => !x.error).length} calls. FINN only grades what management put a number or date on.</p>}
      {shown.map(x => <BeforeAfter key={x.id} p={x} compact={inline} lead src={c.source} />)}
      {!xs.length && <Others c={c} open={pid => openCompany(c.symbol, pid)} />}
      <button className="link" onClick={() => openCompany(c.symbol, shown[0]?.id)}>{xs.length > shown.length ? `All ${xs.length}, and the rest of their record` : `${name}’s full record`}<Arrow /></button>
    </section>
  )
}

// When the question has no answer, what they did promise: three, weakest first
function Others({ c, open }: { c: Company; open: (pid: number) => void }) {
  const xs = matching(c.ledger, { intent: null }).slice(0, 3)
  if (!xs.length) return null
  return <>
    <h3 className="small kicker">What they did promise</h3>
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
      <h2 className="head">{mine.length ? `${mine.length} ${mine.length === 1 ? 'promise' : 'promises'} ${what}${on}` : `Nothing ${what}${on} in your book`}</h2>
      <p className="sub">{mine.length ? `At ${cos} of your ${held.size} holdings.` : `Across your ${held.size} holdings.`}</p>
      {mine.length > 0 && <ul className="rows">{mine.map(row)}</ul>}
      {other.length > 0 && <>
        <h3 className="small kicker ask-other">Outside your book</h3>
        <ul className="rows">{other.slice(0, 6).map(row)}</ul>
        {other.length > 6 && <p className="small">{other.length - 6} more at companies outside your book.</p>}
      </>}
    </section>
  )
}
