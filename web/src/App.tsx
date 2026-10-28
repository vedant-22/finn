import { useCallback, useEffect, useState } from 'react'
import { CompanyView } from './CompanyView'
import { Book } from './Book'
import { Today } from './Today'
import {
  buildLive, CATEGORY_LABEL, plainError, DEFAULT_LINES, getCompany, getPush, loadLines, saveLines, shortName,
  type Company, type Lines, type Push, type Step,
} from './lib'
import { Mark, Sheet } from './ui'

type Route = { tab: 'today' | 'book' | 'look'; sym?: string }
const parse = (): Route => {
  const h = location.hash.replace(/^#\/?/, '').split('/')
  if (h[0] === 'c' && h[1]) return { tab: 'look', sym: h[1].toUpperCase() }
  if (h[0] === 'book' || h[0] === 'look') return { tab: h[0] }
  return { tab: 'today' }
}

export function App() {
  const [route, setRoute] = useState<Route>(parse)
  const [push, setPush] = useState<Push | null>(null)
  const [err, setErr] = useState('')
  const [lines, setLinesState] = useState<Lines>(loadLines)
  const [linesOpen, setLinesOpen] = useState(false)
  const [prev, setPrev] = useState<string>('#/')

  useEffect(() => { getPush().then(setPush).catch(e => setErr(e.message)) }, [])
  useEffect(() => {
    const on = () => { setRoute(parse()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on)
  }, [])
  const setLines = (l: Lines) => { setLinesState(l); saveLines(l) }
  const openCompany = useCallback((s: string) => { setPrev(location.hash || '#/'); location.hash = `#/c/${s}` }, [])
  const go = (t: Route['tab']) => { location.hash = t === 'today' ? '#/' : `#/${t}` }

  if (err) return <div className="boot"><p>Couldn't load your filings. {plainError(err)}</p><button className="text-btn" onClick={() => location.reload()}>Try again</button></div>
  if (!push) return <div className="boot"><Mark status="kept" size={36} /></div>
  const holding = (s?: string) => push.portfolio.find(p => p.symbol === s)

  return (
    <>
      {route.sym
        ? <CompanyRoute sym={route.sym} sector={holding(route.sym)?.sector} title={holding(route.sym)?.short} back={() => { location.hash = prev === location.hash ? '#/' : prev }} />
        : route.tab === 'book' ? <Book push={push} openCompany={openCompany} />
          : route.tab === 'look' ? <Look push={push} openCompany={openCompany} />
            : <Today push={push} lines={lines} setLines={setLines} openCompany={openCompany} openLines={() => setLinesOpen(true)} />}

      <nav className="tabs" aria-label="Sections">
        <button className={route.tab === 'today' && !route.sym ? 'on' : ''} onClick={() => go('today')}>Today</button>
        <button className={route.tab === 'book' ? 'on' : ''} onClick={() => go('book')}>Book</button>
        <button className={route.tab === 'look' || route.sym ? 'on' : ''} onClick={() => go('look')}>Look up</button>
      </nav>

      <Sheet open={linesOpen} onClose={() => setLinesOpen(false)} title="Your lines">
        <LinesForm lines={lines} setLines={setLines} />
      </Sheet>
    </>
  )
}

function LinesForm({ lines, setLines }: { lines: Lines; setLines: (l: Lines) => void }) {
  const toggle = (c: string) => setLines({ ...lines, interrupt: lines.interrupt.includes(c) ? lines.interrupt.filter(x => x !== c) : [...lines.interrupt, c] })
  return (
    <div className="lines">
      <p className="sub">FINN interrupts you only when one of these is crossed. Everything else waits in a fold.</p>
      <Stepper label="Volume above its 20-day average" value={lines.volX} step={0.5} min={1.5} max={6} fmt={v => `${v}×`} set={v => setLines({ ...lines, volX: v })} />
      <Stepper label="Price move in a day" value={lines.movePct} step={1} min={1} max={15} fmt={v => `±${v}%`} set={v => setLines({ ...lines, movePct: v })} />
      <h3>Filings that can interrupt</h3>
      <ul className="checks">
        {['results', 'management_change', 'M&A', 'litigation', 'fund_raise', 'credit_rating', 'capex', 'insider_trading'].map(c => (
          <li key={c}>
            <label><input type="checkbox" checked={lines.interrupt.includes(c)} onChange={() => toggle(c)} /><span>{CATEGORY_LABEL[c]}</span></label>
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

function CompanyRoute({ sym, sector, title, back }: { sym: string; sector?: string; title?: string; back: () => void }) {
  const [c, setC] = useState<Company | null | undefined>(undefined)
  const [steps, setSteps] = useState<Step[]>([])
  const [failed, setFailed] = useState('')
  const [attempt, setAttempt] = useState(0)
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
  if (c) return <CompanyView c={c} sector={sector} title={title} back={back} />
  return (
    <main className="screen building">
      <header className="top"><button className="text-btn back" onClick={back}>Back</button><span className="sub">{sym}</span></header>
      <h1 className="co-name">{sym}</h1>
      {!failed && steps.length > 0 && <p className="sub">Reading its last five earnings calls and filed results. About a minute.</p>}
      <ul className="steps">
        {steps.map((s, i) => (
          <li key={i} className={`step ${s.state}`}>
            <span className="step-mark">{s.state === 'done' ? <Mark status="kept" size={18} /> : s.state === 'fail' ? <Mark status="missed" size={18} /> : <span className="dot-run" />}</span>
            <span>{s.label}</span><span className="sub">{s.detail}</span>
          </li>
        ))}
      </ul>
      {failed && <div className="fail-box">
        <p className="fail">{/NotFound|404/.test(failed) ? `No listed company found for ${sym}. Check the NSE symbol.` : plainError(failed)}</p>
        <div className="fail-acts">
          {!/NotFound|404/.test(failed) && <button className="text-btn" onClick={() => setAttempt(a => a + 1)}>Try again</button>}
          <a className="text-btn" href="#/look">Pick another company</a>
        </div>
      </div>}
    </main>
  )
}

function Look({ push, openCompany }: { push: Push; openCompany: (s: string) => void }) {
  const [q, setQ] = useState('')
  const [built, setBuilt] = useState<string[]>([])
  useEffect(() => { fetch('/data/companies.json').then(r => r.json()).then(setBuilt).catch(() => setBuilt([])) }, [])
  const recent: string[] = JSON.parse(localStorage.getItem('finn.recent') || '[]')
  const held = new Set(push.portfolio.map(p => p.symbol))
  const others = built.filter(s => !held.has(s))
  const submit = (e: React.FormEvent) => { e.preventDefault(); const s = q.trim().toUpperCase().replace(/\.(NS|BO)$/, ''); if (s) openCompany(s) }
  return (
    <main className="screen look">
      <header className="top"><h1>Look up a company</h1></header>
      <form onSubmit={submit} className="look-form">
        <label htmlFor="sym" className="sub">NSE symbol</label>
        <div className="look-row">
          <input id="sym" value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. ASTRAL" autoCapitalize="characters" autoCorrect="off" spellCheck={false} />
          <button type="submit" disabled={!q.trim()}>Check their word</button>
        </div>
      </form>
      <p className="sub look-note">FINN reads the company's last five earnings calls and its filed results, lists what management promised, and checks each promise against what happened. Nothing else goes in.</p>
      {recent.length > 0 && <Chips title="Recent" syms={recent} open={openCompany} />}
      {others.length > 0 && <Chips title="Ready to open" syms={others} open={openCompany} />}
      <Chips title="Your holdings" syms={push.portfolio.map(p => p.symbol)} open={openCompany} names={Object.fromEntries(push.portfolio.map(p => [p.symbol, p.short || shortName(p.name)]))} />
    </main>
  )
}
function Chips({ title, syms, open, names }: { title: string; syms: string[]; open: (s: string) => void; names?: Record<string, string> }) {
  return (
    <section className="chips-sec"><h2>{title}</h2>
      <div className="chips">{syms.map(s => <button key={s} onClick={() => open(s)}>{names?.[s] || s}</button>)}</div>
    </section>
  )
}
