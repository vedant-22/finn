// The brief: the few things that crossed the investor's lines, as notifications, and a way through them that ends.
import { useEffect, useRef, useState } from 'react'
import { isDone, remaining, type Brief, type Done, type Item } from './queue'
import { CATEGORY_LABEL, cr, when, type Lines, type Push } from './lib'
import { FoldSummary, NoteRow, Roll, few, moveWhy, reclass, resultLine, sizeWords, sortPeople, tidySubject } from './items'
import { Masthead, Sheet } from './ui'
import { alertsBlocked, alertsOn, canAlert, disableAlerts, enableAlerts } from './alerts'

export const WINDOWS = [{ h: 24, label: '24 hours' }, { h: 72, label: '3 days' }, { h: 168, label: 'Week' }, { h: 720, label: 'Month' }]

// ---------- how an item reads ----------
const pct1 = (v: number) => `${Math.abs(v).toFixed(1)}%`
const strip = (n: string) => n.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')
export function itemTitle(i: Item, name: string): string {
  const m = i.move, f = i.story?.lead
  if (i.kind === 'results' && f?.results) return `${name} reported ${f.results.quarter.replace(/ FY\d\d$/, '')}`
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0]
    const role = p.role.length > 26 ? 'a director' : p.role
    return ['appointed', 're-appointed', 'redesignated'].includes(p.action) ? `${name} names a new ${role}` : `${name}: ${role} ${p.action === 'retired' ? 'retires' : 'leaves'}`
  }
  if (m) return m.why.includes('price') ? `${name} ${m.chg > 0 ? 'rose' : 'fell'} ${pct1(m.chg)}` : `${name} traded ${m.volX.toFixed(1)}× its usual volume`
  return `${name}: ${(CATEGORY_LABEL[i.story!.category] || i.story!.category).toLowerCase()}`
}
export function itemLine(i: Item): string {
  const f = i.story?.lead
  if (i.kind === 'results' && f?.results) return resultLine(f.results, f.results.lines.find((l: any) => l.key === 'pat'))
  if (i.kind === 'people' && f?.people?.length) {
    const p = sortPeople(f.people)[0], more = f.people.length - 1
    const what = reclass(p) ? `stays ${p.role}, off the senior management list` : `${({ appointed: 'joins as', resigned: 'resigns as', retired: 'retires as', ceased: 'leaves as', redesignated: 'is now', 're-appointed': 'is re-appointed' } as any)[p.action] || p.action} ${p.role}`
    return `${strip(p.name)} ${what}.${more > 0 ? ` ${more} more ${more === 1 ? 'change' : 'changes'} in the filing.` : ''}`
  }
  if (i.move && !f) return i.move.why.includes('price')
    ? `On ${i.move.volX.toFixed(1)}× its usual volume. ${moveWhy(i.move)}`
    : `${i.move.chg >= 0 ? 'Up' : 'Down'} ${pct1(i.move.chg)} on the day. ${moveWhy(i.move)}`
  const t = (f?.line || tidySubject(f?.subject || '')).replace(/\.?$/, '.')
  return f?.pct_rev != null ? `${t} ${sizeWords(f)}` : t
}
// The line that set it off, in the investor's own terms
export function crossedText(i: Item, lines: Lines): string {
  const parts = i.crossed.map(c => c.line === 'price' ? `a ±${lines.movePct}% day` : c.line === 'volume' ? `${lines.volX}× volume` : (CATEGORY_LABEL[c.category!] || c.category!).toLowerCase())
  const u = [...new Set(parts)]
  return `Your ${u.length > 1 ? 'lines' : 'line'}: ${u.length > 1 ? `${u.slice(0, -1).join(', ')} and ${u[u.length - 1]}` : u[0]}`
}

// ---------- the screen ----------
export function BriefScreen({ push, brief, fresh, done, setDone, lines, setLines, names, openReader, openLines }: {
  push: Push; brief: Brief; fresh: Set<string>; done: Done; setDone: (d: Done) => void; lines: Lines; setLines: (l: Lines) => void; names: Record<string, string>
  openReader: (key?: string) => void; openLines: () => void
}) {
  const left = remaining(brief, done)
  const [sheet, setSheet] = useState<'notes' | 'fold' | null>(null)
  const nNotes = brief.notes.length + brief.spill.length
  // One segment per item to read, matching the figure and the reader's 'k of n'
  const segs = brief.items.length
  const filled = segs - left.items.length
  const kept = brief.items.filter(i => done.kept.includes(i.key))
  const cleared = brief.items.filter(i => done.cleared.includes(i.key)).length
  const asof = new Date(push.asof)
  const stamp = `Filings to ${asof.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}, ${asof.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }).toLowerCase()}`
  const cos = [...new Set(left.items.map(i => names[i.symbol]))]
  const finished = left.total === 0
  // The figure: items to read. With none crossed, say so in words
  const n = left.items.length

  return (
    <main className="screen brief">
      <Masthead right={<Listen push={push} brief={brief} done={done} lines={lines} names={names} />} />
      <section className="hero" aria-labelledby="brief-h">
        <p className="small">{stamp}</p>
        <h1 id="brief-h" className="sr-only" aria-live="polite">{finished ? 'Up to date' : n ? `${n} to read` : 'Nothing crossed your lines'}</h1>
        <div className="hero-fig" aria-hidden="true">
          {finished ? <span className="fig fig-word">Up to date</span>
            : n ? <><span className="fig"><Roll to={n} /></span><span className="fig-unit">to read</span></>
              : <span className="fig fig-word">All quiet</span>}
        </div>
        <p className="hero-line">
          {finished ? summary(brief, done, kept.length, cleared)
            : n ? `${few(cos)}. ${brief.filings} ${brief.filings === 1 ? 'filing' : 'filings'} in the window, ${brief.routine} of them routine.`
              : `Nothing crossed your lines in the ${WINDOWS.find(w => w.h === lines.hours)?.label.toLowerCase() || 'window'}. ${nNotes} worth a line.`}
        </p>
        {!finished && <div className="cta"><button className="btn btn-wide" onClick={() => openReader()}>{filled ? 'Carry on reading' : 'Read the brief'}</button></div>}
        {segs > 0 && <div className="progress" role="progressbar" aria-label="Read so far" aria-valuemin={0} aria-valuemax={segs} aria-valuenow={filled}>
          {Array.from({ length: segs }, (_, k) => <span key={k} className={k < filled ? 'on' : ''} />)}
        </div>}
        <div className="stops" role="radiogroup" aria-label="Window">
          {WINDOWS.map(w => <button key={w.h} role="radio" aria-checked={lines.hours === w.h} className={lines.hours === w.h ? 'on' : ''} onClick={() => setLines({ ...lines, hours: w.h })}>{w.label}</button>)}
        </div>
      </section>

      {left.items.length > 0 && (
        <section className="sec" aria-labelledby="crossed-h">
          <h2 id="crossed-h" className="head">Crossed your lines</h2>
          <ul className="notifs">
            {left.items.map(i => <li key={i.key}><Notif i={i} fresh={fresh.has(i.key)} name={names[i.symbol]} push={push} lines={lines} open={() => openReader(i.key)} openLines={openLines} /></li>)}
          </ul>
        </section>
      )}

      {kept.length > 0 && (
        <section className="sec" aria-labelledby="kept-h">
          <h2 id="kept-h" className="head">Kept for later</h2>
          <ul className="rows">{kept.map(i => <li key={i.key}><button className="row" onClick={() => openReader(i.key)}><span>{itemTitle(i, names[i.symbol])}</span><Arrow /></button></li>)}</ul>
        </section>
      )}

      <section className="sec sec-quiet" aria-label="Set aside">
        <ul className="rows">
          {nNotes > 0 && <li><button className="row" onClick={() => setSheet('notes')}><span>Worth a line<span className="row-sub">The rest of the window, one line each{left.notesLeft ? '' : ', read'}</span></span><span className="row-n num">{nNotes}</span><Arrow /></button></li>}
          {brief.routine > 0 && <li><button className="row" onClick={() => setSheet('fold')}><span>Routine filings<span className="row-sub">Notices, call papers, newspaper ads</span></span><span className="row-n num">{brief.routine}</span><Arrow /></button></li>}
          <AlertsRow top={brief.items[0]} names={names} lines={lines} />
          <li><button className="row" onClick={openLines}><span>Your lines<span className="row-sub">{`±${lines.movePct}% in a day, ${lines.volX}× volume, ${lines.interrupt.length} kinds of filing`}</span></span><Arrow /></button></li>
        </ul>
      </section>

      {finished && (cleared + kept.length > 0 || done.notes.length > 0) && <button className="btn-quiet bring" onClick={() => setDone({ ...done, cleared: done.cleared.filter(k => !brief.items.some(i => i.key === k)), kept: done.kept.filter(k => !brief.items.some(i => i.key === k)), notes: [] })}>Bring back what you cleared</button>}

      <Sheet open={sheet === 'notes'} onClose={() => setSheet(null)} title="Worth a line" full>
        <NotesList brief={brief} names={names} asof={push.asof} />
      </Sheet>
      <Sheet open={sheet === 'fold'} onClose={() => setSheet(null)} title="Routine filings" full>
        <p className="sheet-intro sub">Notices, call papers and the like. Nothing here needs you.</p>
        <FoldSummary stories={brief.folded} names={names} />
      </Sheet>
    </main>
  )
}

function summary(b: Brief, d: Done, kept: number, cleared: number) {
  const read = cleared + kept
  const parts = [read ? `${read} read${kept ? `, ${kept} kept for later` : ''}.` : '']
  const aside = b.notes.length + b.spill.length + b.routine
  if (aside) parts.push(`${aside} more ${aside === 1 ? 'filing' : 'filings'} set aside, each a tap away.`)
  return parts.filter(Boolean).join(' ') || 'Nothing in this window.'
}

// A move is a day's close: 'At the close' on the snapshot's day, else the date
export const closeWhen = (d: string, asof: string) => d === asof.slice(0, 10) ? 'At the close' : new Date(d + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

export const Arrow = () => <svg className="arrow" viewBox="0 0 16 16" aria-hidden><path d="M6 3.5l4.5 4.5L6 12.5" /></svg>

// The figure an alert leads with, where one number carries it: profit on a year ago, or a deal's size.
// A move already has its number in the headline; a management change has none.
function alertFig(i: Item): { v: string; c: string; body: string } | null {
  const f = i.story?.lead
  const pat = f?.results?.lines.find((l: any) => l.key === 'pat')
  if (i.kind === 'results' && pat?.yoy != null) {
    const r = f!.results!, rest = r.ebitda_margin != null ? `; EBITDA margin ${r.ebitda_margin}%${r.yago_margin != null ? ` against ${r.yago_margin}%` : ''}` : ''
    return { v: `${pat.yoy >= 0 ? '+' : '−'}${String(+Math.abs(pat.yoy).toFixed(Math.abs(pat.yoy) < 10 ? 1 : 0))}%`, c: 'PAT YoY', body: `Profit after tax ₹${cr(pat.value)} crore${rest}.` }
  }
  if (i.kind === 'filing' && f?.amount_cr != null && f.amount_cr >= 1 && f.pct_rev != null)
    return { v: `₹${cr(f.amount_cr)} cr`, c: `${f.pct_rev < 1 ? f.pct_rev.toFixed(1) : f.pct_rev.toFixed(0)}% of revenue`, body: (f.line || tidySubject(f.subject || '')).replace(/\.?$/, '.') }
  return null
}

// An alert: when, what happened with its number, and the line it crossed. Flat rows, like the rest of the brief.
function Notif({ i, fresh, name, push, lines, open, openLines }: { i: Item; fresh: boolean; name: string; push: Push; lines: Lines; open: () => void; openLines: () => void }) {
  const fig = alertFig(i)
  return (
    <article className="notif">
      <button className="notif-main" onClick={open}>
        <span className="notif-when">{i.kind === 'move' ? closeWhen(i.move!.d, push.asof) : when(i.at, push.asof)}{fresh && <span className="notif-new">New</span>}</span>
        <span className="notif-t">{itemTitle(i, name)}</span>
        <span className="notif-b">{fig ? fig.body : itemLine(i)}</span>
        {fig && <span className="notif-fig"><span className="notif-v">{fig.v}</span><span className="notif-c">{fig.c}</span></span>}
      </button>
      <button className="notif-line" onClick={openLines}>{crossedText(i, lines)}</button>
    </article>
  )
}

export function NotesList({ brief, names, asof }: { brief: Brief; names: Record<string, string>; asof: string }) {
  return (
    <ul className="notes">
      {brief.spill.map(i => i.story
        ? <NoteRow key={i.key} s={i.story} name={names[i.symbol]} asof={asof} />
        : <li key={i.key}><div className="note"><span className="note-co">{names[i.symbol]}</span><span className="note-text">{itemTitle(i, names[i.symbol]).replace(names[i.symbol] + ' ', '').replace(/^./, c => c.toUpperCase())}. {moveWhy(i.move!)}</span><span className="note-when">{when(i.at, asof)}</span></div></li>)}
      {brief.notes.map(s => <NoteRow key={s.key} s={s} name={names[s.symbol]} asof={asof} />)}
    </ul>
  )
}

// Listen: the brief read aloud by the browser's own voice. Free, and works offline.
function Listen({ push, brief, done, lines, names }: { push: Push; brief: Brief; done: Done; lines: Lines; names: Record<string, string> }) {
  const [on, setOn] = useState(false)
  const ok = typeof window !== 'undefined' && 'speechSynthesis' in window
  const utter = useRef<SpeechSynthesisUtterance | null>(null)
  useEffect(() => () => { if (ok) speechSynthesis.cancel() }, [ok])
  if (!ok) return null
  const left = brief.items.filter(i => !isDone(done, i.key))
  const say = () => {
    if (on) { speechSynthesis.cancel(); setOn(false); return }
    const said = (t: string) => t.replace(/₹/g, 'rupees ').replace(/\bcr\b/g, 'crore').replace(/×/g, ' times').replace(/±/g, 'plus or minus ').replace(/−/g, 'minus ').replace(/%/g, ' percent')
    const text = left.length
      ? [`${left.length} to read.`, ...left.map(i => `${itemTitle(i, names[i.symbol])}. ${itemLine(i)} ${crossedText(i, lines)}.`), 'That’s the brief.'].join(' ')
      : 'Nothing left to read. You’re up to date.'
    const u = new SpeechSynthesisUtterance(said(text)); u.lang = 'en-IN'; u.rate = 1.02
    u.onend = () => setOn(false); u.onerror = () => setOn(false)
    utter.current = u; speechSynthesis.cancel(); speechSynthesis.speak(u); setOn(true)
  }
  void push
  return <button className="top-btn" onClick={say} aria-pressed={on}>
    <svg viewBox="0 0 20 20" aria-hidden><path d="M3.5 7.5h3l4-3.5v12l-4-3.5h-3z" />{on ? <path d="M13.5 7.5v5M16 6v8" /> : <path d="M13.5 7.2a4 4 0 0 1 0 5.6M15.6 5.2a7 7 0 0 1 0 9.6" />}</svg>
    {on ? 'Stop' : 'Listen'}
  </button>
}

// Alerts on this phone: asks the browser once; when on, the top item arrives as a real notification straight away
function AlertsRow({ top, names, lines }: { top?: Item; names: Record<string, string>; lines: Lines }) {
  const [on, setOn] = useState(alertsOn)
  const [note, setNote] = useState('')
  if (!canAlert()) return null
  const flip = async () => {
    if (on) { disableAlerts(); setOn(false); setNote(''); return }
    const r = await enableAlerts(top && { key: top.key, title: itemTitle(top, names[top.symbol]), body: `${itemLine(top)} ${crossedText(top, lines)}.` })
    setOn(r === 'on')
    setNote(r === 'denied' ? 'The browser said no. Allow notifications for this site in its settings.' : r === 'on' && top ? 'Sent the top item so you can see one.' : '')
  }
  const sub = note || (on ? 'On. New items arrive as notifications when FINN opens on a newer snapshot' : alertsBlocked() ? 'Blocked in this browser’s settings' : 'Off. Get what crosses your lines as phone notifications')
  return (
    <li><label className="row row-switch"><span>Alerts on this phone<span className="row-sub" aria-live="polite">{sub}</span></span>
      <input type="checkbox" role="switch" checked={on} onChange={flip} /></label></li>
  )
}
