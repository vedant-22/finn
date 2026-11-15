import { NetCompany, useNetNext } from './Network'
import { useEffect, useRef, useState } from 'react'
import { useDrift } from './motion'
import { cr, crBig, dayMon, deadline, minus, pct, rupees, shortName, tidyEvidence, whoAsked, type Bar, type Company, type Promise_, type Status } from './lib'
import { Accordion, BackBar, Bars, Chart, Fold, fyLabel, Outcome, SettleImg, Src, STATUS_WORD, StatusLabel } from './ui'
import { cap, plainTerms, promiseLine, verdictText } from './Trail'
import { BeforeAfter } from './Word'
import { monthLabel } from './Brief'
import { AnnualFold, annualQuestions, useAnnual } from './Annual'

const SHOW: Status[] = ['missed', 'quiet', 'partly', 'kept', 'pending', 'unclear']

export function CompanyView({ c, focus, sector, title, close, bars, back, ask }: { c: Company; focus?: number; sector?: string; title?: string; close?: { d: string; close: number }; bars?: Bar[]; back: () => void; ask?: React.ReactNode }) {
  const [openId, setOpenId] = useState<number | null>(focus ?? null)
  // The company's own questions for the next call, any the Network raises from its filings read together,
  // and any FINN's rules raise from the annual report's notes
  const net = useNetNext(c.symbol)
  const annual = useAnnual(c.symbol)
  const fromReport = annualQuestions(annual)
  const next = [...c.questions.map(x => plainTerms(rupees(x))), ...net, ...fromReport]
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
  // The first FY the promises name, said once in plain months: Indian companies' year runs April to March
  const fy = Number(hard.map(p => p.by_when.match(/FY ?(\d\d)\b/)?.[1]).find(Boolean) || 0)
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
    return <>{pct(v)} from a year earlier</>
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
  // What came due, counted as Book and the full view count it (wordScore): a promise past its date with nothing said is in
  const nGraded = hard.filter(p => ['kept', 'partly', 'missed', 'quiet'].includes(p.status) || p.checked === 'past_due').length
  const nPending = hard.filter(p => p.status === 'pending').length, nUnclear = hard.filter(p => p.status === 'unclear').length
  const standing = nGraded ? `${nKept} of ${nGraded} ${nGraded === 1 ? 'promise' : 'promises'} kept${nPartly ? `, ${nPartly} partly` : ''}.`
    : nPending ? `${nPending} ${nPending === 1 ? 'promise' : 'promises'}, none due yet.`
      : 'Nothing to check yet.'

  const newHard = c.open.filter(p => p.hard)
  // What's been settled leads; what's still running waits one tap away
  const settledRows = hard.filter(p => !['pending', 'unclear'].includes(p.status))
  const running = hard.filter(p => ['pending', 'unclear'].includes(p.status))
  const name = title || shortName(c.name)
  const topRef = useRef<HTMLDivElement>(null)
  useDrift(topRef)

  return (
    <main className="screen company">
      {/* The page opens warm, as v4's did: the sector, the name in grey running into the one thing to know, the price */}
      <BackBar back={back} name={past ? name : undefined} band={!past} />
      <div className="co-top" ref={topRef}>
        <p className="lbl lbl-quiet co-sector">{sector || 'NSE'}, {c.symbol}{c.live ? ', read just now' : ''}</p>
        {/* v4's two-tone title, chosen: avoid-ai-design-ignore: SD5 */}
        <h1 className="co-name" ref={nameRef}><span className="co-name-n">{name}.</span> {standing}</h1>
        <p className="co-meta">
          {price != null && <>₹{price.toLocaleString('en-IN', close ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : undefined)}{close && ` at the ${dayMon(new Date(close.d + 'T12:00:00'))} close`}. </>}
          {s.mcap != null && <>Worth ₹{crBig(s.mcap * k)}{s.pe ? `, ${(s.pe * k).toFixed(1)}× earnings` : ''}.</>}
        </p>
      </div>
      {bars && bars.length > 1 && <div className="co-pic"><SettleImg><Chart series={bars.slice(-30)} /></SettleImg><p className="co-pic-cap">{monthLabel(bars.slice(-30))}</p></div>}

      <section className="word">
        <h2 className="sec-head">What they promised</h2>
        {c.read && settled >= 3
          ? <><p className="read word-intro">{readAll ? plainTerms(rupees(c.read)) : plainTerms(readFirst)}{readFirst !== rupees(c.read) && <> <button className="see" onClick={() => setReadAll(!readAll)}>{readAll ? 'Read less' : 'Read more'}</button></>}</p>
            <p className="who-wrote">Drafted by AI from the promises below. Each verdict and its quote is checked against the calls and reported numbers; this paragraph is the AI’s own words.</p></>
          : hard.length === 0 && <p className="read word-intro">{readable === 0
            ? `None of the ${c.calls.length} results-call transcripts linked from its exchange filings could be opened, so there is nothing to check yet.`
            : 'No promise in these calls had both a number and a date.'}</p>}
        {hard.length > 0 && (
          <div className="og-panel">
            {nUnclear < hard.length && <ul className="og" aria-label="Promise record">
              {SHOW.filter(st => st !== 'unclear').map(st => {
                const n = hard.filter(p => p.status === st).length
                return n ? <li key={st} className="og-item"><Outcome value={n} /><span className="og-d1">{STATUS_WORD[st]}</span></li> : null
              })}
            </ul>}
            {/* Can't tell is a footnote, not a count: it says nothing about whether they did it */}
            {(readable > 1 || nUnclear > 0) && <p className="sub tally-note">
              {readable > 1 && `These are promises with a number and a date, from the ${readable - 1 === 1 ? 'results call' : `${readable - 1} results calls`} before the latest one.`}
              {nUnclear > 0 && `${readable > 1 ? ' ' : ''}For ${nUnclear} of these promises, the company hasn’t reported enough yet to tell.`}
              {readable > 1 && fy > 0 && ` FY${fy} is the year from April 20${String(fy - 1).padStart(2, '0')} to March 20${fy}.`}
            </p>}
          </div>
        )}

        {/* What's been settled leads, figure by figure; what's still running waits one tap away */}
        {settledRows.length > 0 && <><h3 className="sec-head pgrid-head">Promise by promise</h3>
          <ul className="og pgrid pgrid-one">{settledRows.map(p => <PromiseItem key={p.id} p={p} src={c.source} said open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul></>}
        {running.length > 0 && (settledRows.length
          ? <Fold title={nUnclear ? 'Not yet due, or can’t tell yet' : 'Not yet due'} count={running.length} open={showRunning} toggle={() => setShowRunning(!showRunning)}>
              <ul className="og pgrid fold-body">{running.map(p => <PromiseItem key={p.id} p={p} src={c.source} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>
            </Fold>
          : <><h3 className="sec-head pgrid-head">Promise by promise</h3><ul className="og pgrid">{running.map(p => <PromiseItem key={p.id} p={p} src={c.source} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul></>)}

        {soft.length > 0
          ? <Fold title="Promises without a number or a date" count={soft.length} open={showSoft} toggle={() => setShowSoft(!showSoft)}>
              <ul className="soft-list">{soft.map(p => <SoftRow key={p.id} p={p} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>
            </Fold>
          : softTalk > 0 && <p className="sub soft-note">Plus {softTalk} {softTalk === 1 ? 'statement' : 'statements'} with no number or date. FINN doesn’t check those.</p>}
      </section>

      {/* The page's one blue block: what to ask them next */}
      {next.length > 0 && (
        <section className="ask lead">
          <h2 className="sec-head ask-head">Worth asking on the next results call</h2>
          <ol>{next.map((x, i) => <li key={i}>{x}</li>)}</ol>
          <p className="who-wrote">{whoAsked(c.questions.length, net.length, fromReport.length)}</p>
          <CopyQuestions name={name} qs={next} />
        </section>
      )}

      <NetCompany sym={c.symbol} />

      {ask && <Fold title={`Ask about ${name}`} open={fold === 'ask'} toggle={() => toggle('ask')}><div className="fold-body">{ask}</div></Fold>}

      {newHard.length > 0 && (
        <Fold title="New promises from the latest call" count={newHard.length} open={showOpen} toggle={() => setShowOpen(!showOpen)}>
          <ul className="open-list fold-body">
            {newHard.map((p, i) => (
              <li key={i}>
                <span className="open-t">{cap(plainTerms(rupees(p.target)))}</span> <span className="sub">{rupees(deadline(p))}</span>
                <blockquote>“{p.quote}” <Src href={`${p.url}#page=${p.page}`}>{p.period} call, page {p.page}</Src></blockquote>
              </li>
            ))}
          </ul>
        </Fold>
      )}

      <Fold title="The numbers" open={fold === 'num'} toggle={() => toggle('num')}>
        <div className="fold-body">
          {lastQ && (
            <div className="fig-grid">
              <Fig label={`Revenue, ${lastQ.q}`} value={`₹${cr(lastQ.rev)}`} unit="cr" sub={lastQ.rev_yoy != null ? `${pct(lastQ.rev_yoy)} from a year earlier` : null} />
              <Fig label="Profit after tax" value={`₹${cr(lastQ.pat)}`} unit="cr" sub={yoy('pat')} />
              {!s.financial
                ? <Fig label="Operating margin" value={`${lastQ.opm ?? '–'}`} unit="%" sub={<>Operating profit per ₹100 of sales. {q.slice(-4).map((x: any) => x.opm ?? '–').join(', ')}% over 4 quarters.</>} />
                : <Fig label="Revenue less interest paid" value={`₹${cr(lastQ.op)}`} unit="cr" sub={<>What is left after paying for the money it lends.{yoy('op') && <> {yoy('op')}.</>}</>} />}
            </div>
          )}
          <div className="traj">
            <div>
              <h3>Revenue over {s.years.length} years</h3>
              <Bars values={s.rev} labels={s.years} />
              <p className="sub">{s.rev_cagr5 != null ? `${pct(s.rev_cagr5, false)} a year, on average` : ''}</p>
            </div>
            <div>
              <h3>Profit after tax</h3>
              <Bars values={s.pat} labels={s.years} />
              <p className="sub">{s.pat_cagr5 != null ? `${pct(s.pat_cagr5, false)} a year, on average` : ''}</p>
            </div>
          </div>
          {!s.financial && (
            <div className="fig-grid">
              <Fig label="Cash from operations per ₹100 of profit, 5 years" value={s.cash_conversion5 != null ? `₹${s.cash_conversion5}` : '–'}
                sub={s.cash_conversion5 != null ? (s.cash_conversion5 >= 90 ? 'Profits are turning into cash.' : s.cash_conversion5 >= 60 ? 'Some profit is still tied up in stock and unpaid bills.' : 'Profits are not turning into cash.') : null} />
              <Fig label="Debt to equity" value={s.de != null ? minus(s.de) : '–'} unit={s.de != null ? '×' : undefined} sub={s.debt != null ? `₹${crBig(s.debt)} borrowed, against the owners’ money.` : 'Borrowings against owners’ money.'} />
              <Fig label="Cash conversion cycle" value={s.ccc?.length ? minus(s.ccc[s.ccc.length - 1]) : '–'} unit={s.ccc?.length ? (Math.abs(s.ccc[s.ccc.length - 1]) === 1 ? 'day' : 'days') : undefined}
                sub={`Days from paying suppliers to being paid by customers${s.ccc?.some((d: number) => d < 0) ? '; negative when customers pay first' : ''}.${s.ccc?.length > 1 ? ` ${minus(s.ccc[0])} ${Math.abs(s.ccc[0]) === 1 ? 'day' : 'days'} in ${fyLabel(s.years[0])}.` : ''}`} />
              <Fig label="Return on capital" value={s.roce?.length ? minus(s.roce[s.roce.length - 1]) : '–'} unit={s.roce?.length ? '%' : undefined} sub={`Profit earned on the money put into the business.${s.roce?.length > 1 ? ` ${minus(s.roce[0])}% in ${fyLabel(s.years[0])}.` : ''}`} />
            </div>
          )}
        </div>
      </Fold>

      <AnnualFold a={annual} open={fold === 'ar'} toggle={() => toggle('ar')} />

      {(c.bull.length > 0 || c.bear.length > 0) && (
        <Fold title="For and against" open={fold === 'case'} toggle={() => toggle('case')}>
          <div className="case fold-body">
            <div><h3 className="lbl lbl-quiet">For</h3><ul>{c.bull.map((x, i) => <li key={i}>{plainTerms(rupees(x))}</li>)}</ul></div>
            <div><h3 className="lbl lbl-quiet">Against</h3><ul>{c.bear.map((x, i) => <li key={i}>{plainTerms(rupees(x))}</li>)}</ul></div>
          </div>
          <p className="who-wrote">Drafted by AI from the results calls and the numbers. Unlike the verdicts above, nothing here is checked against a page.</p>
        </Fold>
      )}

      <Fold title="Sources for this page" open={fold === 'src'} toggle={() => toggle('src')}>
        <div className="sources fold-body">
          <ul>
            {c.calls.map(x => {
              // What this call adds to the page: promises with a number and a date first made on it (repeats sit with the first call).
              // The tally note says what counts and the line below says the quotes were checked, so each row is just the count
              const n = [...c.ledger, ...c.open].filter(p => p.hard && p.period === x.period).length
              return (
                <li key={x.period}><Src href={x.url}>{x.period} call</Src>
                  <span className="sub">{x.error ? 'Could not be read' : !n ? `${x.pages} pages, no promise to check` : `${x.pages} pages, ${n} ${n === 1 ? 'promise' : 'promises'}`}</span></li>
              )
            })}
            <li><Src href={c.source}>The tables of reported numbers</Src><span className="sub">screener.in, {c.basis}, compiled from filed results</span></li>
          </ul>
          {pages > 0 && <p className="sub">Read {pages} pages. Every quote above was matched to its page in the PDF{dropped ? `; ${dropped} that didn’t match ${dropped === 1 ? 'was' : 'were'} thrown out` : ''}. Nothing here comes from news, brokers or the model’s own memory.</p>}
          {c.usage?.calls > 0 && <p className="sub">The AI model was called {c.usage.calls} times ({Math.round((c.usage.tokens_in + c.usage.tokens_out) / 1000)}k tokens), about ${c.usage.usd_if_billed.toFixed(2)} if billed. {grader(c.usage.by_model)}</p>}
        </div>
      </Fold>
    </main>
  )
}

const grader = (by: Record<string, number> = {}) =>
  !Object.keys(by).length ? '' : by['gemini-3.5-flash'] ? 'Checked by the main AI model, gemini-3.5-flash.'
    : 'Checked by a smaller AI model, gemini-3.5-flash-lite: the main one had reached its free daily limit.'
// 'X remains ongoing.' / 'X is pending.' only restates the promise; the dash mark already says not due yet

function Fig({ label, value, unit, sub }: { label: string; value: string; unit?: string; sub: any }) {
  return <div className="fig og-item"><Outcome size={value.length > 9 ? 'xxs' : value.length > 5 ? 'xs' : 's'} value={value} unit={unit} /><span className="og-d1">{label}</span>{sub && <span className="og-d2">{sub}</span>}</div>
}

// The figure they promised, pulled from the promise itself: '15%', '₹5,600–5,800 cr', '0.8–0.9×'.
// A number glued to letters ('FY26', 'Q3', 'Lakshya 31' is fine) is a date or a name, not the figure; so is a bare year.
const FIG = /(₹\s?|\$)?(\d[\d,]*(?:\.\d+)?)(?:\u2060?[–-]\u2060?(\d[\d,]*(?:\.\d+)?))?\s?(%|x\b|×|bps|lakh\scrore|crore|cr\b|GW|MW|MVA|days|months|years|million tons?|million|billion|trillion|lakh|KTPA|MTPA)?s?(?![a-z])/gi
function promised(t: string): [string, string] | null {
  // '12 to 15 percent', '23% to 24%' -> '12–15%', '23–24%'
  const txt = rupees(t).replace(/\bpercent\b/gi, '%').replace(/\s+%/g, '%')
    .replace(/(\d+(?:\.\d+)?)\s(billion|million|crore) to (\d+(?:\.\d+)?)\s\2/g, '$1–$3 $2')
    .replace(/(\d+(?:\.\d+)?)%?[\s\u2060]*(?:to|[-–])[\s\u2060]*(\d+(?:\.\d+)?)(?=\s?%)/g, '$1–$2').replace(/(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)/g, '$1–$2')
  for (const m of txt.matchAll(FIG)) {
    if (/[A-Za-z]$/.test(txt.slice(0, m.index))) continue
    // A bare number ('plant 2', 'August 25', 'mid-20s') says nothing on its own; only a unit or a currency makes it the figure
    if (!m[1] && !m[4]) continue
    const u = m[4] || '', unit = /^x$/i.test(u) ? '×' : /^crore$/i.test(u) ? 'cr' : /^lakh\scrore$/i.test(u) ? 'lakh cr' : /^(mva|gw|mw|ktpa|mtpa|bps)$/i.test(u) ? (u.toLowerCase() === 'bps' ? 'bps' : u.toUpperCase()) : u.toLowerCase()
    return [`${m[1] ? m[1].trim() : ''}${m[2]}${m[3] ? `–${m[3]}` : ''}`, unit === '%' || unit === '×' ? unit : unit ? ` ${unit}` : '']
  }
  // A count of things: 'Add 6 new branches', '50 new branches', '100–200 trucks'
  const n = txt.match(/(?<![\w.])(\d[\d,]*(?:–\d[\d,]*)?)\s+(?:new\s+|more\s+|additional\s+)?(branches|clients|stores|trucks|rooftops|ships|rakes|products|plants|tires|outlets|customers)\b/i)
  if (n) return [n[1], ` ${n[2].toLowerCase()}`]
  return null
}
// No figure in the promise: the year it's due, as they named it ('FY26'), else when it was said
const dueFig = (p: Promise_) => `${p.target} ${deadline(p)}`.match(/\b(Q\d\s)?FY\d\d\b|\b20\d\d\b/)?.[0]

// What was delivered, for a settled promise with one figure: the one other figure of the same unit in the verdict
// ('grew 11.8% ... against the 15% growth target' -> 11.8%). Left out when there are two, or when the figure follows
// a guide's words ('expected raw material costs around 25%'), so the big figure is never a guess
const PCT = /(\d[\d,]*(?:\.\d+)?)(?:\s?(?:[–-]|to)\s?(\d[\d,]*(?:\.\d+)?))?\s?(%|×)/g
function delivered(p: Promise_): [string, string] | null {
  if (!['missed', 'kept', 'partly', 'quiet'].includes(p.status)) return null
  const t = [...p.target.matchAll(PCT)]
  if (t.length !== 1) return null
  const key = (m: RegExpMatchArray) => `${m[1]}${m[2] ? '–' + m[2] : ''}`
  const c = [...(p.verdict || '').matchAll(PCT)].filter(m => m[3] === t[0][3] && key(m) !== key(t[0]))
  const vals = [...new Set(c.map(key))]
  if (vals.length !== 1 || /expect|guid|target|promis|plan/i.test(p.verdict.slice(Math.max(0, c[0].index! - 40), c[0].index))) return null
  return [vals[0], t[0][3]]
}

// One promise as an outcome, as v4 set it: the figure, what they said, the verdict word. Tap for the quote and what the filings showed
// said: a settled promise carries what the filings showed under its verdict word, so promised and delivered read together
function PromiseItem({ p, src, open, toggle, said }: { p: Promise_; src?: string; open: boolean; toggle: () => void; said?: boolean }) {
  const got = said ? delivered(p) : null
  const fig = got ?? promised(p.target), due = fig ? undefined : dueFig(p)
  const len = (fig?.[0] || '').replace(/\u2060/g, '').length + (fig?.[1] || '').trim().length
  const size = !fig ? 'xs' : len <= 5 ? 's' : len <= 6 ? 'm' : len <= 9 ? 'xs' : 'xxs'
  return (
    <li className={`og-item p-item st-${p.status}${open ? ' open' : ''}`} data-pid={p.id}>
      <button className="og-btn" aria-expanded={open} onClick={toggle}>
        {/* Figures sit in one 48 px band, so the sentences under them start level across the row */}
        <span className="p-fig">{fig ? <><Outcome size={size} value={fig[0]} unit={fig[1]} />{got && <span className="p-against">against {promised(p.target)?.join('')}</span>}</> : due ? (/^FY\d\d$/.test(due) ? <Outcome size="s" pre="FY" value={due.slice(2)} /> : <Outcome size={due.length > 5 ? 'xs' : 's'} value={due} />) : null}</span>
        <span className="og-d1">{promiseLine(p)}.</span>
        <span className="og-d2">Said {p.period.replace(/ 20/, ' ’')}</span>
      </button>
      <StatusLabel status={p.status} />
      {said && !open && verdictText(p) && <p className="p-ev">{verdictText(p).replace(/\.?$/, '.')}</p>}
      <Accordion open={open}><div className="p-detail"><BeforeAfter p={p} inRow src={src} /></div></Accordion>
      {!open && <button className="og-link" onClick={toggle}>See their exact words</button>}
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
  const copy = () => navigator.clipboard.writeText(`${name}: worth asking on the next results call\n${qs.map((q, i) => `${i + 1}. ${q}`).join('\n')}`)
    .then(() => { setDone(true); setTimeout(() => setDone(false), 2000) }).catch(() => { /* clipboard refused: nothing to undo */ })
  return <button className="text-btn copy" onClick={copy} aria-live="polite">{done ? 'Copied' : 'Copy the questions'}</button>
}
