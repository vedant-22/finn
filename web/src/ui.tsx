import { useEffect, useRef, type ReactNode } from 'react'
import type { Bar, Status } from './lib'

// Auditor's tick marks, drawn as pencil strokes. Paths carry a little wobble on purpose.
const PATHS: Record<Status, string[]> = {
  kept: ['M3.5 11.2c1.6 1.2 3.1 2.9 4.4 5.1 2.4-5 5.6-9.1 9.6-12.3'],
  missed: ['M4.5 4.8c3.6 3.2 7.2 6.9 11 10.6', 'M15.4 4.3c-3.9 3.6-7.4 7.4-10.6 11.4'],
  partly: ['M3.5 11.6c1.5 1.1 2.9 2.6 4.1 4.6 1.7-3.1 3.7-5.6 6-7.6', 'M12.2 15.6h5'],
  quiet: ['M10 3.6c3.8 0 6.4 2.8 6.4 6.4s-2.7 6.4-6.4 6.4-6.4-2.9-6.4-6.4c0-2.6 1.5-4.9 3.6-5.8'],
  pending: ['M5 10.4c3.4-.3 6.7-.3 10 .1'],
  unclear: ['M6.4 7.4c.4-2 1.9-3.2 3.8-3.2 2.1 0 3.6 1.4 3.6 3.2 0 2.6-3.6 2.8-3.6 5.4', 'M10.2 15.6v.4'],
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
  return (
    <div className={`sheet-wrap ${open ? 'open' : ''}`} aria-hidden={!open}>
      <div className="scrim" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <div className="sheet-head">
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
