// The Network where it matters: under a management change, beside a material filing, on a company's page,
// at the end of the brief, and as an answer to a direct question. Everything shown is computed by finn/network;
// this file only sets it down. The network in the demo is synthetic and every block says so.
import { useEffect, useState } from 'react'
import { Fold, useKept } from './ui'
import { foldNotices, netKey, type Kind, type NetNotice, type Topic } from './queue'
import { rupees } from './lib'
import { loadJSON, saveJSON } from './storage'
import { few, shortDay } from './items'

type Contact = { id: string; name: string; now: string; tie: string; last: string }
type Path = { contact: Contact; label: string; line: string; spoke: string; strength?: number }
type Note = { status: string; line: string; why: string; key?: string; said?: boolean }
type Ask = { ask: string; because: string; about?: string }
// Before a meeting: a person's path as the filing lists it, and at each station the one contact who can answer one question
type Pin = { contact: Contact; kind: string; tag: string; basis: string; ask: string; caution: string }
type Station = { kind: string; org: string; role: string; when: string; line?: string; pin: Pin | null }
type Prep = { person: { id: string; name: string; role: string; company: string }; caption: string; stations: Station[]; room: Ask[]; you?: string; pins: number; on_path: number; line: string; sheet: string }
type PersonBlock = { person: { id: string; name: string; role: string; seniority?: string }; identity: Note[]; you: { line: string } | null; paths: Path[]; ask: Ask[]; prep?: Prep | null }
type Call = { contact: Contact; relation: string; line: string; caution: string }
// Who fits a question about the company, by its kind: one choice, with the one question for them (finn/network/engine.py, fit)
type Fit = { contact: Contact; relation: string; basis: string; ask: string; on?: Partial<Record<Topic, string>> }
// The fit's own question, on the subject of the question it sits under
const askOf = (f: Fit, topic?: Topic | null) => (topic && f.on?.[topic]) || f.ask
const REL: Record<string, string> = { former: 'Worked there', inside: 'Works there', competitor: 'Works at a competitor', supplier: 'Works at a supplier', customer: 'Works at a customer', group: 'Same group', sector: 'Same industry', watcher: 'Follows it' }
// Close enough to the company to explain an event there: inside it, or across a counter from it
const NEAR = ['inside', 'former', 'competitor', 'supplier', 'customer', 'group']
const sentences = (t: string) => t.split(/(?<=\.) (?=[A-Z])/)
const first = (t: string) => sentences(t)[0].replace(/\.?$/, '.')
type Notice = NetNotice
// What two or more of a company's filings say together: the line, the evidence, who to ask and what, and a question for the next call
type Pattern = { kind: string; line: string; why: string; next: string; none: string; pin: { contact: Contact; relation: string; basis: string; ask: string } | null }
type Net = {
  build?: string; synthetic?: boolean; label: string; me: string; contacts: number; notices: Notice[]
  filings: Record<string, { people?: PersonBlock[]; call?: Call[] }>
  companies: Record<string, { company: string; cover: string; call: Call[]; counted?: string[]; exits: string; patterns?: Pattern[]; fit?: Partial<Record<Kind, Fit | null>>; people: { person: { name: string; role: string; change: string }; identity: Note[]; path: Path | null; prep?: boolean }[] }>
}
type Answer = {
  intent: string; title: string; lede: string; notes: string[]; follow: string[]; ask?: Ask[]; preps?: Prep[]
  rows: { name: string; sub: string; line: string; tag: string; note: string; ask?: string; person?: string }[]
}

// The investor's answers to "Is it the same person?" live on this phone only. With none, the app shows the static file.
// With some, it shows the file at once, then the views the server rebuilds from them (it stores nothing); the last
// rebuild is kept in one slot, keyed by the file's build and the answers, so a new deploy never shows stale views
type Answers = Record<string, 'same' | 'different'>
export const loadAnswers = (): Answers => { const a = loadJSON<Answers>('identity', {}); return a && typeof a === 'object' ? a : {} }
const sig = (a: Answers) => JSON.stringify(Object.keys(a).sort().map(k => [k, a[k]]))
let base: Net | null = null, current: Net | null = null, booted = false
let applying: 'idle' | 'busy' | 'offline' = 'idle'
const subs = new Set<() => void>()
const emit = () => subs.forEach(f => f())
async function apply(a: Answers) {
  if (!base) return
  let b: Net = base
  const want = sig(a)
  if (!Object.keys(a).length) { current = base; applying = 'idle'; emit(); return }
  const c = loadJSON<any>('identityViews', null)   // an unreadable slot is rebuilt
  if (c?.build === base.build && c?.sig === want) { current = c.views; applying = 'idle'; emit(); return }
  applying = 'busy'; emit()
  for (let tries = 0; tries < 2; tries++) {
    try {
      const r = await fetch('/api/network', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ op: 'views', answers: a }) })
      const v = await r.json()
      if (sig(loadAnswers()) !== want) return          // answered again meanwhile: the newer request decides
      if (!r.ok) throw new Error('server')
      if (v.build !== b.build) {
        // a deploy since this phone read the file (it is cached for minutes): read it again, then ask once more
        const fresh = await fetch('/data/network.json', { cache: 'no-store' }).then(x => x.ok ? x.json() : null)
        if (!fresh || fresh.build !== v.build) throw new Error('stale')
        base = b = fresh; continue
      }
      // nothing to apply (a pair a newer snapshot no longer has): the file as it is
      current = v.notices ? v : b; applying = 'idle'
      saveJSON('identityViews', { build: b.build, sig: want, views: current })   // full: shown, not kept
      emit(); return
    } catch { break }
  }
  if (sig(loadAnswers()) === want) applying = 'offline'
  emit()
}
// Saved while the server couldn't be reached: applied when the phone is back online
if (typeof window !== 'undefined') addEventListener('online', () => { if (applying === 'offline') apply(loadAnswers()) })
function boot() {
  if (booted) return
  booted = true
  fetch('/data/network.json').then(r => r.ok ? r.json() : null).catch(() => null).then(n => { base = current = n; emit(); if (n) apply(loadAnswers()) })
}
export function answer(key: string, v: 'same' | 'different' | null) {
  const a = loadAnswers()
  if (v) a[key] = v; else delete a[key]
  saveJSON('identity', a)   // private mode: applied for this visit
  apply(a)
}
export function useNetwork() {
  const [, tick] = useState(0)
  useEffect(() => { const f = () => tick(x => x + 1); subs.add(f); boot(); return () => { subs.delete(f) } }, [])
  return current
}

// "Is it the same person?", answered where it is asked. The engine's own line then says whose answer it is, with Change
function SamePerson({ k, said }: { k: string; said?: boolean }) {
  useNetwork()
  const mine = loadAnswers()[k]
  return <div className="net-same">
    {said || mine
      ? <button className="see" onClick={() => answer(k, null)}>Change</button>
      : <><button className="see" onClick={() => answer(k, 'same')}>Same person</button><button className="see" onClick={() => answer(k, 'different')}>Someone else</button></>}
    {mine && applying === 'busy' && <p className="net-row-cap" aria-live="polite">Applying your answer.</p>}
    {mine && applying === 'offline' && <p className="net-row-cap" aria-live="polite">Saved on this phone. FINN will apply it when it can reach the server.</p>}
  </div>
}
const Note = ({ n }: { n: Note }) => <div className="net-note-q"><p className="prev net-note">{n.line} {n.why}</p>
  {n.key && (n.status === 'possible' || n.said) && <SamePerson k={n.key} said={n.said} />}</div>

const LINK: Record<string, string> = { strong: 'Strong link', good: 'Fair link', weak: 'Weak link' }
const SAMPLE = 'Sample contacts: the people you know here are made up. Names and jobs from company filings are real.'
const Synthetic = () => <p className="prev net-syn">{SAMPLE}</p>
// Under Today's cards, once: what is invented and what is real
export function NetSyntheticNote() {
  const net = useNetwork()
  return net ? <p className="prev net-syn net-syn-today">{SAMPLE}</p> : null
}

// One person as a hairline row: the name, how they stand to the company, why them, when you last spoke
function Who({ name, tag, why, cap, caution, ask }: { name: string; tag?: string; why: string; cap?: string; caution?: string; ask?: string }) {
  return <li className="net-row">
    <div className="net-row-top"><b className="row-co">{name}</b>{tag && <span className="lbl lbl-quiet">{tag}</span>}</div>
    {ask && <p className="stn-ask">{ask}</p>}
    <p className="net-row-line">{why}</p>
    {cap && <p className="net-row-cap">{cap}</p>}
    {caution && <p className="net-row-cap net-caution">{caution}</p>}
  </li>
}
const spoke = (c: Contact) => c.last ? `You last spoke in ${c.last}.` : ''

// The path: a hairline down the left, a dot a station, a hollow dot for what the filing doesn't list.
// The question leads, in ink; who to put it to, and why them, is one grey line under it.
// The call sheet, as plain text for the investor's notes
function CopySheet({ text, className }: { text: string; className: string }) {
  const [done, setDone] = useState(false)
  const copy = () => navigator.clipboard.writeText(text)
    .then(() => { setDone(true); setTimeout(() => setDone(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return navigator.clipboard ? <button className={className} onClick={copy} aria-live="polite">{done ? 'Copied' : 'Copy the call sheet'}</button> : null
}
function PathView({ d }: { d: Prep }) {
  return <div className="path">
    <p className="prev path-cap">{d.caption}</p>
    <ol className="path-line">
      {d.stations.map((s, k) => <li key={k} className={s.kind === 'gap' ? 'stn stn-gap' : 'stn'}>
        <p className="stn-at">{s.line ? <span className="stn-role">{s.line}</span> : <><span className="lbl">{s.org}</span>{s.role && <span className="stn-role"> · {s.role}{s.when ? `, ${s.when}` : ''}</span>}</>}</p>
        {s.pin?.ask && <p className="stn-ask">{s.pin.ask}</p>}
        {s.pin && <p className="stn-who"><b>{s.pin.contact.name}</b>, {s.pin.tag.charAt(0).toLowerCase() + s.pin.tag.slice(1)}. {s.pin.basis}</p>}
        {s.pin?.caution && <p className="stn-who net-caution">{s.pin.caution}</p>}
      </li>)}
    </ol>
    {(d.room.length > 0 || !!d.you) && <div className="path-room">
      <h3 className="lbl lbl-quiet">In the room</h3>
      {d.you && <p className="stn-who path-you">{d.you}</p>}
      {d.room.map(a => <p key={a.ask} className="stn-ask">{a.ask}</p>)}
    </div>}
    <CopySheet text={d.sheet} className="text-btn path-copy" />
  </div>
}
// A pattern across filings: what they say together in ink, the filings' own words in grey, then the one person and the one question
function Patterns({ xs }: { xs: Pattern[] }) {
  return <>{xs.map(p => <div key={p.line} className="net-pat">
    <p className="net-ask">{p.line} <span className="net-why">{p.why}{p.none ? ` ${p.none}` : ''}</span></p>
    {p.pin && <ul className="net-rows"><Who name={p.pin.contact.name} tag={REL[p.pin.relation]} ask={p.pin.ask} why={p.pin.basis} cap={spoke(p.pin.contact)} /></ul>}
  </div>)}</>
}
// A pattern raises a question for management too: it joins the company's questions for the next call
export function useNetNext(sym: string): string[] {
  const net = useNetwork()
  return (net?.companies[sym]?.patterns || []).map(p => p.next)
}
// The path a card or an answer leads with: the most senior arrival's, then the one with more people on it
const leadPrep = (ppl: PersonBlock[]) => ppl.filter(p => p.prep).sort((a, b) => (a.person.seniority === 'top' ? 0 : 1) - (b.person.seniority === 'top' ? 0 : 1) || b.prep!.pins - a.prep!.pins)[0]?.prep

// Everything the network holds on an item: the people its filings name, and who is best placed to explain it.
// A filing with nobody of its own falls back to the one person closest to the company.
function forItem(net: Net, ids: (string | undefined)[], sym?: string) {
  const blocks = [...new Set(ids.filter(Boolean) as string[])].map(id => net.filings[id]).filter(Boolean)
  const seen = new Set<string>()
  const ppl = blocks.flatMap(b => b.people || []).filter(p => !seen.has(p.person.id) && !!seen.add(p.person.id))
  // A way to the CEO, CFO or MD comes before a way to a director; then the stronger link
  const top = (p: PersonBlock) => p.person.seniority === 'top' ? 0 : 1
  const paths = ppl.flatMap(p => p.paths.filter(x => x.label !== 'weak').slice(0, 1).map(x => ({ p, x })))
    .sort((a, b) => top(a.p) - top(b.p) || (b.x.strength ?? 0) - (a.x.strength ?? 0))
  // own: matched by the engine to this filing's event. Otherwise the one contact closest to the company stands in
  const own = [...new Map(blocks.flatMap(b => b.call || []).map(c => [c.contact.id, c])).values()]
  const co = sym ? net.companies[sym] : undefined
  const call = own.length || !co ? own : co.call.filter(c => NEAR.includes(c.relation)).slice(0, 1)
  const asks = [...new Map(ppl.flatMap(p => p.ask).map(a => [a.ask, a])).values()].slice(0, 2)
  return { ppl, paths, call, own, asks, prep: leadPrep(ppl) }
}
const together = (line: string) => { const a = line.split(': ')[0]; return a.includes(' overlapped at ') ? `together at ${a.split(' overlapped at ')[1]}` : a }

// On a Today card: the one person to ask, in a line. Nothing when the network has nobody close enough.
export function NetCardLine({ ids, sym, kind }: { ids: (string | undefined)[]; sym: string; kind?: Kind | null }) {
  const net = useNetwork()
  if (!net) return null
  const { paths, call, own, prep } = forItem(net, ids, sym)
  // An arrival with two or more of the investor's people on the path: that is the notice, and it comes unasked
  if (prep?.line) return <p className="card-line card-net">{prep.line}</p>
  // A departure or the numbers: the one person who fits that kind of question, or nobody
  if (kind) {
    const f = net.companies[sym]?.fit?.[kind]
    return f ? <p className="card-line card-net">Ask someone you know: <b>{f.contact.name}</b>, {f.basis}.</p> : null
  }
  // The person matched to the event leads; then whoever knows someone the filing names (a new CFO, a new MD);
  // then the contact closest to the company
  const c = own[0] ?? (paths.length ? undefined : call[0])
  // Someone inside the company now, or just out of it, is named but not pressed on the investor: the full view carries the caution
  if (c) return <p className="card-line card-net">{c.caution ? 'You know' : 'Ask someone you know:'} <b>{c.contact.name}</b>. {first(c.line)}</p>
  if (paths.length) return <p className="card-line card-net"><b>{paths[0].x.contact.name}</b> knows {paths[0].p.person.name}: {together(paths[0].x.line)}.</p>
  return null
}

// Beside a next-call question in the end band: who to ask before the call
// The person fits the question: someone who left over a year ago for a departure, someone at a competitor or a customer
// today for the numbers, each asked about their own seat. Nobody fits: nothing is shown
export function NetAskFirst({ sym, kind, topic }: { sym: string; kind: Kind; topic?: Topic | null }) {
  const net = useNetwork()
  const f = net?.companies[sym]?.fit?.[kind]
  return f ? <span className="end-who">Ask first: <b>{f.contact.name}</b>, {f.basis}. {askOf(f, topic)}</span> : null
}

// In a card's full view: who can explain this, and what to ask them
export function NetFiling({ ids, sym, kind, topic }: { ids: (string | undefined)[]; sym?: string; kind?: Kind | null; topic?: Topic | null }) {
  const net = useNetwork()
  if (!net) return null
  const { ppl, paths, call: near, own: matched, asks, prep } = forItem(net, ids, sym)
  // A departure or the numbers: the one person who fits, with their own question, in place of the event's or the
  // company's closest contact; a question about the company then goes to the room
  const fit = kind && sym ? net.companies[sym]?.fit?.[kind] ?? null : undefined
  const call = fit === undefined ? near : [], own = fit === undefined ? matched : []
  const notes = ppl.flatMap(p => p.identity)
  const you = ppl.filter(p => p.you)
  const pats = (sym && net.companies[sym]?.patterns) || []
  if (prep) return (
    <section className="iv-sec net" aria-label="Who was there">
      <h2 className="t-b1">Who was there</h2>
      <PathView d={prep} />
      <Patterns xs={pats} />
      {notes.map((n, k) => <Note key={k} n={n} />)}
      <Synthetic />
    </section>
  )
  if (!fit && !paths.length && !call.length && !asks.length && !notes.length && !you.length && !pats.length) return null
  // A question about the company sits under the person who can answer it: the first who isn't inside it now.
  // A question about the person is for the person, in the room
  const about = asks.filter(a => a.about === 'company'), answers = call.find(c => !c.caution)
  const room = asks.filter(a => a.about !== 'company' || !answers)
  // Whoever knows a person the filing names comes before a contact who only knows the company
  const pinned = new Set(pats.map(p => p.pin?.contact.id))
  const callRows = call.filter(c => !pinned.has(c.contact.id)).map(c => <Who key={c.contact.id} name={c.contact.name} tag={REL[c.relation]} why={c.line} cap={spoke(c.contact)} caution={c.caution} ask={c === answers ? about[0]?.ask : undefined} />)
  return (
    <section className="iv-sec net" aria-label="Who to ask">
      <h2 className="t-b1">Who to ask</h2>
      <Patterns xs={pats} />
      {(!!fit || call.length > 0 || paths.length > 0 || you.length > 0) && <ul className="net-rows">
        {fit && <Who name={fit.contact.name} tag={REL[fit.relation]} ask={askOf(fit, topic)} why={fit.basis} cap={spoke(fit.contact)} />}
        {own.length > 0 && callRows}
        {paths.map(({ p, x }) => <Who key={p.person.id + x.contact.id} name={x.contact.name} tag={LINK[x.label]} why={`Knows ${p.person.name}. ${x.line}`} cap={x.spoke} />)}
        {own.length === 0 && callRows}
        {you.map(p => <Who key={p.person.id} name={p.person.name} tag="You may know them" why={p.you!.line} />)}
      </ul>}
      {room.length > 0 && <div className="net-asks">
        <h3 className="lbl lbl-quiet">In the room</h3>
        {room.map(a => <p key={a.ask} className="net-ask">{a.ask} <span className="net-why">{a.because}</span></p>)}
      </div>}
      {notes.map((n, k) => <Note key={k} n={n} />)}
      <Synthetic />
    </section>
  )
}

// On a company's page, under the questions for the next call: who else to ask
export function NetCompany({ sym }: { sym: string }) {
  const net = useNetwork()
  const c = net?.companies[sym]
  if (!c) return null
  const routes = c.people.filter(p => p.path && p.person.change !== 'leaves')
  // Three rows, but never fewer than the cover counts: everyone it says has worked inside is listed
  const rows = c.call.filter(r => !(c.patterns || []).some(p => p.pin?.contact.id === r.contact.id))
  const counted = (r: Call) => (c.counted || []).includes(r.contact.id)
  let room = Math.max(0, 3 - rows.filter(counted).length)
  const shown = rows.filter(r => counted(r) || room-- > 0)
  if (!c.call.length && !routes.length && !c.people.some(p => p.prep)) return null
  return (
    <section className="net net-co" aria-label="Who to ask">
      <h2 className="sec-head">Who to ask</h2>
      <p className="sub">{c.cover}{c.exits ? ` ${c.exits}` : ''}</p>
      <Patterns xs={c.patterns || []} />
      <ul className="net-rows">
        {shown.map(r => <Who key={r.contact.id} name={r.contact.name} tag={REL[r.relation]} why={r.line} cap={spoke(r.contact)} caution={r.caution} />)}
        {routes.slice(0, 2).map(p => <Who key={p.person.name} name={p.path!.contact.name} tag={LINK[p.path!.label]} why={`Knows ${p.person.name}, ${p.person.role}. ${p.path!.line}`} cap={p.path!.spoke} />)}
      </ul>
      {c.people.some(p => p.prep) && <p className="net-before"><a className="src" href={`#/ask?q=${encodeURIComponent(`Brief me before I meet ${c.company}`)}`}>Before you meet them</a></p>}
      <Synthetic />
    </section>
  )
}

// With Today's folds: what the network noticed in the window that the cards above don't already carry
export function NetNoticed({ hours, asof, skip, raised }: { hours: number; asof: string; skip: string[]; raised?: NetNotice | null }) {
  const net = useNetwork()
  const [open, setOpen] = useKept('today.net', false)
  if (!net?.notices.length) return null
  // A standing note (where you are blind) waits for "Where am I blind?"; what a card above carries is not said twice
  const xs = foldNotices(net.notices, asof, hours, skip, raised)
  if (!xs.length) return null
  return (
    <Fold title="People you know" count={xs.length} line={open ? undefined : xs[0].line} open={open} toggle={() => setOpen(!open)}>
      <ul className="notes net-notes">
        {xs.map((n, k) => {
          // A path opens as the brief on that person; a pattern opens its company. The rest say what there is to say
          // Someone you know in a filing opens their company too: its Who to ask
          // A notice with a card opens that card's full view, and says the card's sentence, not all its evidence
          const href = n.card ? `#/read/${encodeURIComponent(netKey(n))}` : n.kind === 'path' && n.q ? `#/ask?q=${encodeURIComponent(n.q)}` : ['seats', 'contact'].includes(n.kind) && n.symbol ? `#/c/${n.symbol}` : ''
          // Amounts as the cards write them: ₹ and crore, whatever the exchange's text said
          const body = <><span className="note-co">{rupees(n.line)}</span><span className="note-text">{rupees(n.card ? n.card.line : n.why)}</span></>
          // A name FINN can't place is asked here, and an answer given here can be changed here
          const ask = n.key && ['identity', 'contact', 'different'].includes(n.kind) ? <SamePerson k={n.key} said={n.kind !== 'identity'} /> : null
          return <li key={k}>{href ? <a className="note" href={href}>{body}</a> : <div className="note">{body}</div>}{ask}</li>
        })}
      </ul>
      <p className="prev net-syn"><a className="src" href="#/ask?q=Who%20should%20I%20reconnect%20with%3F">Ask about people you know</a>. The investor and the contacts here are made up.</p>
    </Fold>
  )
}

// A direct question. Words that make a question one for the network rather than the promise ledger
export const NET_Q = /\b(who (should|do|can|knows|are|covers|is my)|whom|call about|reach|introduc\w*|reconnect|lost touch|blind|brief me|meeting|before i meet|go-?to|my network|notice[d]?)\b/i
export const NET_STARTERS = ['Brief me before I meet Home First', 'Who knows the new MD of HDFC Bank?', 'Who should I call about SRF’s tax notice?', 'Who are my go-to people for specialty chemicals?']

export function NetAnswer({ q, fallback }: { q: string; fallback: React.ReactNode }) {
  const [cur, setCur] = useState(q)
  const [a, setA] = useState<Answer | null | undefined>(undefined)
  useEffect(() => {
    let live = true
    setA(undefined)
    fetch('/api/network', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: cur, decisions: loadAnswers() }) })
      .then(r => r.json()).then(j => { if (live) setA(j.error ? null : j) }).catch(() => { if (live) setA(null) })
    return () => { live = false }
  }, [cur])
  if (a === undefined) return <section className="answer"><div className="skel skel-line" /><div className="skel skel-block" /></section>
  if (a === null || (a.intent === 'none' && cur === q)) return <>{fallback}</>
  // A person whose path is drawn below is not also set out as rows: the path is the fuller account
  const preps = a.preps || []
  const rows = preps.length ? a.rows.filter(r => r.person && !preps.some(d => d.person.id === r.person)) : a.rows
  return (
    <section className="answer net" aria-live="polite">
      {cur !== q && <p className="small answer-q">{cur}</p>}
      <h2 className="t-b1">{a.title}</h2>
      <p>{a.lede}</p>
      {rows.length > 0 && <ul className="rows">{rows.map((r, k) => <li key={k} className="net-row">
        <div className="net-row-top"><b className="row-co">{r.name}</b>{r.tag && <span className="lbl lbl-quiet">{r.tag}</span>}</div>
        {r.sub && <p className="row-sub">{r.sub}</p>}
        {!a.lede.includes(r.line) && <p className="net-row-line">{r.line}</p>}
        {r.note && <p className="prev">{r.note}</p>}
        {r.ask && <button className="see" onClick={() => setCur(r.ask!)}>This one</button>}
      </li>)}</ul>}
      {preps.map(d => <div key={d.person.id} className="path-sec">
        <h3 className="t-b1">Who was there</h3>
        {(preps.length > 1 || a.intent !== 'diligence') && <p className="row-sub">{d.person.name}, {d.person.role}</p>}
        <PathView d={d} />
      </div>)}
      {a.ask && a.ask.length > 0 && <>
        <h3 className="lbl lbl-quiet ask-other">In the room</h3>
        <ul className="net-list">{a.ask.map(x => <li key={x.ask}><p className="net-line"><b>{x.ask}</b> <span className="net-why">{x.because}</span></p></li>)}</ul>
      </>}
      {a.notes.map((n, k) => <p key={k} className="prev">{n}</p>)}
      {a.follow.length > 0 && <div className="chips">{a.follow.map(f => <button key={f} className="btn-outline" onClick={() => setCur(f)}>{f}</button>)}</div>}
      <Synthetic />
    </section>
  )
}

// A notice raised as a card on Today: titled with its companies, the person in the sentence
export const netTitle = (n: NetNotice, names: Record<string, string>) => few((n.card?.symbols || []).map(s => names[s] || s))

// The raised card's full view. One call: each company's question for the one person, and the call sheet. Control seats:
// the filings' own words, the one person and question, the question for management, and the company
export function NetItemPage({ n, title, names, openCompany }: { n: NetNotice; title: string; names: Record<string, string>; openCompany: (s: string) => void }) {
  const net = useNetwork()
  const pat = n.kind === 'seats' ? net?.companies[n.symbol]?.patterns?.[0] : undefined
  const c = n.card!
  return <>
    <div className="iv-top">
      <div className="card-lbl"><span className="lbl">People you know</span><span className="lbl lbl-quiet">{shortDay(n.at)}</span></div>
      <h1 className="t-h1 iv-name">{title}</h1>
      <p className="card-desc iv-lede">{c.line}</p>
      {/* what the filings said, once, under the sentence; for one call, why it is here at all */}
      <p className="iv-line">{pat ? pat.why : 'It is here because of people you know; it passed none of your alert levels. One person you know can answer questions about several companies at once.'}</p>
    </div>
    {c.rows && <section className="iv-sec net" aria-label="One call">
      <h2 className="t-b1">One call</h2>
      <ul className="net-rows">{c.rows.map(r => <li key={r.symbol} className="net-row">
        <div className="net-row-top"><button className="row-co net-co-link" onClick={() => openCompany(r.symbol)}>{names[r.symbol] || r.symbol}</button></div>
        <p className="stn-ask">{r.ask}</p>
        <p className="net-row-line">{r.line}</p>
      </li>)}</ul>
      {n.contact?.last && <p className="net-row-cap">You last spoke to {n.contact.name} in {n.contact.last}.</p>}
      {c.sheet && <CopySheet text={c.sheet} className="text-btn path-copy" />}
    </section>}
    {pat?.pin && <section className="iv-sec net" aria-label="Who to ask">
      <h2 className="t-b1">Who to ask</h2>
      <ul className="net-rows"><Who name={pat.pin.contact.name} tag={REL[pat.pin.relation]} ask={pat.pin.ask} why={pat.pin.basis} cap={spoke(pat.pin.contact)} /></ul>
    </section>}
    {pat && <section className="iv-sec" aria-label="For the next results call">
      <h2 className="t-b1">For the next results call</h2>
      <p className="stn-ask">{pat.next}</p>
      <p className="net-before"><button className="see" onClick={() => openCompany(n.symbol)}>Open {names[n.symbol] || n.symbol}</button></p>
    </section>}
    <section className="iv-sec"><Synthetic /></section>
  </>
}
