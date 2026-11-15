import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { pct, type Bar, type Status } from './lib'
import { useHideOnScroll, useSettle } from './motion'

// useState that outlives the screen, so a filter or an open fold is still there after Back from a company
const kept = new Map<string, unknown>()
export function useKept<T>(key: string, init: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => (kept.has(key) ? kept.get(key) as T : init))
  return [v, (n: T) => { kept.set(key, n); setV(n) }]
}

// Swipe in from the left edge to go back. Only from the home screen on iOS, where there is no browser back gesture.
export function useEdgeBack(back: () => void) {
  const cb = useRef(back); cb.current = back
  useEffect(() => {
    let x0 = -1, y0 = 0, dx = 0, horiz = false, el: HTMLElement | null = null
    const start = (e: TouchEvent) => {
      const t = e.touches[0]
      if ((navigator as any).standalone !== true || e.touches.length !== 1 || t.clientX > 24) return
      x0 = t.clientX; y0 = t.clientY; dx = 0; horiz = false; el = document.querySelector('main.screen')
    }
    const move = (e: TouchEvent) => {
      if (x0 < 0) return
      const t = e.touches[0]; dx = t.clientX - x0
      if (!horiz) {
        if (Math.abs(t.clientY - y0) > Math.abs(dx)) { x0 = -1; return }
        if (dx < 8) return
        horiz = true
      }
      if (el) { el.style.transition = 'none'; el.style.transform = `translateX(${Math.max(0, dx)}px)` }
    }
    const end = () => {
      if (x0 < 0) return
      x0 = -1
      const go = horiz && dx > 80, node = el
      if (!node) { if (go) cb.current(); return }
      node.style.transition = 'transform 200ms cubic-bezier(.19,1,.22,1)'
      node.style.transform = go ? 'translateX(100vw)' : ''
      // On go, the screen is replaced, so it never slides back into view
      setTimeout(() => { if (go) cb.current(); else node.style.transition = '' }, 200)
    }
    addEventListener('touchstart', start, { passive: true }); addEventListener('touchmove', move, { passive: true })
    addEventListener('touchend', end); addEventListener('touchcancel', end)
    return () => {
      removeEventListener('touchstart', start); removeEventListener('touchmove', move)
      removeEventListener('touchend', end); removeEventListener('touchcancel', end)
    }
  }, [])
}

export const STATUS_WORD: Record<Status, string> = {
  kept: 'Done', partly: 'Partly done', missed: 'Missed', quiet: 'No update', pending: 'Not yet due', unclear: "Can't tell yet",
}
const STATUS_LABEL: Record<Status, string> = {
  kept: 'Done', partly: 'Partly done', missed: 'Missed', quiet: 'No update', pending: 'Not due', unclear: "Can't tell yet",
}
// A verdict is a small capital word in its colour, as v4 set it: red for missed, amber for no update, green for done
export function StatusLabel({ status }: { status: Status }) {
  return <span className={`lbl st st-${status}`}>{STATUS_LABEL[status]}</span>
}

// The wordmark, in ENAM blue
export function Mark({ label = 'FINN' }: { label?: string }) {
  return <span className="wordmark" aria-label={label || undefined} role={label ? 'img' : undefined}><span aria-hidden>FINN</span></span>
}

// The masthead: wordmark left, one outlined pill right. Hides on the way down, comes back on the way up.
// Warm: the page opens on a warm block, so the masthead is warm while it sits over it.
export function Masthead({ right, warm }: { right?: ReactNode; warm?: boolean }) {
  const [top, setTop] = useState(true)
  const ref = useRef<HTMLElement>(null)
  useHideOnScroll(ref)
  useEffect(() => {
    const on = () => setTop(scrollY < 320)
    addEventListener('scroll', on, { passive: true }); return () => removeEventListener('scroll', on)
  }, [])
  return (
    <header ref={ref} className={`mast${warm && top ? ' warm' : ''}`}>
      <a className="wordmark" href="#/" aria-label="FINN, Today">FINN</a>
      {right}
    </header>
  )
}

// An index row: a title, one line saying what's behind it, a count, an arrow. Opens a sheet or a page.
export function IndexRow({ title, line, count, onClick, big }: { title: ReactNode; line?: ReactNode; count?: number; onClick: () => void; big?: boolean }) {
  return (
    <button className={`fo-row${big ? ' fo-row-big' : ''}`} onClick={onClick}>
      <span className="fo-row-t">{title}</span>
      {count != null && <span className="fo-row-n num">{count}</span>}
      <svg className="fo-row-arrow" viewBox="0 0 16 16" aria-hidden><path d="M6 3.5l4.5 4.5L6 12.5" /></svg>
      {line && <span className="fo-row-l">{line}</span>}
    </button>
  )
}

// The reference's accordion: the body opens on a grid-rows transition and is only in the page while open or closing
export function Accordion({ open, children, id }: { open: boolean; children: ReactNode; id?: string }) {
  const [mounted, setMounted] = useState(open)
  const [shown, setShown] = useState(open)
  const ref = useRef<HTMLDivElement>(null)
  const before = useRef<Map<HTMLElement, number> | null>(null)
  // What sits below is measured before the fold moves, so it can slide from where it was instead of jumping
  const flip = (to: boolean) => { before.current = ref.current ? measureBelow(ref.current) : null; setShown(to) }
  useEffect(() => {
    if (open) { setMounted(true); const r = requestAnimationFrame(() => requestAnimationFrame(() => flip(true))); return () => cancelAnimationFrame(r) }
    if (shown) flip(false)
    const t = setTimeout(() => setMounted(false), 120); return () => clearTimeout(t)
  }, [open])  // eslint-disable-line react-hooks/exhaustive-deps
  useLayoutEffect(() => { const b = before.current; before.current = null; if (b && ref.current) slideFrom(b, pageColour(ref.current)) }, [shown])
  return (
    <div id={id} ref={ref} className={`acc${shown ? ' open' : ''}`}>
      <div className="acc-in">{mounted && children}</div>
    </div>
  )
}

// Everything after an element on its page (its later siblings, and theirs up to the page), but not fixed bars
function measureBelow(el: HTMLElement): Map<HTMLElement, number> {
  const m = new Map<HTMLElement, number>()
  for (let n: HTMLElement | null = el; n && n.parentElement && !n.matches('main, .iv-page, body'); n = n.parentElement)
    for (let x = n.nextElementSibling as HTMLElement | null; x; x = x.nextElementSibling as HTMLElement | null)
      if (getComputedStyle(x).position !== 'fixed') m.set(x, x.getBoundingClientRect().top)
  return m
}
// The colour of the page an element sits on, for what slides over the fold's rows to cover them, not show through
function pageColour(el: HTMLElement): string {
  for (let n: HTMLElement | null = el; n; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor; if (c && !/rgba\(.*, 0\)$|transparent/.test(c)) return c }
  return '#fff'
}
// FLIP: put each one back where it was with a transform, then let it slide to its new place (transform only, 240 ms)
function slideFrom(b: Map<HTMLElement, number>, bg: string) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const moved: HTMLElement[] = []
  b.forEach((top, x) => {
    const d = top - x.getBoundingClientRect().top
    if (Math.abs(d) < 1) return
    x.style.transition = 'none'; x.style.transform = `translateY(${d}px)`; moved.push(x)
    if (/rgba\(.*, 0\)$|transparent/.test(getComputedStyle(x).backgroundColor)) x.style.backgroundColor = bg
  })
  if (!moved.length) return
  void document.body.offsetHeight
  requestAnimationFrame(() => moved.forEach(x => {
    x.style.transition = 'transform 240ms cubic-bezier(.2, 0, 0, 1)'; x.style.transform = ''
    const done = (e: TransitionEvent) => {
      if (e.target !== x || e.propertyName !== 'transform') return
      x.style.transition = ''; x.style.backgroundColor = ''
      x.removeEventListener('transitionend', done); x.removeEventListener('transitioncancel', done)
    }
    x.addEventListener('transitionend', done); x.addEventListener('transitioncancel', done)
  }))
}

// A section that folds: title and count on the left, a plus that turns into a minus on the right
export function Fold({ title, count, line, open, toggle, children }: { title: string; count?: number; line?: ReactNode; open: boolean; toggle: () => void; children: ReactNode }) {
  return (
    <section className={`fold${open ? ' is-open' : ''}`}>
      <button className="fold-head" aria-expanded={open} onClick={toggle}>
        <span>{title}{count != null && <span className="fold-n"> ({count})</span>}{line && <span className="fold-l">{line}</span>}</span><span className="plus" aria-hidden />
      </button>
      <Accordion open={open}>{children}</Accordion>
    </section>
  )
}

// A company page's bar: the floating bar again, holding Back, and the name once the heading has scrolled away
export function BackBar({ back, name, band }: { back: () => void; name?: string; band?: boolean }) {
  const ref = useRef<HTMLElement>(null)
  useHideOnScroll(ref)
  return (
    <header ref={ref} className={`bar co-bar${band ? ' warm' : ''}`}>
      <button className="back" onClick={back}>Back</button>
      {name && <span className="bar-name">{name}</span>}
    </header>
  )
}

// A big figure with its unit set smaller on the baseline, as on an outcomes page: +12%, 1/7
// A prefix ('FY' in FY26) is set at unit size too, as the reference sets its letters beside a number
export function Outcome({ value, unit, pre, size = 's' }: { value: ReactNode; unit?: ReactNode; pre?: ReactNode; size?: 'l' | 's' | 'm' | 'xs' | 'xxs' }) {
  return <span className={`outcome outcome-${size}`}>{pre != null && <span className="o-unit o-pre">{pre}</span>}<span className="o-val">{value}</span>{unit != null && <span className="o-unit">{unit}</span>}</span>
}
// '+12.4%' -> ['+12', '%']; one decimal under 10 so small moves still read
export function pctParts(v: number | null | undefined): [string, string] {
  if (v == null || !isFinite(v)) return ['–', '']
  const a = Math.abs(v), r = a < 10 ? Math.round(a * 10) / 10 : Math.round(a)
  return [r === 0 ? '0' : `${v > 0 ? '+' : '−'}${r}`, '%']
}

// A card's picture plate: clips the picture, which settles about its latest price as it scrolls in (motion.ts)
export function SettleImg({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  useSettle(ref)
  return <div className="card-img" ref={ref}>{children}</div>
}

// The card's picture: the stock's last sessions, drawn full width, a brand line over a pale wash
export function Chart({ series, h = 120 }: { series: Bar[]; h?: number }) {
  if (series.length < 2) return null
  // The picture fills its plate as the reference's photos do: the wash runs to the edges, the line keeps clear of the top
  const w = 320, top = 22, base = h - 14
  const closes = series.map(b => b.close)
  const lo = Math.min(...closes), hi = Math.max(...closes)
  const x = (i: number) => (i / (series.length - 1)) * w
  const y = (v: number) => base - ((v - lo) / (hi - lo || 1)) * (base - top)
  const pts = closes.map((c, i) => `${x(i).toFixed(1)} ${y(c).toFixed(1)}`)
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden>
      <path className="wash" d={`M${pts.join('L')}L${w} ${h}L0 ${h}Z`} />
      <path className="line" d={`M${pts.join('L')}`} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

// The price picture, kept small: context for a card, not its point
export function Strip({ bars }: { bars: Bar[] }) {
  if (bars.length < 2) return null
  const chg = bars[bars.length - 1].close / bars[0].close - 1
  return <figure className="fo-strip"><div className="fo-media"><Chart series={bars} h={80} /></div><figcaption>Last {bars.length} sessions, {pct(chg * 100)}</figcaption></figure>
}

// 'Mar 2021' is the year to March 2021: FY21
export const fyLabel = (s?: string) => (s || '').replace(/^Mar \d\d(\d\d)$/, 'FY$1')

export function Bars({ values, labels, w = 150, h = 44, fmt }: { values: (number | null)[]; labels: string[]; w?: number; h?: number; fmt?: (v: number) => string }) {
  const vs = values.map(v => v ?? 0)
  const max = Math.max(...vs.map(Math.abs), 1)
  const bw = w / vs.length
  return (
    <svg className="bars" width={w} height={h + 14} viewBox={`0 0 ${w} ${h + 14}`} aria-label={labels.map((l, i) => `${l}: ${fmt ? fmt(vs[i]) : vs[i]}`).join(', ')}>
      {vs.map((v, i) => {
        const bh = (Math.abs(v) / max) * h
        return <rect key={i} x={i * bw + bw * 0.18} width={bw * 0.64} y={v >= 0 ? h - bh : h} height={Math.max(bh, 1)}
          className={i === vs.length - 1 ? 'bar-last' : v < 0 ? 'bar-neg' : 'bar-y'} />
      })}
      <text x={0} y={h + 12} className="bars-label">{fyLabel(labels[0])}</text>
      <text x={w} y={h + 12} className="bars-label" textAnchor="end">{fyLabel(labels[labels.length - 1])}</text>
    </svg>
  )
}

export function Sheet({ open, onClose, title, children, full }: { open: boolean; onClose: () => void; title: string; children: ReactNode; full?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  const close = useRef(onClose); close.current = onClose
  useEffect(() => {
    // Closed, nothing inside can take focus; open, focus goes in and comes back to the opener on close
    const wrap = ref.current?.parentElement as (HTMLElement & { inert: boolean }) | null | undefined
    if (wrap) wrap.inert = !open
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    const k = (e: KeyboardEvent) => e.key === 'Escape' && close.current()
    window.addEventListener('keydown', k)
    ref.current?.focus()
    // The page behind stays put while the sheet is up
    const root = document.documentElement, was = root.style.overflow
    root.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', k); root.style.overflow = was; opener?.focus?.({ preventScroll: true }) }
  }, [open])
  // Drag the head down to close, like a native sheet.
  const drag = useRef<number | null>(null)
  const down = (e: React.PointerEvent) => { if ((e.target as HTMLElement).closest('button')) return; drag.current = e.clientY; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); if (ref.current) ref.current.style.transition = 'none' }
  const move = (e: React.PointerEvent) => { if (drag.current === null || !ref.current) return; ref.current.style.transform = `translateY(${Math.max(0, e.clientY - drag.current)}px)` }
  const up = (e: React.PointerEvent) => {
    if (drag.current === null || !ref.current) return
    const dy = e.clientY - drag.current; drag.current = null
    ref.current.style.transition = ''; ref.current.style.transform = ''
    if (dy > 80) onClose()
  }
  // On the body, so a sheet opened inside a screen still covers the tab bar
  return createPortal(
    <div className={`sheet-wrap ${open ? 'open' : ''}`} aria-hidden={!open}>
      <div className="scrim" onClick={onClose} />
      <div className={`sheet${full ? ' sheet-full' : ''}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <div className="sheet-head" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
          <span className="grab" aria-hidden />
          <h2>{title}</h2>
          <button className="text-btn" onClick={onClose}>Done</button>
        </div>
        {children}
      </div>
    </div>, document.body)
}

export function Src({ href, children }: { href?: string; children: ReactNode }) {
  if (!href) return <span className="src">{children}</span>
  return <a className="src" href={href} target="_blank" rel="noopener noreferrer">{children}</a>
}
