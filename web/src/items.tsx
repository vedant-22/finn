// The pieces an item is made of: results tables, people, one-line notes, tidy filing titles.
import { useEffect, useRef, useState } from 'react'
import { cr, getCompany, plainBio, when, type Company, type Move, type Story } from './lib'

// 'L&T, Syngene and 2 more'
export const few = (xs: string[]) => xs.length <= 3 ? xs.join(xs.length === 2 ? ' and ' : ', ').replace(/, ([^,]*)$/, ' and $1') : `${xs.slice(0, 2).join(', ')} and ${xs.length - 2} more`
export const shortDay = (iso: string) => new Date(iso.length > 10 ? iso : iso + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })


// Promises about the headline numbers, to set the quarter against: the latest one already settled (their record),
// then the latest one still running (what this quarter is measured against). Newest calls first.
export function useWord(symbol: string) {
  const [co, setCo] = useState<Company | null>(null)
  useEffect(() => { getCompany(symbol).then(setCo).catch(() => setCo(null)) }, [symbol])
  const about = (co?.ledger || []).filter(p => p.hard && ['margin', 'revenue_growth', 'profit', 'volume'].includes(p.metric) && p.status !== 'unclear')
    .map((p, i) => ({ p, i, t: +p.period.slice(-4) * 12 + MON3.indexOf(p.period.slice(0, 3).toLowerCase()) })).sort((a, b) => b.t - a.t || a.i - b.i).map(x => x.p)
  const settled = about.find(p => p.status !== 'pending'), running = about.find(p => p.status === 'pending')
  return [settled, running, ...about].filter((p, i, all): p is NonNullable<typeof p> => !!p && all.indexOf(p) === i).slice(0, 2)
}


// Results first, in one sentence: profit and margin after the revenue figure above it
export function resultLine(r: any, pat: any) {
  const parts: string[] = []
  const n = (v: number) => String(+Math.abs(v).toFixed(Math.abs(v) < 10 ? 1 : 0))
  if (pat?.value != null) {
    parts.push(pat.yoy != null ? `Profit after tax ${pat.yoy >= 0 ? 'up' : 'down'} ${n(pat.yoy)}% on a year ago, to ₹${cr(pat.value)} crore`
      : pat.yago != null && pat.yago < 0 && pat.value >= 0 ? `Profit after tax ₹${cr(pat.value)} crore, from a loss a year ago` : `Profit after tax ₹${cr(pat.value)} crore`)
  }
  // After the profit clause the comparison is already a year ago; alone, the margin says so itself
  if (r.ebitda_margin != null) parts.push(`EBITDA margin ${r.ebitda_margin}%${r.yago_margin != null ? ` against ${r.yago_margin}%${parts.length ? '' : ' a year ago'}` : ''}`)
  return parts.length ? `${parts.join('; ')}.` : `${r.quarter} results are out.`
}

export function sizeWords(f: { amount_cr?: number; pct_rev?: number; line?: string }) {
  if (f.amount_cr == null || f.pct_rev == null) return ''
  const p = f.pct_rev < 0.1 ? 'under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`
  if (f.amount_cr < 1) return 'Under ₹1 cr.'
  // The line already names the amount ('buyback of ₹150 crore'): just the share of revenue
  const a = f.amount_cr
  const said = [...(f.line || '').matchAll(/₹([\d,]+(?:\.\d+)?)(?:–[\d,.\u2060]+)?\scrore/g)].some(m => Math.abs(+m[1].replace(/,/g, '') - a) <= Math.max(0.5, a * 0.01))
  return said ? `${p.charAt(0).toUpperCase()}${p.slice(1)} of a year’s revenue.` : `₹${cr(a)} cr, ${p} of a year’s revenue.`
}

// NSE's own labels for the routine call papers, in sentence case
const PAPERS: Record<string, string> = {
  'transcript': 'Earnings call transcript', 'investor presentation': 'Investor presentation', 'link of recording': 'Earnings call recording',
  'audio recording': 'Earnings call recording',
}
// A model line or a size note follows it, so it ends with a full stop
const stop = (t: string) => (/[.!?)]$/.test(t.trim()) ? t : `${t.trim()}.`)
export function tidySubject(s: string) {
  const t = tidyRaw(s)
  return PAPERS[t.toLowerCase()] || t
}
function tidyRaw(s: string) {
  return s.replace(/^.*? has (informed|submitted to) the Exchange( about| regarding)?[,\s]*(the\s+)?/i, '')
    .replace(/^'(.*)'\.?$/, '$1').replace(/^a press release dated .*?, titled\s*"?(.*?)"?\.?$/i, 'Press release: $1').replace(/\.-\s*/g, ' - ').replace(/\s{2,}/g, ' ').replace(/^./, c => c.toUpperCase())
}

export function ResultsBlock({ f }: { f: any }) {
  const r = f.results
  // EBITDA here leaves out other income, so PBT can sit above it; say why rather than let it look like an error
  const e = r.lines.find((l: any) => l.key === 'ebitda' && l.label === 'EBITDA'), b = r.lines.find((l: any) => l.key === 'pbt')
  const exc = r.one_offs?.some((o: any) => o.q === r.quarter && o.exceptional)
  // With no exceptional items the gap is exactly other income less depreciation and interest, so give it in rupees
  const above = e && b && b.value > e.value ? exc ? ' PBT is above EBITDA because other income and exceptional items outweigh depreciation and interest.'
    : ` PBT is above EBITDA: other income was ₹${cr(Math.round(b.value) - Math.round(e.value))} crore more than depreciation and interest.` : ''
  const day = r.source?.filed?.split(' ')[0] || '', filed = day ? effDate(day, day.slice(-4)) : ''
  return (
    <div className="results">
      <table className="figs">
        <caption>{r.quarter}, {r.basis}, ₹ crore</caption>
        <thead><tr><th /><th>Quarter</th><th>QoQ</th><th>YoY</th></tr></thead>
        <tbody>
          {/* Every change to one decimal, so a column reads as one set of figures */}
          {r.lines.map((l: any) => <tr key={l.key}>
            <th scope="row">{l.label}</th>
            <td className="num">{cr(l.value)}</td>
            <Chg v={l.qoq} base={l.prev} now={l.value} />
            <Chg v={l.yoy} base={l.yago} now={l.value} />
          </tr>)}
          {/* The margin is often the quarter's story; its change is in percentage points, not percent */}
          {r.ebitda_margin != null && <tr className="figs-margin">
            <th scope="row">EBITDA margin</th>
            <td className="num">{r.ebitda_margin}%</td>
            <td className="num">{pp(r.ebitda_margin, r.prev_margin)}</td>
            <td className="num">{pp(r.ebitda_margin, r.yago_margin)}</td>
          </tr>}
        </tbody>
      </table>
      <p className="small figs-foot">
        Against {r.compare.prev || 'the previous quarter'} and {r.compare.yago || 'a year ago'}.
        {r.one_offs?.length > 0 && ' ' + r.one_offs.map((o: any) => `${o.q === r.quarter ? 'This quarter’s' : o.q} profit includes ${[o.tax_credit && `a ₹${cr(o.tax_credit)} cr tax credit`, o.exceptional && `₹${cr(Math.abs(o.exceptional))} cr of exceptional items`].filter(Boolean).join(' and ')}.`).join(' ')}
        {above}
        {f.url && <> From the <a className="link-inline" href={f.url} target="_blank" rel="noreferrer">results filed with NSE</a>{filed && `, ${filed}`}.</>}
      </p>
    </div>
  )
}

const pp = (a: number | null, b: number | null) => a == null || b == null ? '–' : `${a - b >= 0 ? '+' : '−'}${Math.abs(a - b).toFixed(1)} pp`
// A percentage off a loss means nothing; a swing back to profit still deserves saying
function Chg({ v, base, now }: { v: number | null; base: number | null; now: number | null }) {
  if (v == null && base != null && base < 0 && now != null && now >= 0) return <td className="num turn">from loss</td>
  return <td className="num">{v == null ? '–' : +Math.abs(v).toFixed(1) === 0 ? '0.0%' : `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}%`}</td>
}

// Filings write 'October 30, 2026', '30th September 2026' or 'close of business hours of 30 September 2026'. Say '30 Oct'.
const MON3 = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
export function effDate(raw: string, filed: string) {
  const t = raw.replace(/(\d+)(st|nd|rd|th)\b/g, '$1')
  const a = t.match(/(\d{1,2})[\s-]+([A-Za-z]{3,})[\s,-]+(\d{4})/), b = t.match(/([A-Za-z]{3,})\s+(\d{1,2}),?\s+(\d{4})/)
  const [d, mon, y] = a ? [a[1], a[2], a[3]] : b ? [b[2], b[1], b[3]] : []
  const m = mon ? MON3.indexOf(mon.slice(0, 3).toLowerCase()) : -1
  if (m < 0) return t
  return `${+d!} ${mon!.slice(0, 1).toUpperCase()}${MON3[m].slice(1)}${y === filed.slice(0, 4) ? '' : ` ${y}`}`
}

// A background worth printing: not a placeholder, and not a restatement of the role ('has assumed charge as...')
const hasBio = (b?: string) => !!b && !/not stated|not provided|^designated as|^.{0,60}\bhas (assumed|been appointed)/i.test(b)
const personKey = (n: string) => n.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/i, '').replace(/[.\s]+/g, ' ').trim().toLowerCase()
// When this filing gives no background, the company's own earlier filing on the same person often does
// (an appointment is announced, then the profile follows, or the other way round).
export function earlierBio(p: any, f: any, all: any[] = []) {
  for (const g of all) {
    if (g === f || g.symbol !== f.symbol) continue
    const q = (g.people || []).find((x: any) => personKey(x.name) === personKey(p.name) && hasBio(x.background))
    if (q) return { background: q.background as string, previous: (q.previous || []) as string[], at: g.at as string, url: g.url as string }
  }
  return null
}

type Bio = { background: string; previous: string[]; at?: string; url?: string }
// The top role's background is printed; a director's or a business head's waits behind one tap
function BioText({ b, fold }: { b: Bio; fold: boolean }) {
  const [open, setOpen] = useState(!fold)
  if (!open) return <button className="link-inline bio-more" onClick={() => setOpen(true)}>Background</button>
  return <>
    {/* Where they worked says more than the filing's paragraph about them: the career leads, the paragraph follows */}
    {b.previous.length > 0 && <p className="bio">Before this: {b.previous.join('; ').replace(/\.?$/, '.')}</p>}
    <p className={b.previous.length ? 'prev' : 'bio'}>{b.previous.length ? plainBio(b.background) : b.background}</p>
    {b.url && b.at && <p className="prev">From the company’s <a href={b.url} target="_blank" rel="noreferrer">{+b.at.slice(8, 10)} {MON3[+b.at.slice(5, 7) - 1].replace(/^./, c => c.toUpperCase())} filing</a></p>}
  </>
}

export function PeopleBlock({ f, all }: { f: any; all?: any[] }) {
  const ppl = sortPeople(f.people)
  return (
    <ul className="people">
      {ppl.map((p: any, i: number) => {
        const joining = ['appointed', 're-appointed', 'redesignated'].includes(p.action)
        const moved = reclass(p)
        return (
          <li key={i} className={joining || moved ? 'in' : 'out'}>
            <div className="who"><b>{p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')}</b>
              <span className="role">{moved ? `Stays ${p.role}, off the senior management list` : `${verb(p.action)} ${p.role}`}{/\d/.test(p.effective || '') ? `, from ${effDate(p.effective, f.at)}` : ''}</span></div>
            {joining && ((b: Bio | null) => b ? <BioText b={b} fold={ppl.length > 3 && p.seniority !== 'top'} /> : <p className="bio bio-none">Background: not in its filings. Worth asking on the next call.</p>)(
              hasBio(p.background) ? { background: p.background, previous: p.previous || [] } : earlierBio(p, f, all))}
            {!joining && !moved && p.reason && !/not stated|^leaving the company\.?$|no other material reason/i.test(p.reason) && <p className="bio">Reason given: {p.reason}</p>}
          </li>
        )
      })}
    </ul>
  )
}
const ORDER_P = { top: 0, board: 1, senior: 2, other: 3 } as Record<string, number>
export const sortPeople = (ps: any[]) => [...ps].sort((a: any, b: any) => (+reclass(a) - +reclass(b)) || (ORDER_P[a.seniority] - ORDER_P[b.seniority]) || (a.action === 'appointed' ? -1 : 1))
// 'Changed from SMP to Non-SMP category': same job, just no longer reported as senior management
export const reclass = (p: any) => p.action === 'ceased' && /non[- ]?smp|non[- ]senior management/i.test(p.reason || '')
export const verb = (a: string) => ({ appointed: 'Joins as', resigned: 'Resigns as', retired: 'Retires as', ceased: 'Leaves as', redesignated: 'Now', 're-appointed': 'Re-appointed', died: 'Died,' } as any)[a] || a

// The lead person on a people card: who, and what changed. Bios wait behind Read more.
export function PeopleLead({ f }: { f: any }) {
  const p = sortPeople(f.people)[0]
  const more = f.people.length - 1
  return <p className="card-desc"><span className="card-who">{p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')}</span> {reclass(p) ? `stays ${p.role}, off the senior management list` : `${verb(p.action).toLowerCase()} ${p.role}`}{/\d/.test(p.effective || '') ? `, from ${effDate(p.effective, f.at)}` : ''}.{more > 0 ? ` ${more} more ${more === 1 ? 'change' : 'changes'} in the filing.` : ''}</p>
}


export const moveWhy = (m: Move) => m.explainedBy
  ? m.explainedBy.category === 'results'
    ? m.explainedBy.at.slice(0, 10) === m.d ? 'Results came out that day.' : 'Results came out after the previous close.'
    : `After: ${(m.explainedBy.line || tidySubject(m.explainedBy.subject)).replace(/\.$/, '')}.`
  : 'No filing explains it.'

// The same reason as one clause, for a fold row: '+12% on 43.5× its volume, the day after results.'
export const moveTail = (m: Move) => m.explainedBy?.category === 'results'
  ? m.explainedBy.at.slice(0, 10) === m.d ? ', on results day.' : ', the day after results.'
  : `. ${moveWhy(m)}`


export function NoteRow({ s, name, asof }: { s: Story; name: string; asof: string }) {
  const f = s.lead
  const text = f.results ? resultLine(f.results, f.results.lines.find((l: any) => l.key === 'pat'))
    : f.people?.length
      ? f.people.map((p: any) => `${p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')} ${verb(p.action).toLowerCase()} ${p.role}`).join('; ')
      : f.line || tidySubject(f.subject)
  return (
    <li>
      <a className="note" href={f.url} target="_blank" rel="noopener noreferrer">
        <span className="note-co">{name}</span>
        <span className="note-text">{stop(text)}{f.pct_rev != null && <span className="sub"> {sizeWords(f)}</span>}</span>
        <span className="note-when">{when(s.at, asof)}</span>
      </a>
    </li>
  )
}

export function FoldSummary({ stories, names }: { stories: Story[]; names: Record<string, string> }) {
  const byDesc = new Map<string, { n: number; cos: Set<string> }>()
  for (const s of stories) for (const f of s.filings) {
    // NSE's labels in sentence case, acronyms kept: 'Copy of Newspaper Publication' -> 'Copy of newspaper publication'
    const k = f.desc.replace(/ under SEBI.*$/, '').replace(/\/Con\. Call Updates/, '')
      .replace(/\b([A-Z])([a-z]+)/g, (_, a, b) => a.toLowerCase() + b).replace(/^./, c => c.toUpperCase())
    const e = byDesc.get(k) || { n: 0, cos: new Set() }
    e.n++; e.cos.add(names[f.symbol]); byDesc.set(k, e)
  }
  return (
    <ul className="folded">
      {[...byDesc.entries()].sort((a, b) => b[1].n - a[1].n).map(([k, v]) => (
        <li key={k}><span className="num">{v.n}</span> <span>{k}</span> <span className="sub">{[...v.cos].slice(0, 3).join(', ')}{v.cos.size > 3 ? ` and\u00a0${v.cos.size - 3}\u00a0more` : ''}</span></li>
      ))}
    </ul>
  )
}


// The headline number rolls from the last window's count to this one, so switching windows reads as a change.
// On the first open of a session it starts at the filing count and falls to what needs you: the sieve, seen once.
export function Roll({ to, start }: { to: number; start?: number }) {
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches
  const [n, setN] = useState(still || start == null ? to : start)
  const from = useRef(start ?? to)
  const first = useRef(start != null)
  useEffect(() => {
    const a = from.current; from.current = to
    const sieve = first.current; first.current = false
    if (a === to || still) { setN(to); return }
    const ms = sieve ? 1100 : 320
    const t0 = performance.now() + (sieve ? 250 : 0); let raf = 0
    const step = (t: number) => {
      const k = Math.max(0, Math.min(1, (t - t0) / ms))
      // the sieve eases like the reveal (expo-decelerate); window switches stay quick
      setN(k >= 1 ? to : Math.round(a + (to - a) * (sieve ? 1 - 2 ** (-10 * k) : 1 - (1 - k) ** 3)))
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [to])
  return <>{n}</>
}
