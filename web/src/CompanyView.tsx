import { useEffect, useRef, useState } from 'react'
import { cr, crBig, deadline, minus, pct, rupees, shortName, tidyEvidence, type Company, type Promise_, type Status } from './lib'
import { Bars, Fold, fyLabel, Outcome, Src, STATUS_WORD, StatusLabel } from './ui'

const SHOW: Status[] = ['missed', 'quiet', 'partly', 'kept', 'pending', 'unclear']

export function CompanyView({ c, focus, sector, title, close, back }: { c: Company; focus?: number; sector?: string; title?: string; close?: { d: string; close: number }; back: () => void }) {
  const [openId, setOpenId] = useState<number | null>(focus ?? null)
  // Opened from a promise elsewhere: bring that promise to the middle of the screen
  useEffect(() => {
    if (focus == null) return
    const el = document.querySelector(`[data-pid="${focus}"]`)
    // Focus follows, so a screen reader starts at that promise too
    if (el) requestAnimationFrame(() => { el.scrollIntoView({ block: 'center' }); el.querySelector('button')?.focus({ preventScroll: true }) })
  }, [focus])
  const [showSoft, setShowSoft] = useState(() => focus != null && c.ledger.some(p => p.id === focus && !p.hard))
  const [showOpen, setShowOpen] = useState(false)
  const [fold, setFold] = useState<string | null>(null)
  const [readAll, setReadAll] = useState(false)
  const s = c.snapshot
  // The file's price is from when the ledger was built; the snapshot's last close is newer. Same shares, so value and P/E move with it
  const price = close?.close ?? s.price
  const k = close && s.price ? close.close / s.price : 1
  const readable = c.calls.filter(x => !x.error).length
  const hard = c.ledger.filter(p => p.hard).sort((a, b) => SHOW.indexOf(a.status) - SHOW.indexOf(b.status))
  const soft = c.ledger.filter(p => !p.hard)
  // The model's one-paragraph read only shows once enough promises have actually been settled.
  const settled = hard.filter(p => ['kept', 'missed', 'partly'].includes(p.status)).length
  const softTalk = c.calls.reduce((n, x) => n + (x.soft || 0), 0) + soft.length
  const pages = c.calls.reduce((n, x) => n + (x.pages || 0), 0)
  const dropped = c.calls.reduce((n, x) => n + (x.dropped || 0), 0)
  const q = c.quarters
  const lastQ = q[q.length - 1]
  // Year on year from the same quarter a year back, when it's in the file and positive.
  const yearAgo = q[q.length - 5]
  const yoy = (k: string) => {
    const a = yearAgo?.[k], b = lastQ?.[k]
    if (a == null || b == null || a <= 0 || yearAgo.q.split(' ')[0] !== lastQ.q.split(' ')[0]) return null
    const v = (b / a - 1) * 100
    return <>{pct(v)} on a year ago</>
  }

  // Back stays in reach on a long page; once the name scrolls off, the bar carries it
  const nameRef = useRef<HTMLHeadingElement>(null)
  const [past, setPast] = useState(false)
  useEffect(() => {
    const el = nameRef.current
    if (!el || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver(([e]) => setPast(!e.isIntersecting && e.boundingClientRect.top < 0))
    io.observe(el); return () => io.disconnect()
  }, [])

  const readFirst = c.read ? rupees(c.read).match(/^.+?[.!?](?=\s+[A-Z]|$)/)?.[0] ?? rupees(c.read) : ''
  const toggle = (k: string) => setFold(fold === k ? null : k)
  const newHard = c.open.filter(p => p.hard)

  return (
    <main className="screen company">
      <header className={`bar${past ? ' past' : ''}`}>
        <button className="text-btn back" onClick={back}>Back</button>
        {past ? <span className="bar-name">{title || shortName(c.name)}</span> : <span className="lbl lbl-quiet">{c.symbol}{c.live ? ', read just now' : ''}</span>}
      </header>
      <h1 className="co-name" ref={nameRef}>{title || shortName(c.name)}</h1>
      <p className="co-meta">
        {sector && <>{sector}. </>}
        {price != null && <>₹{price.toLocaleString('en-IN', close ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : undefined)}{close && ` at the ${new Date(close.d + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} close`}. </>}
        {s.mcap != null && <>Worth ₹{crBig(s.mcap * k)}{s.pe ? `, ${(s.pe * k).toFixed(1)}× earnings` : ''}.</>}
      </p>

      <section className="word">
        <h2 className="sec-head">Their word</h2>
        {c.read && settled >= 3
          ? <p className="read word-intro">{readAll ? rupees(c.read) : readFirst}{readFirst !== rupees(c.read) && <> <button className="see" onClick={() => setReadAll(!readAll)}>{readAll ? 'Read less' : 'Read more'}</button></>}</p>
          : hard.length === 0 && <p className="read word-intro">{readable === 0
            ? `None of the ${c.calls.length} call transcripts linked from its exchange filings could be opened, so there is nothing to grade yet.`
            : 'No promise in these calls had both a number and a date.'}</p>}
        {hard.length > 0 && (
          <div className="og-panel">
            <ul className="og" aria-label="Promise record">
              {SHOW.map(st => {
                const n = hard.filter(p => p.status === st).length
                return n ? <li key={st} className="og-item"><Outcome value={n} /><span className="og-d1">{STATUS_WORD[st]}</span></li> : null
              })}
            </ul>
            {readable > 1 && <p className="sub tally-note">Promises with a number and a date, from the {readable - 1 === 1 ? 'call' : `${readable - 1} calls`} before the latest one.</p>}
          </div>
        )}

        {hard.length > 0 && <ul className="og pgrid">
          {hard.map(p => <PromiseItem key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}
        </ul>}

        {softTalk > 0 && (
          <button className="soft" aria-expanded={showSoft} onClick={() => setShowSoft(!showSoft)}>
            Plus {softTalk} {softTalk === 1 ? 'statement' : 'statements'} with no number or date. Not graded.
          </button>
        )}
        {showSoft && <ul className="og pgrid soft-list">{soft.map(p => <PromiseItem key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>}
      </section>

      {c.questions.length > 0 && (
        <section className="ask">
          <h2 className="sec-head ask-head">Ask on the next call</h2>
          <ol>{c.questions.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ol>
          <CopyQuestions name={title || shortName(c.name)} qs={c.questions.map(rupees)} />
        </section>
      )}

      {newHard.length > 0 && (
        <Fold title={`New on the latest call`} count={newHard.length} open={showOpen} toggle={() => setShowOpen(!showOpen)}>
          <ul className="open-list fold-body">
            {newHard.map((p, i) => (
              <li key={i}>
                <b className="og-d1" style={{ padding: 0 }}>{cap(rupees(p.target))}</b> <span className="sub">{deadline(p)}</span>
                <blockquote>“{p.quote}” <Src href={`${p.url}#page=${p.page}`}>{p.period}, page {p.page}</Src></blockquote>
              </li>
            ))}
          </ul>
        </Fold>
      )}

      <Fold title="The numbers" open={fold === 'num'} toggle={() => toggle('num')}>
        <div className="fold-body">
          {lastQ && (
            <div className="fig-grid">
              <Fig label={`Revenue, ${lastQ.q}`} value={`₹${cr(lastQ.rev)}`} unit="cr" sub={lastQ.rev_yoy != null ? `${pct(lastQ.rev_yoy)} on a year ago` : null} />
              {!s.financial
                ? <Fig label="Operating margin" value={`${lastQ.opm ?? '–'}`} unit="%" sub={<>{q.slice(-4).map((x: any) => x.opm ?? '–').join(', ')} over 4 quarters</>} />
                : <Fig label="Net interest income" value={`₹${cr(lastQ.op)}`} unit="cr" sub={yoy('op')} />}
              <Fig label="Profit after tax" value={`₹${cr(lastQ.pat)}`} unit="cr" sub={yoy('pat')} />
            </div>
          )}
          <div className="traj">
            <div>
              <h3>Revenue, {s.years.length} years</h3>
              <Bars values={s.rev} labels={s.years} />
              <p className="sub">{s.rev_cagr5 != null ? `${pct(s.rev_cagr5, false)} a year` : ''}</p>
            </div>
            <div>
              <h3>Profit after tax</h3>
              <Bars values={s.pat} labels={s.years} />
              <p className="sub">{s.pat_cagr5 != null ? `${pct(s.pat_cagr5, false)} a year` : ''}</p>
            </div>
          </div>
          {!s.financial && (
            <div className="fig-grid">
              <Fig label="Cash from operations per ₹100 of profit, 5 years" value={s.cash_conversion5 != null ? `₹${s.cash_conversion5}` : '–'}
                sub={s.cash_conversion5 != null ? (s.cash_conversion5 >= 90 ? 'Profits are turning into cash.' : s.cash_conversion5 >= 60 ? 'Some profit is stuck in working capital.' : 'Profits are not turning into cash.') : null} />
              <Fig label="Debt to equity" value={s.de != null ? minus(s.de) : '–'} unit={s.de != null ? '×' : undefined} sub={s.debt != null ? `₹${crBig(s.debt)} borrowed` : null} />
              <Fig label="Cash conversion cycle" value={s.ccc?.length ? minus(s.ccc[s.ccc.length - 1]) : '–'} unit={s.ccc?.length ? 'days' : undefined}
                sub={s.ccc?.length > 1 ? `${minus(s.ccc[0])} days in ${fyLabel(s.years[0])}` : null} />
              <Fig label="Return on capital" value={s.roce?.length ? minus(s.roce[s.roce.length - 1]) : '–'} unit={s.roce?.length ? '%' : undefined} sub={s.roce?.length > 1 ? `${minus(s.roce[0])}% in ${fyLabel(s.years[0])}` : null} />
            </div>
          )}
        </div>
      </Fold>

      {(c.bull.length > 0 || c.bear.length > 0) && (
        <Fold title="For and against" open={fold === 'case'} toggle={() => toggle('case')}>
          <div className="case fold-body">
            <div><h3 className="lbl lbl-quiet">For</h3><ul>{c.bull.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ul></div>
            <div><h3 className="lbl lbl-quiet">Against</h3><ul>{c.bear.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ul></div>
          </div>
        </Fold>
      )}

      <Fold title="Read for this page" open={fold === 'src'} toggle={() => toggle('src')}>
        <div className="sources fold-body">
          <ul>
            {c.calls.map(x => {
              // What this call adds to the page: promises with a number and a date first made on it (repeats sit with the first call)
              const n = [...c.ledger, ...c.open].filter(p => p.hard && p.period === x.period).length
              return (
                <li key={x.period}><Src href={x.url}>{x.period} call</Src>
                  <span className="sub"> {x.error ? 'could not be read' : !n ? `${x.pages} pages, no new promise with a number and a date` : `${x.pages} pages, ${n} ${n === 1 ? 'promise' : 'promises'} with a number and a date, quotes checked`}</span></li>
              )
            })}
            <li><Src href={c.source}>Financial tables</Src><span className="sub"> screener.in, {c.basis}, compiled from filed results</span></li>
          </ul>
          {pages > 0 && <p className="sub">Read {pages} pages. Every quote above was matched to its page in the PDF{dropped ? `; ${dropped} that didn't match ${dropped === 1 ? 'was' : 'were'} thrown out` : ''}. Nothing here comes from news, brokers or the model's own memory.</p>}
          {c.usage?.calls > 0 && <p className="sub">{c.usage.calls} model calls, {Math.round((c.usage.tokens_in + c.usage.tokens_out) / 1000)}k tokens, about ${c.usage.usd_if_billed.toFixed(2)} if billed. {grader(c.usage.by_model)}</p>}
        </div>
      </Fold>
    </main>
  )
}

const grader = (by: Record<string, number> = {}) =>
  !Object.keys(by).length ? '' : by['gemini-3.5-flash'] ? 'Graded by gemini-3.5-flash.'
    : 'Graded by gemini-3.5-flash-lite: the stronger model’s free daily quota was used up.'
// 'X remains ongoing.' / 'X is pending.' only restates the promise; the dash mark already says not due yet
const FILLER = /\b(remains|is) (still )?(pending|ongoing)\b|\bnot yet due\b/i
const verdictText = (p: Promise_) => p.status === 'pending' && FILLER.test(p.verdict || '') ? '' : p.verdict ? rupees(p.verdict) : STATUS_WORD[p.status]
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)

function Fig({ label, value, unit, sub }: { label: string; value: string; unit?: string; sub: any }) {
  return <div className="fig og-item"><Outcome size={value.length > 9 ? 'xxs' : value.length > 5 ? 'xs' : 's'} value={value} unit={unit} /><span className="og-d1">{label}</span>{sub && <span className="og-d2">{sub}</span>}</div>
}

// The figure they promised, pulled from the promise itself: '15%', '₹5,600–5,800 cr', '0.8–0.9×'.
// A number glued to letters ('FY26', 'Q3', 'Lakshya 31' is fine) is a date or a name, not the figure; so is a bare year.
const FIG = /(₹\s?|\$)?(\d[\d,]*(?:\.\d+)?)(?:\u2060?[–-]\u2060?(\d[\d,]*(?:\.\d+)?))?\s?(%|x\b|×|bps|lakh crore|crore|cr\b|GW|MW|MVA|days|months|years|million tons?|million|billion|trillion|lakh|KTPA|MTPA)?s?(?![a-z])/gi
function promised(t: string): [string, string] | null {
  // '12 to 15 percent', '23% to 24%' -> '12–15%', '23–24%'
  const txt = rupees(t).replace(/\bpercent\b/gi, '%').replace(/\s+%/g, '%')
    .replace(/(\d+(?:\.\d+)?) (billion|million|crore) to (\d+(?:\.\d+)?) \2/g, '$1–$3 $2')
    .replace(/(\d+(?:\.\d+)?)%?[\s\u2060]*(?:to|[-–])[\s\u2060]*(\d+(?:\.\d+)?)(?=\s?%)/g, '$1–$2').replace(/(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)/g, '$1–$2')
  for (const m of txt.matchAll(FIG)) {
    if (/[A-Za-z]$/.test(txt.slice(0, m.index))) continue
    // A bare number ('plant 2', 'August 25', 'mid-20s') says nothing on its own; only a unit or a currency makes it the figure
    if (!m[1] && !m[4]) continue
    const u = m[4] || '', unit = /^x$/i.test(u) ? '×' : /^crore$/i.test(u) ? 'cr' : /^lakh crore$/i.test(u) ? 'lakh cr' : /^(mva|gw|mw|ktpa|mtpa|bps)$/i.test(u) ? (u.toLowerCase() === 'bps' ? 'bps' : u.toUpperCase()) : u.toLowerCase()
    return [`${m[1] ? m[1].trim() : ''}${m[2]}${m[3] ? `–${m[3]}` : ''}`, unit === '%' || unit === '×' ? unit : unit ? ` ${unit}` : '']
  }
  // A count of things: 'Add 6 new branches', '50 new branches', '100–200 trucks'
  const n = txt.match(/(?<![\w.])(\d[\d,]*(?:–\d[\d,]*)?)\s+(?:new\s+|more\s+|additional\s+)?(branches|clients|stores|trucks|rooftops|ships|rakes|products|plants|tires|outlets|customers)\b/i)
  if (n) return [n[1], ` ${n[2].toLowerCase()}`]
  return null
}
// No figure in the promise: the year it's due, as they named it ('FY26'), else when it was said
const dueFig = (p: Promise_) => `${p.target} ${deadline(p)}`.match(/\b(Q\d )?FY\d\d\b|\b20\d\d\b/)?.[0]

// One promise as an outcome: the figure, what they said, the verdict word. Tap for the quote and the evidence.
function PromiseItem({ p, open, toggle }: { p: Promise_; open: boolean; toggle: () => void }) {
  const fig = promised(p.target), due = fig ? undefined : dueFig(p)
  const len = (fig?.[0] || '').replace(/\u2060/g, '').length + (fig?.[1] || '').trim().length
  const size = !fig ? 'xs' : len <= 5 ? 's' : len <= 9 ? 'xs' : 'xxs'
  return (
    <li className={`og-item p-item st-${p.status}${open ? ' open' : ''}`} data-pid={p.id}>
      <button className="og-btn" aria-expanded={open} onClick={toggle}>
        {fig ? <Outcome size={size} value={fig[0]} unit={fig[1]} /> : due ? <Outcome size="xs" value={due} /> : <span className="o-gap" aria-hidden />}
        <span className="og-d1" style={{ display: 'block' }}>{cap(rupees(p.target))}{deadline(p) ? ` ${deadline(p)}` : ''}.</span>
        <span className="og-d2" style={{ display: 'block' }}>Said {p.period.replace(/ 20/, ' ’')}</span>
      </button>
      <StatusLabel status={p.status} />
      {open && (
        <div className="p-detail">
          {verdictText(p) && <p className="verdict-t">{verdictText(p)}</p>}
          <div>
            <h4 className="lbl lbl-quiet">Said</h4>
            <blockquote>“{p.quote}”</blockquote>
            <p className="sub">{p.speaker}, <Src href={`${p.url}#page=${p.page}`}>{p.period} call, page {p.page}</Src>
              {p.restated?.length ? <>. Said again: {p.restated.filter((r, k, all) => all.findIndex(x => x.period === r.period) === k).map((r, k) => <span key={k}>{k ? ', ' : ' '}<Src href={`${r.url}#page=${r.page}`}>{r.period}</Src></span>)}</> : null}</p>
          </div>
          {p.evidence && (
            <div>
              <h4 className="lbl lbl-quiet">{p.evidence_kind === 'quote' ? 'Latest call' : 'Reported'}</h4>
              {p.evidence_kind === 'quote'
                ? <><blockquote>“{p.evidence}”</blockquote><p className="sub"><Src href={p.evidence_url ? `${p.evidence_url}#page=${p.evidence_page}` : undefined}>page {p.evidence_page}</Src></p></>
                : <p className="verdict-t">{tidyEvidence(p.evidence)}</p>}
            </div>
          )}
        </div>
      )}
      {!open && <a className="og-link" href={`${p.url}#page=${p.page}`} target="_blank" rel="noopener noreferrer">See the call</a>}
    </li>
  )
}

// For the call prep notes: the questions as plain numbered text
function CopyQuestions({ name, qs }: { name: string; qs: string[] }) {
  const [done, setDone] = useState(false)
  if (!navigator.clipboard) return null
  const copy = () => navigator.clipboard.writeText(`${name}: ask on the next call\n${qs.map((q, i) => `${i + 1}. ${q}`).join('\n')}`)
    .then(() => { setDone(true); setTimeout(() => setDone(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return <button className="text-btn copy" onClick={copy} aria-live="polite">{done ? 'Copied' : 'Copy the questions'}</button>
}
