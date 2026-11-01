import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { CompanyView } from './CompanyView'
import { Book } from './Book'
import { BriefScreen } from './Brief'
import { AskHere, ItemView } from './Reader'
import { AskScreen, useKnown } from './Ask'
import { buildBrief, lastSeen, markSeen } from './queue'
import { raise } from './alerts'
import { AlertsRow, crossedText, itemLine, itemTitle } from './Brief'
import {
  buildLive, cachedCompany, CATEGORY_LABEL, plainError, DEFAULT_LINES, forgetCompanies, getCompany, getPush, loadLines, saveLines, shortName,
  type Bar, type Company, type Lines, type Push, type Step,
} from './lib'
import { BackBar, Mark, Sheet, useEdgeBack } from './ui'

type Tab = 'brief' | 'book' | 'ask'
type Route = { tab: Tab; sym?: string; pid?: number; item?: string; q?: string }
const parse = (): Route => {
  const [path, query] = location.hash.replace(/^#\/?/, '').split('?')
  const h = path.split('/')
  if (h[0] === 'c' && h[1]) return { tab: 'brief', sym: h[1].toUpperCase(), pid: h[2] && /^\d+$/.test(h[2]) ? +h[2] : undefined }
  if (h[0] === 'read') return { tab: 'brief', item: h[1] ? decodeURIComponent(h.slice(1).join('/')) : undefined }
  if (h[0] === 'book') return { tab: 'book' }
  if (h[0] === 'ask' || h[0] === 'look') return { tab: 'ask', q: new URLSearchParams(query || '').get('q') || undefined }
  return { tab: 'brief' }
}

// The shared-element morph runs where the browser has view transitions and motion is welcome
const morph = () => 'startViewTransition' in document && !matchMedia('(prefers-reduced-motion: reduce)').matches
// The card and every part of it the full view repeats: the panel grows while the price line, the kind, the name, the
// volume, the figure and the sentence each travel to their place in the view, so nothing you were reading is drawn
// twice or over another line on the way. Names are set on the first match only, so no name is ever doubled.
const PARTS: [string, string, string][] = [
  ['.price', '.iv-top .price', 'item-line'], ['.card-lbl', '.iv-top .card-lbl', 'item-kind'], ['.card-title', '.iv-top .iv-name', 'item-name'],
  ['.card-info > .card-cap', '.iv-top > .card-cap', 'item-cap'], ['.card-fig .outcome', '.iv-top .card-fig .outcome', 'item-fig'], ['.card-desc', '.iv-top .iv-lede', 'item-desc']]
const share = (card: HTMLElement, on: boolean) => {
  card.style.viewTransitionName = on ? 'item' : ''
  for (const [sel, , name] of PARTS) { const x = card.querySelector<HTMLElement>(sel); if (x) x.style.viewTransitionName = on ? name : '' }
}
// A Book card grows into its company's warm top, and Back shrinks the top into the card: the panel and the name travel
const nameCo = (el: Element | null | undefined, on: boolean) => {
  if (!(el instanceof HTMLElement)) return
  el.style.viewTransitionName = on ? 'co' : ''
  // The name travels only when it sits on one line: two boxes would cancel the transition, and a name that wraps in
  // a narrow card would be stretched on its way into the one-line title. Otherwise it crosses over with the panel
  const n = el.querySelector<HTMLElement>('.card-title, .co-name-n')
  const oneLine = (x: HTMLElement) => x.getClientRects().length === 1 && x.getBoundingClientRect().height < 1.5 * (parseFloat(getComputedStyle(x).lineHeight) || 40)
  if (n) n.style.viewTransitionName = on && oneLine(n) ? 'co-name' : ''
}
const bookCard = (sym: string) => document.querySelector(`.book-card[data-sym="${CSS.escape(sym)}"]`)
const shareView = (on: boolean) => {
  const v = document.querySelector<HTMLElement>('.item-view'); if (!v) return
  for (const [, sel, name] of PARTS) { const x = v.querySelector<HTMLElement>(sel); if (x) x.style.viewTransitionName = on ? name : '' }
}

export function App() {
  const [route, setRoute] = useState<Route>(parse)
  const [push, setPush] = useState<Push | null>(null)
  const [err, setErr] = useState('')
  const [lines, setLinesState] = useState<Lines>(loadLines)
  const [linesOpen, setLinesOpen] = useState(false)
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
      toY.current = back ? scrolls.current.get(location.hash || '#/') ?? 0 : r.item ? window.scrollY : 0
      setLinesOpen(false)
      // Closing an item shrinks its view back into the card it came from
      const card = from.startsWith('#/read/') && !r.item ? document.querySelector<HTMLElement>(`.card[data-key="${CSS.escape(decodeURIComponent(from.slice(7)))}"]`) : null
      const toCo = from.startsWith('#/book') && r.sym ? bookCard(r.sym) : null
      const fromSym = from.startsWith('#/c/') && !r.sym && (location.hash || '').startsWith('#/book') ? decodeURIComponent(from.slice(4).split('/')[0]) : ''
      if ((toCo || fromSym) && morph()) {
        nameCo(toCo || document.querySelector('.co-top'), true)
        document.startViewTransition(() => {
          nameCo(toCo || document.querySelector('.co-top'), false)
          flushSync(() => setRoute(r)); window.scrollTo(0, toY.current)
          // the card it lands in is shown at once; the rest of Book rises in around it as usual
          const land = toCo ? document.querySelector('.co-top') : bookCard(fromSym)
          land?.setAttribute('data-seen', ''); nameCo(land, true)
        }).finished.finally(() => { nameCo(document.querySelector('.co-top'), false); nameCo(bookCard(fromSym || r.sym || ''), false) })
      } else if (card && morph()) {
        shareView(true)
        document.startViewTransition(() => { flushSync(() => setRoute(r)); window.scrollTo(0, toY.current); share(card, true) })
          .finished.finally(() => share(card, false))
      } else setRoute(r)
    }
    window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on)
  }, [])
  useLayoutEffect(() => { window.scrollTo(0, toY.current) }, [route])
  const setLines = (l: Lines) => { setLinesState(l); saveLines(l) }
  const openCompany = useCallback((s: string, pid?: number) => { location.hash = `#/c/${s}${pid != null ? `/${pid}` : ''}` }, [])
  const go = (t: Tab) => {
    const h = t === 'brief' ? '#/' : `#/${t}`
    if ((location.hash || '#/') === h) window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    else location.hash = h
  }
  const brief = useMemo(() => push ? buildBrief(push, lines) : null, [push, lines])
  const names = useMemo(() => Object.fromEntries((push?.portfolio || []).map(p => [p.symbol, p.short || shortName(p.name)])), [push])
  // Since you last looked: items newer than the last snapshot this phone opened are marked, and raised as alerts if they're on
  const [fresh, setFresh] = useState<Set<string>>(new Set())
  useEffect(() => {
    if (!push || !brief) return
    const seen = lastSeen()
    if (seen && seen < push.asof) {
      const news = brief.items.filter(i => i.at > seen)
      setFresh(new Set(news.map(i => i.key)))
      raise(news.map(i => ({ key: i.key, title: itemTitle(i, names[i.symbol]), body: `${itemLine(i)} ${crossedText(i, lines)}.` })))
    }
    markSeen(push.asof)
  }, [push?.asof])  // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return <div className="boot"><Mark /><p className="serif-line">Couldn’t load your filings. {plainError(err)}</p><button className="btn-primary" onClick={() => location.reload()}>Try again</button></div>
  if (!push || !brief) return <BootSkeleton />
  const holding = (s?: string) => push.portfolio.find(p => p.symbol === s)
  const tab: Tab = !route.sym ? route.tab : prev.startsWith('#/book') ? 'book' : prev.startsWith('#/ask') ? 'ask' : prev ? 'brief' : holding(route.sym) ? 'book' : 'ask'
  // A card grows into its full view (a shared-element transition where the browser has one)
  const openItem = (key: string, el: HTMLElement | null) => {
    const to = `#/read/${encodeURIComponent(key)}`
    if (!el || !morph()) { location.hash = to; return }
    const y = window.scrollY
    share(el, true)
    document.startViewTransition(() => {
      scrolls.current.set(location.hash || '#/', y); toY.current = y
      history.pushState(null, '', to)
      flushSync(() => setRoute(parse()))
      share(el, false); shareView(true)
    }).finished.finally(() => shareView(false))
  }
  const closeItem = () => { if (history.length > 1 && route.item) history.back(); else location.hash = '#/' }

  return (
    <>
      {route.sym
        ? <CompanyRoute push={push} openCompany={openCompany} sym={route.sym} pid={route.pid} sector={holding(route.sym)?.sector} title={holding(route.sym)?.short} close={push.eod[route.sym]?.[push.eod[route.sym].length - 1]} bars={push.eod[route.sym]} back={() => { location.hash = !prev || prev === location.hash ? '#/' : prev }} />
        : route.tab === 'book' ? <Book push={push} openCompany={openCompany} />
          : route.tab === 'ask' ? <AskScreen push={push} q0={route.q} openCompany={openCompany} />
            : <BriefScreen push={push} brief={brief} fresh={fresh} lines={lines} setLines={setLines} names={names} openItem={openItem} openLines={() => setLinesOpen(true)} />}

      {/* The page dims a little under the panel as it grows; the view covers it once open */}
      {route.item && <div className="iv-scrim" aria-hidden="true" />}
      {route.item && <ItemView push={push} brief={brief} k={route.item} lines={lines} names={names}
        close={closeItem} openCompany={openCompany} openLines={() => setLinesOpen(true)} />}

      {/* The tab bar stays in the full view: one tap to Book or Look up from anything you are reading */}
      <nav className="tabs" aria-label="Sections">
        {([['brief', 'Today'], ['book', 'Book'], ['ask', 'Look up']] as [Tab, string][]).map(([t, label]) => (
          <button key={t} className={tab === t ? 'on' : ''} aria-current={tab === t ? 'page' : undefined} onClick={() => go(t)}>{label}</button>
        ))}
      </nav>

      <Sheet open={linesOpen} onClose={() => setLinesOpen(false)} title="Your lines">
        <LinesForm lines={lines} setLines={setLines} count={brief.items.length + brief.spill.length} shown={brief.items.length}
          alerts={<AlertsRow top={brief.items[0]} names={names} lines={lines} />} />
      </Sheet>
    </>
  )
}

// The first paint, before the snapshot arrives: Today's shape in grey, a warm card where the first one will be
function BootSkeleton() {
  return (
    <main className="screen today" aria-busy="true" aria-label="Loading">
      <header className="mast"><Mark label="FINN, loading" /></header>
      <section className="hero"><div className="skel skel-line short" /><div className="skel skel-fig" /><div className="skel skel-line" /><div className="skel skel-line short" /></section>
      <div className="card skel-card"><div className="card-img" /><div className="skel skel-line short" /><div className="skel skel-name" /><div className="skel skel-line" /></div>
    </main>
  )
}

function LinesForm({ lines, setLines, count, shown, alerts }: { lines: Lines; setLines: (l: Lines) => void; count: number; shown: number; alerts: React.ReactNode }) {
  const toggle = (c: string) => setLines({ ...lines, interrupt: lines.interrupt.includes(c) ? lines.interrupt.filter(x => x !== c) : [...lines.interrupt, c] })
  return (
    <div className="lines">
      <p className="serif-line">FINN puts something on Today only when it crosses one of these. With these lines, {count} {count === 1 ? 'thing crosses' : 'things cross'} in this window{count > shown ? `; Today leads with ${shown} and folds the rest under Worth a look` : ''}.</p>
      <ul className="checks">{alerts}</ul>
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
  // A company already read (Book reads them all) is there on the first frame, so a card can grow straight into it
  const [c, setC] = useState<Company | null | undefined>(() => cachedCompany(sym) ?? undefined)
  const [steps, setSteps] = useState<Step[]>([])
  const [failed, setFailed] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [slow, setSlow] = useState(false)
  const { names } = useKnown(push)
  useEdgeBack(back)
  useEffect(() => { setSlow(false); const t = setTimeout(() => setSlow(true), 400); return () => clearTimeout(t) }, [sym, attempt])
  useEffect(() => {
    let live = true
    setC(cachedCompany(sym) ?? undefined); setSteps([]); setFailed('')
    getCompany(sym).then(found => {
      if (!live) return
      if (found) { setC(found); return }
      buildLive(sym, s => live && setSteps(s)).then(x => live && setC(x)).catch(e => live && setFailed(e.message))
    }).catch(e => live && setFailed(e.message))
    return () => { live = false }
  }, [sym, attempt])
  if (c) return <CompanyView c={c} focus={pid} sector={sector} title={title} close={close} bars={bars} back={back}
    ask={<AskHere push={push} symbol={c.symbol} name={title || shortName(c.name)} openCompany={openCompany} bare />} />
  const notFound = /NotFound|404/.test(failed)
  return (
    <main className="screen building">
      {/* The same header the finished company page opens on, so one becomes the other */}
      <BackBar back={back} />
      <div className="co-top">
        <p className="lbl lbl-quiet co-sector">{[sector || 'NSE', sym].join(', ')}</p>
        <h1 className="co-name">{title || sym}</h1>
        {!failed && steps.length === 0 && slow && <p className="co-meta opening"><span className="dot-run" />Opening the ledger</p>}
        {!failed && steps.length > 0 && <p className="co-meta">Reading its last five earnings calls and filed results. About a minute.</p>}
        {notFound && <p className="co-meta">There’s no NSE company with the symbol {sym}. Check the spelling, or type part of the name.</p>}
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
        {/* Out of quota, the companies FINN has already read still open: list them rather than send the investor looking */}
        {/429|RESOURCE_EXHAUSTED|quota/i.test(failed) && <>
          <h2 className="lbl lbl-quiet ready-h">Ready now, outside your book</h2>
          <ul className="chips">{Object.keys(names).filter(s => !push.portfolio.some(p => p.symbol === s)).sort((a, b) => names[a].localeCompare(names[b])).map(s =>
            <li key={s}><button className="btn-outline" onClick={() => openCompany(s)}>{names[s]}</button></li>)}</ul>
          <p className="sub ready-note">Your {push.portfolio.length} holdings are in <a className="see" href="#/book">Book</a>.</p>
        </>}
      </div>}</>}
    </main>
  )
}

