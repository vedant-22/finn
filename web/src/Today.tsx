import { useEffect, useMemo, useRef, useState } from 'react'
import {
  CATEGORY_LABEL, cr, deadline, getCompany, pct, rupees, shortName, triage, when,
  type Bar, type Company, type Lines, type Move, type Push, type Story,
} from './lib'
import { Accordion, Chart, Fold, Masthead, Outcome, pctParts, Src, StatusLabel, useKept } from './ui'

const WINDOWS = [{ h: 24, label: '24h' }, { h: 72, label: '3 days' }, { h: 168, label: 'Week' }, { h: 720, label: 'Month' }]
// However busy the window, at most five things interrupt; the rest wait in the first fold
const MAX_CARDS = 5

export function Today({ push, lines, setLines, openCompany, openLines }: {
  push: Push; lines: Lines; setLines: (l: Lines) => void; openCompany: (s: string, pid?: number) => void; openLines: () => void
}) {
  const t = useMemo(() => triage(push, lines), [push, lines])
  const names = useMemo(() => Object.fromEntries(push.portfolio.map(p => [p.symbol, p.short || shortName(p.name)])), [push])
  const [showNotes, setShowNotes] = useKept('today.notes', false)
  const [showFold, setShowFold] = useKept('today.fold', false)
  // Results and people first, then the unusual days, as triage orders them; past five they become rows in the fold
  const items = [...t.needs.map(s => ({ s })), ...t.moves.map(m => ({ m }))] as ({ s: Story; m?: undefined } | { m: Move; s?: undefined })[]
  // No one kind takes more than three of the five, so a week of results can't hide a CFO leaving
  const kind = (x: typeof items[number]) => x.s ? x.s.category : 'move'
  const chosen = new Set<typeof items[number]>(), per = new Map<string, number>()
  for (const x of items) if (chosen.size < MAX_CARDS && (per.get(kind(x)) ?? 0) < 3) { chosen.add(x); per.set(kind(x), (per.get(kind(x)) ?? 0) + 1) }
  for (const x of items) if (chosen.size < MAX_CARDS) chosen.add(x)
  const cards = items.filter(x => chosen.has(x)), spill = items.filter(x => !chosen.has(x))
  const count = cards.length
  // The sieve plays once a session, not on every return to Today
  const sieve = useRef(!sessionStorage.getItem('finn-sieved'))
  useEffect(() => { sessionStorage.setItem('finn-sieved', '1') }, [])
  const asof = new Date(push.asof)
  const time = asof.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()
  const routine = t.folded.reduce((n, s) => n + s.filings.length, 0)
  const bars = (sym: string, upto?: string) => {
    const all = push.eod[sym] || []
    const end = upto ? all.findIndex(b => b.d > upto.slice(0, 10)) : -1
    return all.slice(0, end < 0 ? all.length : end).slice(-30)
  }

  return (
    <main className="screen today">
      <Masthead right={<button className="btn-outline btn-sm" onClick={openLines}>Your lines</button>} />
      <section className="hero">
        <p className="lbl lbl-quiet hero-lbl">{asof.toDateString() === new Date().toDateString()
          ? `Today, filings to ${time}`
          : `Snapshot, ${asof.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}, ${time}`}</p>
        {/* The roll is for the eye; a screen reader hears the settled count once */}
        <h1 className="sr-only" aria-live="polite">{count === 0 ? 'Nothing needs you' : `${count} ${count === 1 ? 'needs' : 'need'} you`}</h1>
        <div className="hero-fig" aria-hidden="true">
          {count === 0 ? <Outcome size="l" value="Nothing" /> : <Outcome size="l" value={<Roll to={count} start={sieve.current ? t.filings : undefined} />} />}
          <span className="hero-unit">{count === 1 ? 'needs you' : count === 0 ? 'needs you' : 'need you'}</span>
        </div>
        {t.filings > 0 && <p className="hero-1">Out of {t.filings} {t.filings === 1 ? 'filing' : 'filings'} across {push.portfolio.length} holdings.</p>}
        {spill.length > 0 && <p className="hero-2">{spill.length} more crossed your lines and {spill.length === 1 ? 'waits' : 'wait'} under Worth a look.</p>}
        {count === 0 && <p className="hero-2">{t.filings === 0
          ? 'None of your holdings filed anything in this window, and no price crossed your lines.'
          : 'Nothing crossed your lines. The rest is folded below.'}</p>}
        <div className="window" role="radiogroup" aria-label="Time window">
          {WINDOWS.map(w => (
            <button key={w.h} role="radio" aria-checked={lines.hours === w.h} className={lines.hours === w.h ? 'on' : ''}
              onClick={() => setLines({ ...lines, hours: w.h })}>{w.label}</button>
          ))}
        </div>
      </section>

      <ol className="cards">
        {/* The first card is the one to read first: it takes the brand colour, as one block on a page does in the reference */}
        {cards.map((x, i) => x.s
          ? <li key={x.s.key}><StoryCard s={x.s} lead={i === 0} name={names[x.s.symbol]} asof={push.asof} bars={bars(x.s.symbol, x.s.at)} openCompany={openCompany} /></li>
          : <li key={x.m.symbol + x.m.d}><MoveCard m={x.m} lead={i === 0} name={names[x.m.symbol]} lines={lines} openCompany={openCompany} /></li>)}
      </ol>

      {(spill.length + t.notes.length) > 0 && (
        <Fold title="Worth a look" count={spill.length + t.notes.length} open={showNotes} toggle={() => setShowNotes(!showNotes)}>
          <ul className="notes">
            {spill.map(x => x.s
              ? <NoteRow key={x.s.key} s={x.s} name={names[x.s.symbol]} asof={push.asof} />
              : <MoveRow key={x.m.symbol + x.m.d} m={x.m} name={names[x.m.symbol]} openCompany={openCompany} />)}
            {t.notes.map(s => <NoteRow key={s.key} s={s} name={names[s.symbol]} asof={push.asof} />)}
          </ul>
        </Fold>
      )}

      {routine > 0 && (
        <Fold title="Routine filings" count={routine} quiet open={showFold} toggle={() => setShowFold(!showFold)}>
          <FoldSummary stories={t.folded} names={names} />
        </Fold>
      )}
    </main>
  )
}

// What kind of thing opens the card; when it happened closes it, beside Read more
function CardLabel({ kind }: { kind: string }) {
  return <div className="card-lbl"><span className="lbl">{kind}</span></div>
}

function CardFoot({ at, more, setMore }: { at: string; more: boolean; setMore: (b: boolean) => void }) {
  return <div className="card-foot"><button className="read-more" aria-expanded={more} onClick={() => setMore(!more)}>{more ? 'Read less' : 'Read more'}</button><span className="lbl lbl-quiet">{at}</span></div>
}
const shortDay = (iso: string) => new Date(iso.length > 10 ? iso : iso + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

function StoryCard({ s, lead, name, asof, bars, openCompany }: { s: Story; lead?: boolean; name: string; asof: string; bars: Bar[]; openCompany: (s: string, pid?: number) => void }) {
  const f = s.lead
  const [more, setMore] = useState(false)
  const others = s.filings.filter(x => x !== f)
  const r = f.results
  const line = (k: string) => r?.lines.find((l: any) => l.key === k)
  const rev = line('revenue') || line('nii') || r?.lines[0], pat = line('pat')
  const [v, u] = pctParts(rev?.yoy)
  return (
    <article className={`card story cat-${s.category}${lead ? ' lead' : ''}`}>
      <div className="card-img"><Chart series={bars} /></div>
      <div className="card-info">
        <CardLabel kind={r ? `Results, ${r.quarter}` : CATEGORY_LABEL[s.category] || s.category} />
        <button className="card-title" onClick={() => openCompany(s.symbol)}>{name}</button>
        {r && rev?.yoy != null && <div className="card-fig"><Outcome value={v} unit={u} /><span className="card-cap">{rev.label.toLowerCase()}, against {r.compare.yago || 'a year ago'}</span></div>}
        {!r && f.amount_cr != null && f.amount_cr >= 1 && <div className="card-fig"><Outcome value={`₹${cr(f.amount_cr)}`} unit="cr" />{f.pct_rev != null && <span className="card-cap">{f.pct_rev < 0.1 ? 'under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`} of a year's revenue</span>}</div>}
        {r ? <><p className="card-desc">{resultLine(r, pat)}</p><CardWord symbol={s.symbol} openCompany={openCompany} /></>
          : f.people?.length ? <PeopleLead f={f} />
            : <p className="card-desc">{f.line || tidySubject(f.subject)}</p>}
        <CardFoot at={when(s.at, asof)} more={more} setMore={setMore} />
      </div>
      <Accordion open={more}>
        <div className="card-more">
          {r ? <ResultsBlock f={f} symbol={s.symbol} openCompany={openCompany} /> : f.people?.length ? <PeopleBlock f={f} /> : null}
          <ul className="srcs">
            {r?.source?.xbrl && <li><Src href={r.source.xbrl}>Exchange XBRL</Src></li>}
            {/\.pdf$/i.test(r?.source?.pdf || '') && <li><Src href={r!.source.pdf}>Results PDF</Src></li>}
            <li><Src href={f.url}>The filing</Src></li>
            {others.map((o, i) => <li key={i}><Src href={o.url}>{tidySubject(o.subject)}</Src> <span className="sub">{when(o.at, asof)}</span></li>)}
          </ul>
        </div>
      </Accordion>
    </article>
  )
}

// Promises about the headline numbers, to set the quarter against: the latest one already settled (their record),
// then the latest one still running (what this quarter is measured against). Newest calls first.
function useWord(symbol: string) {
  const [co, setCo] = useState<Company | null>(null)
  useEffect(() => { getCompany(symbol).then(setCo).catch(() => setCo(null)) }, [symbol])
  const about = (co?.ledger || []).filter(p => p.hard && ['margin', 'revenue_growth', 'profit', 'volume'].includes(p.metric) && p.status !== 'unclear')
    .map((p, i) => ({ p, i, t: +p.period.slice(-4) * 12 + MON3.indexOf(p.period.slice(0, 3).toLowerCase()) })).sort((a, b) => b.t - a.t || a.i - b.i).map(x => x.p)
  const settled = about.find(p => p.status !== 'pending'), running = about.find(p => p.status === 'pending')
  return [settled, running, ...about].filter((p, i, all): p is NonNullable<typeof p> => !!p && all.indexOf(p) === i).slice(0, 2)
}

// FINN's point on a results card: the promise this quarter is held to, and its word
function CardWord({ symbol, openCompany }: { symbol: string; openCompany: (s: string, pid?: number) => void }) {
  const p = useWord(symbol)[0]
  if (!p) return null
  return (
    <button className="word-row card-word" onClick={() => openCompany(symbol, p.id)}>
      <span className="word-t">{rupees(p.target.charAt(0).toUpperCase() + p.target.slice(1))}{deadline(p) ? ` ${deadline(p)}` : ''}</span>
      <StatusLabel status={p.status} />
    </button>
  )
}

// Results first, in one sentence: profit and margin after the revenue figure above it
function resultLine(r: any, pat: any) {
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

function sizeWords(f: { amount_cr?: number; pct_rev?: number; line?: string }) {
  if (f.amount_cr == null || f.pct_rev == null) return ''
  const p = f.pct_rev < 0.1 ? 'under 0.1%' : `${f.pct_rev.toFixed(f.pct_rev < 1 ? 1 : 0)}%`
  if (f.amount_cr < 1) return 'Under ₹1 cr.'
  // The line already names the amount ('buyback of ₹150 crore'): just the share of revenue
  const a = f.amount_cr
  const said = [...(f.line || '').matchAll(/₹([\d,]+(?:\.\d+)?)(?:–[\d,.]+)? crore/g)].some(m => Math.abs(+m[1].replace(/,/g, '') - a) <= Math.max(0.5, a * 0.01))
  return said ? `${p.charAt(0).toUpperCase()}${p.slice(1)} of a year's revenue.` : `₹${cr(a)} cr, ${p} of a year's revenue.`
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

function ResultsBlock({ f, symbol, openCompany }: { f: any; symbol: string; openCompany: (s: string, pid?: number) => void }) {
  const r = f.results
  const word = useWord(symbol)
  return (
    <div className="results">
      <table className="figs">
        <caption>{r.quarter}, {r.basis}, ₹ crore</caption>
        <thead><tr><th /><th>Quarter</th><th>vs {r.compare.prev?.split(' ')[0] || 'prev'}</th><th>vs {r.compare.yago || 'year ago'}</th></tr></thead>
        <tbody>
          {r.lines.map((l: any) => (
            <tr key={l.key}>
              <th scope="row">{l.label}</th>
              <td className="num">{cr(l.value)}</td>
              <Chg v={l.qoq} base={l.prev} now={l.value} />
              <Chg v={l.yoy} base={l.yago} now={l.value} />
            </tr>
          ))}
        </tbody>
      </table>
      {r.ebitda_margin != null && r.prev_margin != null && (
        <p className="margin-line sub">EBITDA margin {r.ebitda_margin}%, from {r.prev_margin}% last quarter.</p>
      )}
      {r.one_offs?.length > 0 && (
        <p className="one-off sub">{r.one_offs.map((o: any) => `${o.q === r.quarter ? "This quarter's" : o.q} profit includes ${[o.tax_credit && `a ₹${cr(o.tax_credit)} cr tax credit`, o.exceptional && `₹${cr(Math.abs(o.exceptional))} cr of exceptional items`].filter(Boolean).join(' and ')}.`).join(' ')}</p>
      )}
      {/* The card already shows the first promise; the detail adds the one after it */}
      {word.length > 1 && (
        <div className="against">
          <h4 className="lbl lbl-quiet">{word.slice(1).every(p => p.status === 'pending') ? 'Still running' : 'Also against what they said'}</h4>
          {word.slice(1).map(p => (
            <button key={p.id} className="word-row" onClick={() => openCompany(symbol, p.id)}>
              <span className="word-t">{rupees(p.target.charAt(0).toUpperCase() + p.target.slice(1))}{deadline(p) ? ` ${deadline(p)}` : ''}</span>
              <StatusLabel status={p.status} />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// A percentage off a loss means nothing; a swing back to profit still deserves saying
function Chg({ v, base, now }: { v: number | null; base: number | null; now: number | null }) {
  if (v == null && base != null && base < 0 && now != null && now >= 0) return <td className="num turn">from loss</td>
  return <td className="num">{pct(v)}</td>
}

// Filings write 'October 30, 2026', '30th September 2026' or 'close of business hours of 30 September 2026'. Say '30 Oct'.
const MON3 = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
function effDate(raw: string, filed: string) {
  const t = raw.replace(/(\d+)(st|nd|rd|th)\b/g, '$1')
  const a = t.match(/(\d{1,2})[\s-]+([A-Za-z]{3,})[\s,-]+(\d{4})/), b = t.match(/([A-Za-z]{3,})\s+(\d{1,2}),?\s+(\d{4})/)
  const [d, mon, y] = a ? [a[1], a[2], a[3]] : b ? [b[2], b[1], b[3]] : []
  const m = mon ? MON3.indexOf(mon.slice(0, 3).toLowerCase()) : -1
  if (m < 0) return t
  return `${+d!} ${mon!.slice(0, 1).toUpperCase()}${MON3[m].slice(1)}${y === filed.slice(0, 4) ? '' : ` ${y}`}`
}

function PeopleBlock({ f }: { f: any }) {
  const ppl = sortPeople(f.people)
  return (
    <ul className="people">
      {ppl.slice(0, 3).map((p: any, i: number) => {
        const joining = ['appointed', 're-appointed', 'redesignated'].includes(p.action)
        const moved = reclass(p)
        return (
          <li key={i} className={joining || moved ? 'in' : 'out'}>
            <div className="who"><b>{p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')}</b>
              <span className="role">{moved ? `Stays ${p.role}, off the senior management list` : `${verb(p.action)} ${p.role}`}{/\d/.test(p.effective || '') ? `, from ${effDate(p.effective, f.at)}` : ''}</span></div>
            {joining && p.background && !/not stated|not provided|^$|^designated as|^.{0,60}\bhas (assumed|been appointed)/i.test(p.background) && <p className="bio">{p.background}</p>}
            {joining && p.previous?.length > 0 && <p className="prev">{p.previous.join('; ')}</p>}
            {!joining && !moved && p.reason && !/not stated|^leaving the company\.?$|no other material reason/i.test(p.reason) && <p className="bio">Reason given: {p.reason}</p>}
          </li>
        )
      })}
    </ul>
  )
}
const ORDER_P = { top: 0, board: 1, senior: 2, other: 3 } as Record<string, number>
const sortPeople = (ps: any[]) => [...ps].sort((a: any, b: any) => (+reclass(a) - +reclass(b)) || (ORDER_P[a.seniority] - ORDER_P[b.seniority]) || (a.action === 'appointed' ? -1 : 1))
// 'Changed from SMP to Non-SMP category': same job, just no longer reported as senior management
const reclass = (p: any) => p.action === 'ceased' && /non[- ]?smp|non[- ]senior management/i.test(p.reason || '')
const verb = (a: string) => ({ appointed: 'Joins as', resigned: 'Resigns as', retired: 'Retires as', ceased: 'Leaves as', redesignated: 'Now', 're-appointed': 'Re-appointed', died: 'Died,' } as any)[a] || a

// The lead person on a people card: who, and what changed. Bios wait behind Read more.
function PeopleLead({ f }: { f: any }) {
  const p = sortPeople(f.people)[0]
  const more = f.people.length - 1
  return <p className="card-desc"><span className="card-who">{p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')}</span> {reclass(p) ? `stays ${p.role}, off the senior management list` : `${verb(p.action).toLowerCase()} ${p.role}`}{/\d/.test(p.effective || '') ? `, from ${effDate(p.effective, f.at)}` : ''}.{more > 0 ? ` ${more} more ${more === 1 ? 'change' : 'changes'} in the filing.` : ''}</p>
}

function MoveCard({ m, lead, name, lines, openCompany }: { m: Move; lead?: boolean; name: string; lines: Lines; openCompany: (s: string) => void }) {
  const [more, setMore] = useState(false)
  const [v, u] = pctParts(m.chg)
  return (
    <article className={`card move${lead ? ' lead' : ''}`}>
      <div className="card-img"><Chart series={m.series} /></div>
      <div className="card-info">
        <CardLabel kind="Unusual day" />
        <button className="card-title" onClick={() => openCompany(m.symbol)}>{name}</button>
        <div className="card-fig"><Outcome value={v} unit={u} /><span className="card-cap"><span className="num">{m.volX.toFixed(1)}×</span> its 20-day volume</span></div>
        <p className="card-desc">{moveWhy(m)}</p>
        <CardFoot at={shortDay(m.d)} more={more} setMore={setMore} />
      </div>
      <Accordion open={more}>
        <div className="card-more">
          <p className="sub">Crossed your line of {m.why.map(w => w === 'volume' ? `${lines.volX}× volume` : `±${lines.movePct}% in a day`).join(' and ')}. Closed at ₹{m.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}.</p>
          {m.explainedBy && <ul className="srcs"><li><Src href={m.explainedBy.url}>{tidySubject(m.explainedBy.subject)}</Src></li></ul>}
        </div>
      </Accordion>
    </article>
  )
}
const moveWhy = (m: Move) => m.explainedBy
  ? m.explainedBy.category === 'results'
    ? m.explainedBy.at.slice(0, 10) === m.d ? 'Results came out that day.' : 'Results came out after the previous close.'
    : `After: ${(m.explainedBy.line || tidySubject(m.explainedBy.subject)).replace(/\.$/, '')}.`
  : 'No filing explains it.'

// Past the fifth card, an unusual day is one line in the fold
function MoveRow({ m, name, openCompany }: { m: Move; name: string; openCompany: (s: string) => void }) {
  return (
    <li>
      <button className="note" onClick={() => openCompany(m.symbol)}>
        <span className="note-co">{name}</span>
        <span className="note-text">{pct(m.chg)} on {m.volX.toFixed(1)}× its volume. {moveWhy(m)}</span>
        <span className="note-when">{shortDay(m.d)}</span>
      </button>
    </li>
  )
}

function NoteRow({ s, name, asof }: { s: Story; name: string; asof: string }) {
  const f = s.lead
  const text = f.results ? resultLine(f.results, f.results.lines.find((l: any) => l.key === 'pat'))
    : f.people?.length
      ? f.people.map((p: any) => `${p.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')} ${verb(p.action).toLowerCase()} ${p.role}`).join('; ')
      : f.line || tidySubject(f.subject)
  return (
    <li>
      <a className="note" href={f.url} target="_blank" rel="noopener noreferrer">
        <span className="note-co">{name}</span>
        <span className="note-text">{f.pct_rev != null ? stop(text) : text}{f.pct_rev != null && <span className="sub"> {sizeWords(f)}</span>}</span>
        <span className="note-when">{when(s.at, asof)}</span>
      </a>
    </li>
  )
}

function FoldSummary({ stories, names }: { stories: Story[]; names: Record<string, string> }) {
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
        <li key={k}><span className="num">{v.n}</span> <span>{k}</span> <span className="sub">{[...v.cos].slice(0, 3).join(', ')}{v.cos.size > 3 ? ` and ${v.cos.size - 3} more` : ''}</span></li>
      ))}
    </ul>
  )
}

// The headline number rolls from the last window's count to this one, so switching windows reads as a change.
// On the first open of a session it starts at the filing count and falls to what needs you: the sieve, seen once.
function Roll({ to, start }: { to: number; start?: number }) {
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
