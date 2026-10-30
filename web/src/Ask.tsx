// Ask: type or say a question about a company or the book. Answered from the ledgers FINN has built, with pages.
// A company FINN hasn't read yet is one tap from live research.
import { useEffect, useMemo, useRef, useState } from 'react'
import { aliases, matching, parse, tally, type Known, type Parsed } from './question'
import { getCompany, shortName, type Company, type Promise_, type Push } from './lib'
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
    for (const p of push.portfolio) { names[p.symbol] = p.short || shortName(p.name); known.push({ symbol: p.symbol, names: aliases(p.symbol, p.name, p.short) }) }
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
  const [q, setQ] = useState(q0 || '')
  const [asked, setAsked] = useState(q0 || '')
  const inRef = useRef<HTMLInputElement>(null)
  useEffect(() => { if (q0) { setQ(q0); setAsked(q0) } }, [q0])
  const submit = (text: string) => { const t = text.trim(); if (!t) { inRef.current?.focus(); return } setQ(t); setAsked(t); inRef.current?.blur() }
  const starters = ['Who missed a promise?', 'Who has gone quiet?', 'Did L&T deliver on revenue growth?', 'What has Syngene promised for FY27?', 'ASTRAL']
  return (
    <main className="screen ask-screen">
      <header className="page-head">
        <h1 className="title">Ask</h1>
        <p className="sub">About a company or your whole book. Answers come from earnings calls and filed results, with the page.</p>
      </header>
      <form className="ask-form" onSubmit={e => { e.preventDefault(); submit(q) }}>
        <label htmlFor="ask" className="sr-only">Your question</label>
        <input id="ask" ref={inRef} value={q} onChange={e => setQ(e.target.value)} placeholder="Did L&T deliver on margins?" autoComplete="off" autoCorrect="off" spellCheck={false} enterKeyHint="search" />
        <Mic onText={t => { setQ(t); submit(t) }} />
        <button type="submit" className="ask-go" aria-label="Ask"><svg viewBox="0 0 16 16" aria-hidden><path d="M3 8h9.5M8.5 3.5L13 8l-4.5 4.5" /></svg></button>
      </form>
      {asked
        ? <Answer key={asked} q={asked} known={known} names={names} openCompany={openCompany} />
        : <section className="ask-try" aria-label="Try">
            <h2 className="head">Try</h2>
            <ul className="rows">{starters.map(s => <li key={s}><button className="row" onClick={() => submit(s)}><span>{s === 'ASTRAL' ? 'ASTRAL, a company FINN hasn’t read' : s}</span><Arrow /></button></li>)}</ul>
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
export function Answer({ q, known, names, openCompany, inline }: { q: string; known: Known[]; names: Record<string, string>; openCompany: (s: string, pid?: number) => void; inline?: boolean }) {
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
  return (
    <section className="answer" aria-live="polite">
      <h2 className="head">{name}{about}{fy}</h2>
      {xs.length
        ? <p className="sub">{tally(xs)}, from the last {c.calls.filter(x => !x.error).length} earnings calls.</p>
        : <p>Nothing{about}{fy} with a number and a date in {name}’s last {c.calls.filter(x => !x.error).length} calls. FINN only grades what management put a number or date on.</p>}
      {shown.map(x => <BeforeAfter key={x.id} p={x} compact={inline} lead />)}
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
  const cos = [...new Set(rows.map(r => r.sym))]
  const what = p.intent === 'quiet' ? 'gone quiet' : p.intent === 'due' ? 'still due' : p.intent === 'delivered' ? 'settled' : 'missed or partly kept'
  return (
    <section className="answer" aria-live="polite">
      <h2 className="head">{rows.length ? `${rows.length} ${rows.length === 1 ? 'promise' : 'promises'} ${what}${p.topic ? ` on ${p.topic.label}` : ''}` : `Nothing ${what}${p.topic ? ` on ${p.topic.label}` : ''}`}</h2>
      <p className="sub">{rows.length ? `At ${cos.length} ${cos.length === 1 ? 'company' : 'companies'} FINN has read.` : 'Across every company FINN has read.'}</p>
      <ul className="rows">{rows.slice(0, 12).map(({ sym, x }) => (
        <li key={sym + x.id}><button className="row row-2" onClick={() => openCompany(sym, x.id)}>
          <span><b className="row-co">{names[sym] || sym}</b> {promiseLine(x)}</span><StatusLabel status={x.status} />
        </button></li>
      ))}</ul>
    </section>
  )
}
