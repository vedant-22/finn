// Your data: what FINN holds, where each fact came from, what stays on this phone, what a model reads, and what
// doesn't work here. ADR 1's "What the app says", on the phone. Every count and date comes from the served files,
// the list of what stays on the phone from storage.ts, and whether reading works from the server's own answer.
import { useEffect, useState } from 'react'
import { builtCompanies, liveStatus, type Push } from './lib'
import { useNetwork } from './Network'
import { GROUPS, clearPhone } from './storage'
import { Sheet } from './ui'

const OPEN = 'finn:yourdata'
export const openYourData = () => window.dispatchEvent(new Event(OPEN))

// Whether reading a new company works here (undefined while asking, null if the server couldn't say), and how many
// companies FINN has read; and the one sentence that says reading is off, used here and on Look up before the tap
export function useLive() {
  const [live, setLive] = useState<boolean | null | undefined>(undefined)
  const [built, setBuilt] = useState(0)
  useEffect(() => {
    let on = true
    liveStatus().then(v => on && setLive(v))
    builtCompanies().then(n => on && setBuilt(n))
    return () => { on = false }
  }, [])
  return { live, built }
}
export const readingOff = (built: number) => `Reading a new company is off on this link: it isn’t connected to a model yet. The ${built || ''} companies FINN has already read all open.`.replace('The  ', 'The ')

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
// '2026-10-28T21:21' as the snapshot wrote it (India time): '28 Oct', and '9:21 pm on 28 Oct 2026'
const day = (iso: string) => `${+iso.slice(8, 10)} ${MON[+iso.slice(5, 7) - 1]}`
function stamp(iso: string) {
  const h = +iso.slice(11, 13), m = iso.slice(14, 16)
  return `${h % 12 || 12}:${m} ${h < 12 ? 'am' : 'pm'} on ${day(iso)} ${iso.slice(0, 4)}`
}

// The masthead's door: the demo's day, stated once, on Today, Book and Look up. A real install has no pill;
// its door is the Your data row at the foot of Your alert levels.
export function DemoPill({ push }: { push: Push }) {
  if (!push.synthetic) return null
  const d = day(push.asof)
  // The name starts with what is shown, so voice control finds it by what it says (WCAG 2.5.3)
  return <button className="demo-pill" onClick={openYourData} aria-label={`Sample data, as of ${d}. Your data`}><span>Sample data, as of {d}</span></button>
}

export function YourDataRow({ before }: { before?: () => void }) {
  return (
    <button className="fo-row yd-row" onClick={() => { before?.(); openYourData() }}>
      <span className="fo-row-t">Your data</span>
      <svg className="fo-row-arrow" viewBox="0 0 16 16" aria-hidden><path d="M6 3.5l4.5 4.5L6 12.5" /></svg>
    </button>
  )
}

export function YourData({ push }: { push: Push }) {
  const [open, setOpen] = useState(false)
  const [live, setLive] = useState<boolean | null | undefined>(undefined)
  const [built, setBuilt] = useState(0)
  const [confirm, setConfirm] = useState(false)
  const net = useNetwork()
  useEffect(() => { const on = () => setOpen(true); addEventListener(OPEN, on); return () => removeEventListener(OPEN, on) }, [])
  useEffect(() => {
    if (!open) { setConfirm(false); return }
    let on = true
    liveStatus().then(v => on && setLive(v))
    builtCompanies().then(n => on && setBuilt(n))
    return () => { on = false }
  }, [open])
  const held = push.portfolio.length
  const oldest = push.filings.reduce((a, f) => (f.at < a ? f.at : a), push.asof)
  const companies = built || 'the'
  const people = net?.synthetic ? `the ${net.contacts} people you know here` : 'the people you know'
  const clear = async () => { await clearPhone(); history.replaceState(null, '', location.pathname); location.reload() }

  return (
    <Sheet open={open} onClose={() => setOpen(false)} title="Your data" full>
      <div className="yd">
        <section className="yd-sec">
          {push.synthetic
            ? <><h3>A sample, frozen at {day(push.asof)}</h3>
              <p>Announcements and prices stop at {stamp(push.asof)}, so every figure can be checked against its filing. The {held} holdings and {people} are made up, the same for everyone who opens this link. The companies, their filings and the people named in them are real.</p></>
            : <><h3>Up to {day(push.asof)}</h3><p>Announcements and prices stop at {stamp(push.asof)}.</p></>}
        </section>

        <section className="yd-sec">
          <h3>What stays on this phone</h3>
          <ul className="yd-list">{GROUPS.map(g => <li key={g.group}>{g.label}</li>)}</ul>
          <p>They stay until you clear them. FINN’s server reads your questions, and your answers on whether two names are the same person, without writing them down. To limit how often it is asked, it holds your internet address for about ten minutes. Its host keeps a log of each request for an hour, never what you sent.</p>
          <p className="yd-real"><span>In a real install</span> Your holdings and contacts come in only with your consent, item by item, and only you can read them. If you withdraw consent they are deleted, closing your account erases every copy, and a contact can ask to be removed.</p>
        </section>

        <section className="yd-sec">
          <h3>What an AI model reads</h3>
          <p>Only public filings, read once for everyone: never your holdings, your people, your questions or your answers. In this sample a model read {companies} companies, including the {held} in the made-up holdings, so the model’s provider could see that list. A company you look up is added to it.</p>
          <p className="yd-real"><span>In a real install</span> The whole market is read whatever anyone holds. A question goes to a model that may not train on it, without your name or holdings, and FINN doesn’t keep it.</p>
        </section>

        <section className="yd-sec">
          <h3>Where each fact comes from</h3>
          <dl className="yd-src">
            <dt>Filings</dt><dd>Announcements on NSE, the stock exchange: {push.filings.length} from {day(oldest)} to {day(push.asof)}</dd>
            <dt>Prices</dt><dd>NSE’s daily closing prices</dd>
            <dt>Results</dt><dd>The exchange’s own results data, read by code, not a model</dd>
            <dt>Promises</dt><dd>Results calls of {companies} companies, read by a model; each quote found on its page</dd>
            <dt>People</dt><dd>The company’s own filing, printed as filed</dd>
          </dl>
          <p>FINN reads a filing as text to check, never as orders to follow. Results figures come from the exchange’s own data. A model writes the one-line summaries of some filings, each linked to its filing. It also writes each company’s summary and questions, and the company page says so.</p>
        </section>

        <section className="yd-sec">
          <h3>When something doesn’t work</h3>
          <p className="yd-live">{live === undefined ? 'Checking this link…'
            : live === null ? 'Couldn’t check just now whether reading a new company works here.'
              : live ? `Reading a new company is on: it takes about a minute.`
                : readingOff(built)}</p>
          <p>With no signal, FINN opens the last snapshot this phone saw.</p>
        </section>

        <section className="yd-foot">
          {confirm
            ? <div className="yd-confirm" role="group" aria-label="Clear this phone">
              <p>Clear your alert levels, reading, answers and the saved copy?</p>
              <div className="fail-acts"><button className="btn-primary" onClick={clear}>Clear</button><button className="btn-outline" autoFocus onClick={() => setConfirm(false)}>Keep</button></div>
            </div>
            : <button className="btn-outline" onClick={() => setConfirm(true)}>Clear this phone</button>}
          <p className="yd-fine">FINN is a prototype for ENAM Holdings, not yet an ENAM product. Information from filings, not investment advice. In a real install, the firm’s grievance officer answers questions about your data.</p>
        </section>
      </div>
    </Sheet>
  )
}
