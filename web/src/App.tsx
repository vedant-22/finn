import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { CompanyView } from './CompanyView'
import { Book } from './Book'
import { BriefScreen } from './Brief'
import { AskHere, Reader } from './Reader'
import { AskScreen } from './Ask'
import { buildBrief, loadDone, saveDone, type Done } from './queue'
import {
  buildLive, CATEGORY_LABEL, plainError, DEFAULT_LINES, forgetCompanies, getCompany, getPush, loadLines, saveLines, shortName,
  type Bar, type Company, type Lines, type Push, type Step,
} from './lib'
import { BackBar, Mark, Sheet, useEdgeBack } from './ui'

type Tab = 'brief' | 'book' | 'ask'
type Route = { tab: Tab; sym?: string; pid?: number; read?: boolean; q?: string }
const parse = (): Route => {
  const [path, query] = location.hash.replace(/^#\/?/, '').split('?')
  const h = path.split('/')
  if (h[0] === 'c' && h[1]) return { tab: 'brief', sym: h[1].toUpperCase(), pid: h[2] && /^\d+$/.test(h[2]) ? +h[2] : undefined }
  if (h[0] === 'read') return { tab: 'brief', read: true }
  if (h[0] === 'book') return { tab: 'book' }
  if (h[0] === 'ask' || h[0] === 'look') return { tab: 'ask', q: new URLSearchParams(query || '').get('q') || undefined }
  return { tab: 'brief' }
}

export function App() {
  const [route, setRoute] = useState<Route>(parse)
  const [push, setPush] = useState<Push | null>(null)
  const [err, setErr] = useState('')
  const [lines, setLinesState] = useState<Lines>(loadLines)
  const [done, setDoneState] = useState<Done>(loadDone)
  const [linesOpen, setLinesOpen] = useState(false)
  const [readFrom, setReadFrom] = useState<string | undefined>()
  const [prev, setPrev] = useState<string>('')
  const scrolls = useRef(new Map<string, number>())
  const toY = useRef(0)

  useEffect(() => { getPush().then(setPush).catch(e => setErr(e.message)) }, [])
  // From the home screen there is no reload. Coming back after a while, pick up a newer snapshot if there is one.
  useEffect(() => {
    let last = Date.now()
    const on = () => {
      if (document.visibilityState !== 'visible' || Date.now() - last < 15 * 60e3) return
      last = Date.now()
      getPush(true).then(p => setPush(cur => {
        if (cur && cur.asof === p.asof) return cur
        forgetCompanies(); return p
      })).catch(() => { /* keep what's on screen */ })
    }
    document.addEventListener('visibilitychange', on); return () => document.removeEventListener('visibilitychange', on)
  }, [])
  useEffect(() => {
    // Back from a company returns to where the list was; anything else starts at the top
    const on = (e: HashChangeEvent) => {
      const from = new URL(e.oldURL).hash || '#/'
      scrolls.current.set(from, window.scrollY)
      const r = parse()
      if (r.sym && !from.startsWith('#/c/')) setPrev(from)
      const back = (from.startsWith('#/c/') && !r.sym) || from.startsWith('#/read')
      toY.current = back ? scrolls.current.get(location.hash || '#/') ?? 0 : r.read ? window.scrollY : 0
      setLinesOpen(false)
      setRoute(r)
    }
    window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on)
  }, [])
  useLayoutEffect(() => { window.scrollTo(0, toY.current) }, [route])
  const setLines = (l: Lines) => { setLinesState(l); saveLines(l) }
  const setDone = (d: Done) => { setDoneState(d); saveDone(d) }
  const openCompany = useCallback((s: string, pid?: number) => { location.hash = `#/c/${s}${pid != null ? `/${pid}` : ''}` }, [])
  const go = (t: Tab) => {
    const h = t === 'brief' ? '#/' : `#/${t}`
    if ((location.hash || '#/') === h) window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    else location.hash = h
  }
  const brief = useMemo(() => push ? buildBrief(push, lines) : null, [push, lines])
  const names = useMemo(() => Object.fromEntries((push?.portfolio || []).map(p => [p.symbol, p.short || shortName(p.name)])), [push])

  if (err) return <div className="boot"><Mark /><p>Couldn’t load your filings. {plainError(err)}</p><button className="btn" onClick={() => location.reload()}>Try again</button></div>
  if (!push || !brief) return <BootSkeleton />
  const holding = (s?: string) => push.portfolio.find(p => p.symbol === s)
  const tab: Tab = !route.sym ? route.tab : prev.startsWith('#/book') ? 'book' : prev.startsWith('#/ask') ? 'ask' : prev ? 'brief' : holding(route.sym) ? 'book' : 'ask'
  const openReader = (key?: string) => { setReadFrom(key); location.hash = '#/read' }
  const closeReader = () => { if (history.length > 1 && route.read) history.back(); else location.hash = '#/' }

  return (
    <>
      {route.sym
        ? <CompanyRoute push={push} openCompany={openCompany} sym={route.sym} pid={route.pid} sector={holding(route.sym)?.sector} title={holding(route.sym)?.short} close={push.eod[route.sym]?.[push.eod[route.sym].length - 1]} bars={push.eod[route.sym]} back={() => { location.hash = !prev || prev === location.hash ? '#/' : prev }} />
        : route.tab === 'book' ? <Book push={push} openCompany={openCompany} />
          : route.tab === 'ask' ? <AskScreen push={push} q0={route.q} openCompany={openCompany} />
            : <BriefScreen push={push} brief={brief} done={done} setDone={setDone} lines={lines} setLines={setLines} names={names} openReader={openReader} openLines={() => setLinesOpen(true)} />}

      {route.read && <Reader push={push} brief={brief} done={done} setDone={setDone} lines={lines} names={names} start={readFrom}
        close={closeReader} openCompany={openCompany} openLines={() => setLinesOpen(true)} />}

      {!route.read && <nav className="tabs" aria-label="Sections">
        {([['brief', 'Brief'], ['book', 'Book'], ['ask', 'Ask']] as [Tab, string][]).map(([t, label]) => (
          <button key={t} className={tab === t ? 'on' : ''} aria-current={tab === t ? 'page' : undefined} onClick={() => go(t)}>{label}</button>
        ))}
      </nav>}

      <Sheet open={linesOpen} onClose={() => setLinesOpen(false)} title="Your lines">
        <LinesForm lines={lines} setLines={setLines} count={brief.items.length + brief.spill.length} shown={brief.items.length} />
      </Sheet>
    </>
  )
}

// The first paint, before the snapshot arrives: the brief's shape in grey
function BootSkeleton() {
  return (
    <main className="screen brief" aria-busy="true" aria-label="Loading the brief">
      <header className="top"><Mark label="FINN, loading" /></header>
      <section className="hero"><div className="skel skel-line short" /><div className="skel skel-fig" /><div className="skel skel-line" /><div className="skel skel-line short" /></section>
      <section className="sec"><div className="skel skel-notif" /><div className="skel skel-notif" /></section>
    </main>
  )
}

function LinesForm({ lines, setLines, count, shown }: { lines: Lines; setLines: (l: Lines) => void; count: number; shown: number }) {
  const toggle = (c: string) => setLines({ ...lines, interrupt: lines.interrupt.includes(c) ? lines.interrupt.filter(x => x !== c) : [...lines.interrupt, c] })
  return (
    <div className="lines">
      <p className="sub">FINN puts something in the brief only when it crosses one of these. With these lines, <b className="num">{count}</b> {count === 1 ? 'thing crosses' : 'things cross'} in this window{count > shown ? `; the brief leads with ${shown} and lists the rest under Worth a line` : ''}.</p>
      <Stepper label="Volume above its 20-day average" value={lines.volX} step={0.5} min={1.5} max={6} fmt={v => `${v}×`} set={v => setLines({ ...lines, volX: v })} />
      <Stepper label="Price move in a day" value={lines.movePct} step={1} min={1} max={15} fmt={v => `±${v}%`} set={v => setLines({ ...lines, movePct: v })} />
      <h3 className="lbl lbl-quiet">Filings that can interrupt</h3>
      <ul className="checks">
        {['results', 'management_change', 'M&A', 'litigation', 'fund_raise', 'credit_rating', 'capex', 'insider_trading'].map(c => (
          <li key={c}>
            <label><span>{CATEGORY_LABEL[c]}</span><input type="checkbox" role="switch" checked={lines.interrupt.includes(c)} onChange={() => toggle(c)} /></label>
          </li>
        ))}
      </ul>
      <button className="text-btn" onClick={() => setLines({ ...DEFAULT_LINES, hours: lines.hours })}>Reset to defaults</button>
    </div>
  )
}

function Stepper({ label, value, step, min, max, fmt, set }: { label: string; value: number; step: number; min: number; max: number; fmt: (v: number) => string; set: (v: number) => void }) {
  return (
    <div className="stepper">
      <span>{label}</span>
      <div className="stepper-ctl">
        <button aria-label={`Lower ${label}`} disabled={value <= min} onClick={() => set(Math.max(min, +(value - step).toFixed(1)))}>−</button>
        <output className="num">{fmt(value)}</output>
        <button aria-label={`Raise ${label}`} disabled={value >= max} onClick={() => set(Math.min(max, +(value + step).toFixed(1)))}>+</button>
      </div>
    </div>
  )
}

function CompanyRoute({ push, openCompany, sym, pid, sector, title, close, bars, back }: { push: Push; openCompany: (s: string, pid?: number) => void; sym: string; pid?: number; sector?: string; title?: string; close?: { d: string; close: number }; bars?: Bar[]; back: () => void }) {
  const [c, setC] = useState<Company | null | undefined>(undefined)
  const [steps, setSteps] = useState<Step[]>([])
  const [failed, setFailed] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [slow, setSlow] = useState(false)
  useEdgeBack(back)
  useEffect(() => { setSlow(false); const t = setTimeout(() => setSlow(true), 400); return () => clearTimeout(t) }, [sym, attempt])
  useEffect(() => {
    let live = true
    setC(undefined); setSteps([]); setFailed('')
    getCompany(sym).then(found => {
      if (!live) return
      if (found) { setC(found); return }
      buildLive(sym, s => live && setSteps(s)).then(x => live && setC(x)).catch(e => live && setFailed(e.message))
    }).catch(e => live && setFailed(e.message))
    return () => { live = false }
  }, [sym, attempt])
  if (c) return <CompanyView c={c} focus={pid} sector={sector} title={title} close={close} bars={bars} back={back}
    ask={<AskHere push={push} symbol={c.symbol} name={title || shortName(c.name)} openCompany={openCompany} cls="sec ask-here" />} />
  const notFound = /NotFound|404/.test(failed)
  return (
    <main className="screen building">
      {/* The same header the finished company page opens on, so one becomes the other */}
      <BackBar back={back} />
      <div className="co-top">
        <p className="small kicker">{sector ? `${sector}, ` : ''}{sym}</p>
        <h1 className="title">{title || sym}</h1>
        {!failed && steps.length === 0 && slow && <p className="sub opening"><span className="dot-run" />Opening the ledger</p>}
        {!failed && steps.length > 0 && <p className="lede">Reading its last five earnings calls and filed results. About a minute.</p>}
        {notFound && <p className="lede">There's no NSE company with the symbol {sym}. Check the spelling, or type part of the name.</p>}
      </div>
      {notFound ? <div className="not-found">
        <a className="btn btn-line" href="#/ask">Ask about another</a>
      </div> : <>
      <ul className="steps">
        {steps.map((s, i) => (
          <li key={i} className={`step ${s.state}`}>
            <span>{s.label}</span>
            <span className={`lbl${s.state === 'fail' ? '' : ' lbl-quiet'}`}>{s.state === 'run' ? <span className="dot-run" aria-label="Working" /> : s.state === 'done' ? 'Done' : s.state === 'fail' ? 'Stopped' : 'Next'}</span>
            {s.detail && s.detail !== 'stopped' && <span className="sub">{s.detail}</span>}{s.note && <span className="step-note">{s.note}</span>}
          </li>
        ))}
      </ul>
      {failed && <div className="fail-box">
        <p className="fail-msg">{plainError(failed)}</p>
        <div className="fail-acts">
          <button className="btn" onClick={() => setAttempt(a => a + 1)}>Try again</button>
          <a className="btn btn-line" href="#/ask">Pick another</a>
        </div>
      </div>}</>}
    </main>
  )
}

