import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Bar, Status } from './lib'

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

// Auditor's tick marks, drawn as pencil strokes. Paths carry a little wobble on purpose.
const PATHS: Record<Status, string[]> = {
  // A pencil tick: short heavy down-stroke, then a long flick that overshoots and lifts.
  kept: ['M2.6 10.6c.9.4 1.9 1.3 2.8 2.5.7 1 1.3 2 1.9 3.3.4-1.1 1.2-2.7 2.4-4.6 2-3.2 4.6-6.3 8-9.2'],
  // A cross pressed hard: two strokes that miss each other's centre a little and run past.
  missed: ['M4.1 3.6c2.4 2.3 5 5.1 7.4 8.1 1.4 1.8 2.8 3.6 4.2 5.4', 'M16.6 3.1c-1.9 1.6-3.8 3.6-5.6 5.8-2.1 2.6-4.3 5.5-6.3 8.6'],
  // A tick that stops short, with a pencil dash after it.
  partly: ['M2.8 11.2c.8.4 1.7 1.3 2.5 2.4.6.9 1.1 1.8 1.6 3 .9-2 2.2-4 3.8-5.9', 'M12.4 15.9c1.5-.2 3.2-.2 5 0'],
  // A ring drawn in one go that overruns its own start.
  quiet: ['M11.7 3.9c-3.6-.9-7.6 1.4-7.9 5.4-.3 3.7 2.5 6.6 6 6.6 3.4 0 6.1-2.4 6.1-5.9 0-3.1-2.2-5.4-5.6-6-1.4-.3-2.6 0-3.7.6'],
  pending: ['M4.6 10.8c1.7-.4 3.6-.5 5.6-.4 1.7.1 3.2.2 4.8.1'],
  unclear: ['M6.4 7.6c.2-2.2 1.9-3.6 3.9-3.5 2 .1 3.5 1.5 3.4 3.3-.1 2.4-3.3 2.6-3.5 5.3', 'M10.1 15.4l.1.6'],
}
export const STATUS_WORD: Record<Status, string> = {
  kept: 'Kept', partly: 'Partly', missed: 'Missed', quiet: 'Gone\u00a0quiet', pending: 'Not due\u00a0yet', unclear: "Can't\u00a0tell",
}

// Marks wait until they scroll into view, so the pencil stroke happens where the reader is looking
let seer: IntersectionObserver | null = null
function watch(el: Element) {
  if (typeof IntersectionObserver === 'undefined') return el.classList.add('seen')
  seer ??= new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('seen'); seer!.unobserve(e.target) }
  }), { rootMargin: '0px 0px -40px 0px' })
  seer.observe(el)
}

export function Mark({ status, size = 20, delay = 0, title }: { status: Status; size?: number; delay?: number; title?: string }) {
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => { const el = ref.current; if (el) { watch(el); return () => seer?.unobserve(el) } }, [])
  return (
    <svg ref={ref} className={`mark mark-${status}`} width={size} height={size} viewBox="0 0 20 20" role="img" aria-label={title || STATUS_WORD[status]}>
      {PATHS[status].map((d, i) => (
        <path key={i} d={d} pathLength={1} style={{ animationDelay: `${delay + i * 120}ms` }} />
      ))}
    </svg>
  )
}

export function Spark({ series, w = 120, h = 36 }: { series: Bar[]; w?: number; h?: number }) {
  if (series.length < 2) return null
  const closes = series.map(b => b.close), vols = series.map(b => b.vol)
  const lo = Math.min(...closes), hi = Math.max(...closes), vmax = Math.max(...vols)
  const x = (i: number) => (i / (series.length - 1)) * (w - 2) + 1
  const y = (v: number) => h * 0.62 - ((v - lo) / (hi - lo || 1)) * (h * 0.58) + 1
  const d = closes.map((c, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(c).toFixed(1)}`).join('')
  const bw = Math.max(1, (w / series.length) * 0.6)
  return (
    <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden>
      {vols.map((v, i) => (
        <rect key={i} x={x(i) - bw / 2} width={bw} y={h - (v / vmax) * h * 0.3} height={(v / vmax) * h * 0.3}
          className={i === vols.length - 1 ? 'vol-last' : 'vol'} />
      ))}
      <path d={d} className="line" />
      <circle cx={x(closes.length - 1)} cy={y(closes[closes.length - 1])} r={2.4} className="dot" />
    </svg>
  )
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
          className={i === vs.length - 1 ? 'bar-last' : v < 0 ? 'bar-neg' : 'bar'} />
      })}
      <text x={0} y={h + 12} className="bars-label">{fyLabel(labels[0])}</text>
      <text x={w} y={h + 12} className="bars-label" textAnchor="end">{fyLabel(labels[labels.length - 1])}</text>
    </svg>
  )
}

export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
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
  return (
    <div className={`sheet-wrap ${open ? 'open' : ''}`} aria-hidden={!open}>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <div className="sheet-head" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
          <span className="grab" aria-hidden />
          <h2>{title}</h2>
          <button className="text-btn" onClick={onClose}>Done</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Src({ href, children }: { href?: string; children: ReactNode }) {
  if (!href) return <span className="src">{children}</span>
  return <a className="src" href={href} target="_blank" rel="noopener noreferrer">{children}</a>
}
