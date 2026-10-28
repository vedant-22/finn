import { useEffect, useRef, type ReactNode } from 'react'
import type { Bar, Status } from './lib'

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
  kept: 'Kept', partly: 'Partly', missed: 'Missed', quiet: 'Gone quiet', pending: 'Not due yet', unclear: "Can't tell",
}

export function Mark({ status, size = 20, delay = 0, title }: { status: Status; size?: number; delay?: number; title?: string }) {
  return (
    <svg className={`mark mark-${status}`} width={size} height={size} viewBox="0 0 20 20" role="img" aria-label={title || STATUS_WORD[status]}>
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
      <text x={0} y={h + 12} className="bars-label">{labels[0]?.replace(/^\w+ /, '’').slice(0, 3)}</text>
      <text x={w} y={h + 12} className="bars-label" textAnchor="end">{labels[labels.length - 1]?.replace(/^\w+ /, '’')}</text>
    </svg>
  )
}

export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    ref.current?.focus()
    return () => window.removeEventListener('keydown', k)
  }, [open, onClose])
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
