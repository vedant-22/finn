import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { CompanyView } from './CompanyView'
import { Book } from './Book'
import { Today } from './Today'
import {
  buildLive, CATEGORY_LABEL, plainError, DEFAULT_LINES, forgetCompanies, getCompany, getPush, loadLines, saveLines, shortName, wordScore,
  type Bar, type Company, type Lines, type Push, type Status, type Step,
} from './lib'
import { IndexRow, Mark, Masthead, MenuCtx, Sheet, StatusLabel, useEdgeBack } from './ui'

type Route = { tab: 'today' | 'book' | 'look'; sym?: string; pid?: number }
const parse = (): Route => {
  const h = location.hash.replace(/^#\/?/, '').split('/')
  if (h[0] === 'c' && h[1]) return { tab: 'look', sym: h[1].toUpperCase(), pid: h[2] && /^\d+$/.test(h[2]) ? +h[2] : undefined }
  if (h[0] === 'book' || h[0] === 'look') return { tab: h[0] }
  return { tab: 'today' }
}

export function App() {
  const [route, setRoute] = useState<Route>(parse)
  const [push, setPush] = useState<Push | null>(null)
  const [err, setErr] = useState('')
  const [lines, setLinesState] = useState<Lines>(loadLines)
  const [linesOpen, setLinesOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [gradesOpen, setGradesOpen] = useState(false)
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
      // However a company was reached (tap, forward, a pasted link), Back and the lit tab follow where it came from
      if (r.sym && !from.startsWith('#/c/')) setPrev(from)
      toY.current = from.startsWith('#/c/') && !r.sym ? scrolls.current.get(location.hash || '#/') ?? 0 : 0
      setLinesOpen(false); setMenuOpen(false); setGradesOpen(false)  // a sheet belongs to the screen it opened on; Back with it up shouldn't carry it over
      setRoute(r)
    }
    window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on)
  }, [])
  useLayoutEffect(() => { window.scrollTo(0, toY.current) }, [route])
  const setLines = (l: Lines) => { setLinesState(l); saveLines(l) }
  // A promise id opens the company at that promise, expanded
  const openCompany = useCallback((s: string, pid?: number) => { setPrev(location.hash || '#/'); location.hash = `#/c/${s}${pid != null ? `/${pid}` : ''}` }, [])
  const go = (t: Route['tab']) => {
    const h = t === 'today' ? '#/' : `#/${t}`
    // Tapping the tab you're on goes back to the top, as on any phone app
    if ((location.hash || '#/') === h) window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    else location.hash = h
  }

  if (err) return <div className="boot"><Mark /> <p className="serif-line">Couldn't load your filings. {plainError(err)}</p><button className="btn-outline" onClick={() => location.reload()}>Try again</button></div>
  if (!push) return <div className="boot"><Mark label="FINN, loading" /></div>
  const holding = (s?: string) => push.portfolio.find(p => p.symbol === s)
  // On a company page, light the tab it was opened from
  const tab = !route.sym ? route.tab : prev.startsWith('#/book') ? 'book' : prev.startsWith('#/look') ? 'look' : prev ? 'today' : holding(route.sym) ? 'book' : 'look'

  const linesSummary = `${lines.interrupt.length} kinds of filing, a ±${lines.movePct}% day or ${lines.volX}× volume`
  return (
    <MenuCtx.Provider value={() => setMenuOpen(true)}>
      {route.sym
        ? <CompanyRoute sym={route.sym} pid={route.pid} sector={holding(route.sym)?.sector} title={holding(route.sym)?.short} close={push.eod[route.sym]?.[push.eod[route.sym].length - 1]} bars={push.eod[route.sym]} back={() => { location.hash = !prev || prev === location.hash ? '#/' : prev }} />
        : route.tab === 'book' ? <Book push={push} openCompany={openCompany} />
          : route.tab === 'look' ? <Look push={push} openCompany={openCompany} />
            : <Today push={push} lines={lines} setLines={setLines} openCompany={openCompany} openLines={() => setLinesOpen(true)} />}

      <nav className="tabs" aria-label="Sections">
        <button className={tab === 'today' ? 'on' : ''} aria-current={tab === 'today' ? 'page' : undefined} onClick={() => go('today')}>Today</button>
        <button className={tab === 'book' ? 'on' : ''} aria-current={tab === 'book' ? 'page' : undefined} onClick={() => go('book')}>Book</button>
        <button className={tab === 'look' ? 'on' : ''} aria-current={tab === 'look' ? 'page' : undefined} onClick={() => go('look')}>Look up</button>
      </nav>

      {/* The menu: an index list of what isn't on a screen. The alert lines, and how FINN grades a promise */}
      <Sheet open={menuOpen} onClose={() => setMenuOpen(false)} title="Menu">
        <nav className="fo-menu" aria-label="Menu">
          <IndexRow title="Alert lines" line={linesSummary} onClick={() => { setMenuOpen(false); setLinesOpen(true) }} />
          <IndexRow title="How a promise is graded" line="Kept, missed, gone quiet: what each word means" onClick={() => { setMenuOpen(false); setGradesOpen(true) }} />
        </nav>
        <p className="fo-menu-foot sub">Filings to {new Date(push.asof).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}. Promises are read from the last five earnings calls and checked against filed results.</p>
      </Sheet>
      <Sheet open={gradesOpen} onClose={() => setGradesOpen(false)} title="How a promise is graded">
        <Grades />
      </Sheet>

      <Sheet open={linesOpen} onClose={() => setLinesOpen(false)} title="Alert lines">
        <LinesForm lines={lines} setLines={setLines} />
      </Sheet>
    </MenuCtx.Provider>
  )
}

// What each verdict word means, as the grader applies it. Only promises with a number or a date are graded.
function Grades() {
  const rows: [Status, string][] = [
    ['kept', 'Delivered by the date, or on track where the filings show the path.'],
    ['partly', 'Some of it delivered: one of two targets, or close but short.'],
    ['missed', 'The date passed and the filed numbers fall short.'],
    ['quiet', 'Due, and neither the filings nor the latest call mention it.'],
    ['pending', 'The date hasn\u2019t come yet.'],
    ['unclear', 'The filings don\u2019t carry the number needed to judge it.'],
  ]
  return (
    <div className="grades">
      <p className="sheet-intro sub">FINN grades a promise only when it has a number or a date. Each verdict cites the filing or the call it rests on.</p>
      <ul>{rows.map(([st, t]) => <li key={st}><StatusLabel status={st} /><span>{t}</span></li>)}</ul>
    </div>
  )
}

function LinesForm({ lines, setLines }: { lines: Lines; setLines: (l: Lines) => void }) {
  const toggle = (c: string) => setLines({ ...lines, interrupt: lines.interrupt.includes(c) ? lines.interrupt.filter(x => x !== c) : [...lines.interrupt, c] })
  return (
    <div className="lines">
      <p className="serif-line">FINN interrupts only when one of these is crossed. Everything else waits in a fold.</p>
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

function CompanyRoute({ sym, pid, sector, title, close, bars, back }: { sym: string; pid?: number; sector?: string; title?: string; close?: { d: string; close: number }; bars?: Bar[]; back: () => void }) {
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
  if (c) return <CompanyView c={c} focus={pid} sector={sector} title={title} close={close} bars={bars} back={back} />
  const notFound = /NotFound|404/.test(failed)
  return (
    <main className="screen building">
      {/* The same warm page header the finished company page opens on, so one becomes the other */}
      <header className="bar co-bar"><button className="text-btn back" onClick={back}>Back</button></header>
      <div className="co-top">
        <p className="lbl lbl-quiet co-sector">{sector || 'NSE'}, {sym}</p>
        <h1 className="co-name">{title || sym}</h1>
        {!failed && steps.length === 0 && slow && <p className="sub opening"><span className="dot-run" />Opening the ledger</p>}
        {!failed && steps.length > 0 && <p className="co-meta">Reading its last five earnings calls and filed results. About a minute.</p>}
        {notFound && <p className="co-meta">There's no NSE company with the symbol {sym}. Check the spelling, or type part of the name.</p>}
      </div>
      {notFound ? <div className="not-found">
        <a className="btn-outline" href="#/look">Look up another</a>
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
          <button className="btn-primary" onClick={() => setAttempt(a => a + 1)}>Try again</button>
          <a className="btn-outline" href="#/look">Pick another</a>
        </div>
      </div>}</>}
    </main>
  )
}

function Look({ push, openCompany }: { push: Push; openCompany: (s: string) => void }) {
  const [q, setQ] = useState('')
  // companies.json: { symbol: name } (older builds: a plain list of symbols)
  const [built, setBuilt] = useState<Record<string, string>>({})
  useEffect(() => {
    fetch('/data/companies.json').then(r => r.json())
      .then(d => setBuilt(Array.isArray(d) ? Object.fromEntries(d.map((s: string) => [s, ''])) : d))
      .catch(() => setBuilt({}))
  }, [])
  const recent: string[] = JSON.parse(localStorage.getItem('finn.recent') || '[]')
  const held = new Set(push.portfolio.map(p => p.symbol))
  const others = Object.keys(built).filter(s => !held.has(s))
  const names: Record<string, string> = Object.fromEntries(push.portfolio.map(p => [p.symbol, p.short || shortName(p.name)]))
  for (const [s, n] of Object.entries(built)) if (n && !names[s]) names[s] = shortName(n)
  for (const s of recent) if (!names[s]) { try { const n = JSON.parse(localStorage.getItem(`finn.c.${s}`) || 'null')?.name; if (n) names[s] = shortName(n) } catch { /* ignore */ } }
  // Typing a name ('pidilite') finds the symbol FINN already knows (PIDILITIND)
  const want = q.trim().toUpperCase().replace(/\.(NS|BO)$/, '')
  const fold = (x: string) => x.toUpperCase().replace(/[^A-Z0-9]/g, '')
  // 'Ltd' and friends are in every name: 'L&T' shouldn't match HDFC Bank Ltd
  const FILLER_WORDS = new Set(['LTD', 'LIMITED', 'THE', 'OF', 'AND', 'CO', 'PVT'])
  const known = [...new Set([...push.portfolio.map(p => p.symbol), ...Object.keys(built)])]
  const full = (s: string) => push.portfolio.find(p => p.symbol === s)?.name || built[s] || names[s] || ''
  const matches = fold(want).length < 2 ? [] : known.filter(s => s !== want && [s, fold(full(s)), ...full(s).toUpperCase().split(/[^A-Z0-9]+/).filter(w => !FILLER_WORDS.has(w))].some(x => x.startsWith(fold(want))))
  const submit = (e: React.FormEvent) => { e.preventDefault(); if (!want) { document.getElementById('sym')?.focus(); return } openCompany(!known.includes(want) && matches.length === 1 && fold(want).length >= 4 ? matches[0] : want) }
  return (
    <main className="screen look">
      <Masthead />
      <header className="banner">
        <h1>Look up any NSE company</h1>
        <p>FINN reads its last five earnings calls and filed results, and checks each promise against what happened.</p>
      </header>
      <form onSubmit={submit} className="look-form">
        <label htmlFor="sym" className="lbl lbl-quiet">NSE symbol or name</label>
        <div className="look-row">
          <input id="sym" value={q} onChange={e => setQ(e.target.value)} placeholder="ASTRAL, or a name" autoCapitalize="characters" autoCorrect="off" spellCheck={false} />
          <button type="submit" className="btn-primary">Check their word</button>
        </div>
      </form>
      {matches.length > 0 && <Chips title={matches.length === 1 && !known.includes(want) ? 'Did you mean' : 'Matches'} syms={matches.slice(0, 6)} open={openCompany} names={names} />}
      {recent.length > 0 && <Tiles title="Recent" syms={recent} open={openCompany} names={names} />}
      {others.length > 0 && <Tiles title="Ready to open" syms={others} open={openCompany} names={names} />}
    </main>
  )
}
// Companies already read, as small panel cards in two columns: the symbol as the label, the name as the title,
// and their record once the ledger is in
function Tiles({ title, syms, open, names }: { title: string; syms: string[]; open: (s: string) => void; names: Record<string, string> }) {
  const [rec, setRec] = useState<Record<string, string>>({})
  useEffect(() => {
    let live = true
    syms.forEach(s => getCompany(s).then(c => {
      const w = wordScore(c ?? undefined)
      if (!live || !w) return
      const line = w.graded ? `${Math.floor(w.kept)}/${w.graded} kept` : w.hard ? 'None due yet' : 'Nothing to grade'
      setRec(r => ({ ...r, [s]: line }))
    }).catch(() => {}))
    return () => { live = false }
  }, [syms.join()])
  return (
    <section className="chips-sec tiles-sec"><h2 className="sec-head">{title}</h2>
      <ul className="tiles">{syms.map(s => <li key={s}><button className="tile" onClick={() => open(s)}><span className="lbl lbl-quiet">{s}</span><span className="tile-name">{names[s] || s}</span><span className="tile-rec">{rec[s] || '\u00a0'}</span></button></li>)}</ul>
    </section>
  )
}
function Chips({ title, syms, open, names }: { title: string; syms: string[]; open: (s: string) => void; names?: Record<string, string> }) {
  return (
    <section className="chips-sec"><h2 className="lbl lbl-quiet">{title}</h2>
      <div className="chips">{syms.map(s => <button key={s} className="btn-outline" onClick={() => open(s)}>{names?.[s] || s}</button>)}</div>
    </section>
  )
}
