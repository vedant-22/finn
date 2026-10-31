import { useEffect, useRef, useState } from 'react'
import { cr, crBig, deadline, minus, pct, rupees, shortName, tidyEvidence, type Bar, type Company, type Promise_, type Status } from './lib'
import { Accordion, BackBar, Bars, Chart, Fold, fyLabel, Outcome, Src, STATUS_WORD, StatusLabel } from './ui'
import { cap, promiseLine } from './Trail'
import { BeforeAfter } from './Word'

const SHOW: Status[] = ['missed', 'quiet', 'partly', 'kept', 'pending', 'unclear']

export function CompanyView({ c, focus, sector, title, close, bars, back, ask }: { c: Company; focus?: number; sector?: string; title?: string; close?: { d: string; close: number }; bars?: Bar[]; back: () => void; ask?: React.ReactNode }) {
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
  const [showRunning, setShowRunning] = useState(() => focus != null && c.ledger.some(p => p.id === focus && p.hard && ['pending', 'unclear'].includes(p.status)))
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
  const nKept = hard.filter(p => p.status === 'kept').length, nPartly = hard.filter(p => p.status === 'partly').length
  const nGraded = hard.filter(p => ['kept', 'partly', 'missed', 'quiet'].includes(p.status)).length
  const nPending = hard.filter(p => p.status === 'pending').length, nUnclear = hard.filter(p => p.status === 'unclear').length
  const standing = nGraded ? `${nKept} of ${nGraded} ${nGraded === 1 ? 'promise' : 'promises'} kept${nPartly ? `, ${nPartly} partly` : ''}.`
    : nPending ? `${nPending} ${nPending === 1 ? 'promise' : 'promises'}, none due yet.`
      : 'Nothing to grade yet.'

  const newHard = c.open.filter(p => p.hard)
  // What's been settled leads; what's still running waits one tap away
  const settledRows = hard.filter(p => !['pending', 'unclear'].includes(p.status))
  const running = hard.filter(p => ['pending', 'unclear'].includes(p.status))
  const name = title || shortName(c.name)

  return (
    <main className="screen company">
      <BackBar back={back} name={past ? name : undefined} />
      <header className="co-top">
        <p className="small kicker">{sector ? `${sector}, ` : ''}{c.symbol}{c.live ? ', read just now' : ''}</p>
        <h1 className="title" ref={nameRef}>{name}</h1>
        <p className="lede co-rec">{standing}</p>
        {price != null && <div className="co-px">
          <span className="fig fig-s num">₹{price.toLocaleString('en-IN', close ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : undefined)}</span>
          <span className="small">{close ? `At the ${new Date(close.d + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} close.` : ''}{s.mcap != null && <><br />Worth ₹{crBig(s.mcap * k)}{s.pe ? `, ${(s.pe * k).toFixed(1)}× earnings` : ''}.</>}</span>
        </div>}
        {bars && bars.length > 1 && <figure className="r-chart"><Chart series={bars.slice(-30)} h={88} /><figcaption className="small">Last {Math.min(30, bars.length)} sessions</figcaption></figure>}
      </header>

      <section className="sec word">
        <h2 className="head">Their word</h2>
        {c.read && settled >= 3
          ? <p className="read word-intro">{readAll ? rupees(c.read) : readFirst}{readFirst !== rupees(c.read) && <> <button className="link-inline" onClick={() => setReadAll(!readAll)}>{readAll ? 'Read less' : 'Read more'}</button></>}</p>
          : hard.length === 0 && <p className="read word-intro">{readable === 0
            ? `None of the ${c.calls.length} call transcripts linked from its exchange filings could be opened, so there is nothing to grade yet.`
            : 'No promise in these calls had both a number and a date.'}</p>}
        {hard.length > 0 && <p className="small word-tally">{SHOW.filter(st => hard.some(p => p.status === st)).map(st => `${hard.filter(p => p.status === st).length} ${STATUS_WORD[st].toLowerCase()}`).join(', ')}{readable > 1 ? `. Promises with a number and a date, from the ${readable - 1 === 1 ? 'call' : `${readable - 1} calls`} before the latest one.` : '.'}</p>}

        {settledRows.length > 0 && <ul className="rows plist">
          {settledRows.map(p => <PromiseRow key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}
        </ul>}
        {running.length > 0 && (settledRows.length
          ? <Fold title="Still running" count={running.length} open={showRunning} toggle={() => setShowRunning(!showRunning)}
              line={`Not due yet${nUnclear ? `, or can’t be told from what they’ve reported` : ''}`}>
              <ul className="rows plist">{running.map(p => <PromiseRow key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>
            </Fold>
          : <ul className="rows plist">{running.map(p => <PromiseRow key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>)}

        {soft.length > 0
          ? <Fold title="Said without a number or date" count={soft.length} open={showSoft} toggle={() => setShowSoft(!showSoft)}
              line="Not graded: nothing to hold them to">
              <ul className="soft-list">{soft.map(p => <SoftRow key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>
            </Fold>
          : softTalk > 0 && <p className="small soft-note">Plus {softTalk} {softTalk === 1 ? 'statement' : 'statements'} with no number or date. Not graded.</p>}
      </section>

      {ask}
      {c.questions.length > 0 && (
        <section className="sec next-call">
          <h2 className="head">Ask on the next call</h2>
          <ol>{c.questions.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ol>
          <CopyQuestions name={title || shortName(c.name)} qs={c.questions.map(rupees)} />
        </section>
      )}

      {newHard.length > 0 && (
        <Fold title="New on the latest call" count={newHard.length} line={`From the ${newHard[0]?.period} call; too new to check against results`} open={showOpen} toggle={() => setShowOpen(!showOpen)}>
          <ul className="open-list fold-body">
            {newHard.map((p, i) => (
              <li key={i}>
                <span className="open-t">{cap(rupees(p.target))}</span> <span className="sub">{rupees(deadline(p))}</span>
                <blockquote>“{p.quote}” <Src href={`${p.url}#page=${p.page}`}>{p.period}, page {p.page}</Src></blockquote>
              </li>
            ))}
          </ul>
        </Fold>
      )}

      <Fold title="The numbers" line={lastQ ? `The ${lastQ.q} quarter, ${s.years.length} years of revenue and profit${s.financial ? '' : ', cash and debt'}` : `${s.years.length} years of revenue and profit`} open={fold === 'num'} toggle={() => toggle('num')}>
        <div className="fold-body">
          {lastQ && (
            <div className="fig-grid">
              <Fig label={`Revenue, ${lastQ.q}`} value={`₹${cr(lastQ.rev)}`} unit="cr" sub={lastQ.rev_yoy != null ? `${pct(lastQ.rev_yoy)} on a year ago` : null} />
              <Fig label="Profit after tax" value={`₹${cr(lastQ.pat)}`} unit="cr" sub={yoy('pat')} />
              {!s.financial
                ? <Fig label="Operating margin" value={`${lastQ.opm ?? '–'}`} unit="%" sub={<>{q.slice(-4).map((x: any) => x.opm ?? '–').join(', ')}% over 4 quarters</>} />
                : <Fig label="Net interest income" value={`₹${cr(lastQ.op)}`} unit="cr" sub={yoy('op')} />}
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
        <Fold title="For and against" line={`${c.bull.length} ${c.bull.length === 1 ? 'point' : 'points'} for, ${c.bear.length} against`} open={fold === 'case'} toggle={() => toggle('case')}>
          <div className="case fold-body">
            <div><h3 className="lbl lbl-quiet">For</h3><ul>{c.bull.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ul></div>
            <div><h3 className="lbl lbl-quiet">Against</h3><ul>{c.bear.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ul></div>
          </div>
        </Fold>
      )}

      <Fold title="Read for this page" line={`${readable} earnings ${readable === 1 ? 'call' : 'calls'}${pages ? `, ${pages} pages` : ''}, and the filed results`} open={fold === 'src'} toggle={() => toggle('src')}>
        <div className="sources fold-body">
          <ul>
            {c.calls.map(x => {
              // What this call adds to the page: promises with a number and a date first made on it (repeats sit with the first call).
              // The tally note says what counts and the line below says the quotes were checked, so each row is just the count
              const n = [...c.ledger, ...c.open].filter(p => p.hard && p.period === x.period).length
              return (
                <li key={x.period}><Src href={x.url}>{x.period} call</Src>
                  <span className="sub">{x.error ? 'Could not be read' : !n ? `${x.pages} pages, none to grade` : `${x.pages} pages, ${n} ${n === 1 ? 'promise' : 'promises'}`}</span></li>
              )
            })}
            <li><Src href={c.source}>Financial tables</Src><span className="sub">screener.in, {c.basis}, compiled from filed results</span></li>
          </ul>
          {pages > 0 && <p className="sub">Read {pages} pages. Every quote above was matched to its page in the PDF{dropped ? `; ${dropped} that didn’t match ${dropped === 1 ? 'was' : 'were'} thrown out` : ''}. Nothing here comes from news, brokers or the model’s own memory.</p>}
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

function Fig({ label, value, unit, sub }: { label: string; value: string; unit?: string; sub: any }) {
  return <div className="fig og-item"><Outcome size={value.length > 9 ? 'xxs' : value.length > 5 ? 'xs' : 's'} value={value} unit={unit} /><span className="og-d1">{label}</span>{sub && <span className="og-d2">{sub}</span>}</div>
}

// One promise as a row: what they promised, its verdict and when it was said. It opens on the before-and-after
function PromiseRow({ p, open, toggle }: { p: Promise_; open: boolean; toggle: () => void }) {
  return (
    <li className={`prow${open ? ' open' : ''}`} data-pid={p.id}>
      <button className="prow-head" aria-expanded={open} onClick={toggle}>
        <span className="prow-t">{promiseLine(p)}</span>
        <span className="prow-meta"><StatusLabel status={p.status} /><span className="small">Said {p.period.replace(/ 20/, ' ’')}</span></span>
        <svg className="chev" viewBox="0 0 16 16" aria-hidden><path d="M3.5 6l4.5 4.5L12.5 6" /></svg>
      </button>
      <Accordion open={open}><div className="prow-body"><BeforeAfter p={p} inRow /></div></Accordion>
    </li>
  )
}

// A statement with no number or date isn't graded: no verdict, only the quote behind the tap
function SoftRow({ p, open, toggle }: { p: Promise_; open: boolean; toggle: () => void }) {
  return (
    <li className={`soft-row${open ? ' open' : ''}`} data-pid={p.id}>
      <button className="og-btn" aria-expanded={open} onClick={toggle}>
        <span className="og-d1">{promiseLine(p)}.</span>
        <span className="og-d2">Said {p.period.replace(/ 20/, ' ’')}</span>
      </button>
      {open && (
        <div className="p-detail">
          <blockquote>“{p.quote}”</blockquote>
          <p className="sub">{p.speaker}, <Src href={`${p.url}#page=${p.page}`}>{p.period} call, page {p.page}</Src></p>
        </div>
      )}
    </li>
  )
}

// For the call prep notes: the questions as plain numbered text
function CopyQuestions({ name, qs }: { name: string; qs: string[] }) {
  const [done, setDone] = useState(false)
  if (!navigator.clipboard) return null
  const copy = () => navigator.clipboard.writeText(`${name}: ask on the next call\n${qs.map((q, i) => `${i + 1}. ${q}`).join('\n')}`)
    .then(() => { setDone(true); setTimeout(() => setDone(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return <button className="btn btn-line copy" onClick={copy} aria-live="polite">{done ? 'Copied' : 'Copy the questions'}</button>
}
