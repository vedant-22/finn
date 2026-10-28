import { useState } from 'react'
import { cr, deadline, minus, pct, rupees, shortName, tone, type Company, type Promise_, type Status } from './lib'
import { Bars, fyLabel, Mark, Src, STATUS_WORD } from './ui'

const SHOW: Status[] = ['missed', 'quiet', 'partly', 'kept', 'pending', 'unclear']

export function CompanyView({ c, sector, title, back }: { c: Company; sector?: string; title?: string; back: () => void }) {
  const [openId, setOpenId] = useState<number | null>(null)
  const [showSoft, setShowSoft] = useState(false)
  const [showOpen, setShowOpen] = useState(false)
  const s = c.snapshot
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
    return <span className={tone(v)}>{pct(v)} on a year ago</span>
  }

  return (
    <main className="screen company">
      <header className="top">
        <button className="text-btn back" onClick={back}>Back</button>
        <span className="sub">{c.symbol}{c.live ? ', read just now' : ''}</span>
      </header>
      <h1 className="co-name">{title || shortName(c.name)}</h1>
      <p className="co-meta">
        {sector && <>{sector}. </>}
        {s.price != null && <>Share price ₹{s.price.toLocaleString('en-IN')}. </>}
        {s.mcap != null && <>Worth ₹{cr(s.mcap)} cr{s.pe ? `, ${s.pe}× earnings` : ''}.</>}
      </p>

      <section className="word">
        <div className="word-head">
          <h2>Their word</h2>
          {hard.length > 0
            ? <ul className="tally" aria-label="Promise record">
              {SHOW.map(st => {
                const n = hard.filter(p => p.status === st).length
                return n ? <li key={st}><Mark status={st} size={18} /><b className="num">{n}</b> <span>{STATUS_WORD[st].toLowerCase()}</span></li> : null
              })}
            </ul>
            : <p className="word-score sub">No promise in these calls had both a number and a date.</p>}
          <p className="sub tally-note">Promises with a number and a date, from the {c.calls.filter(x => !x.error).length - 1} calls before the latest one.</p>
        </div>
        {c.read && settled >= 3 && <p className="read">{rupees(c.read)}</p>}

        <ul className="ledger">
          {hard.map((p, i) => <LedgerRow key={p.id} p={p} i={i} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}
        </ul>

        {softTalk > 0 && (
          <button className="soft" aria-expanded={showSoft} onClick={() => setShowSoft(!showSoft)}>
            Plus {softTalk} {softTalk === 1 ? 'statement' : 'statements'} with no number or date. Not graded.
          </button>
        )}
        {showSoft && <ul className="ledger soft-list">{soft.map((p, i) => <LedgerRow key={p.id} p={p} i={i} open={openId === p.id} toggle={() => setOpenId(openId === p.id ? null : p.id)} />)}</ul>}
      </section>

      {c.questions.length > 0 && (
        <section className="ask">
          <h2>Ask on the next call</h2>
          <ol>{c.questions.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ol>
        </section>
      )}

      {c.open.some(p => p.hard) && (
        <section className="open-book">
          <button className="fold-head" aria-expanded={showOpen} onClick={() => setShowOpen(!showOpen)}>
            <span>{c.open.filter(p => p.hard).length} new {c.open.filter(p => p.hard).length === 1 ? 'promise' : 'promises'} on the latest call</span><span className="chev" aria-hidden>{showOpen ? '–' : '+'}</span>
          </button>
          {showOpen && (
            <ul className="ledger">
              {c.open.filter(p => p.hard).map((p, i) => (
                <li key={i} className="ledger-row static">
                  <Mark status="pending" />
                  <div><b>{cap(rupees(p.target))}</b> <span className="sub">{deadline(p)}</span>
                    <blockquote>“{p.quote}” <Src href={`${p.url}#page=${p.page}`}>{p.period}, p{p.page}</Src></blockquote></div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="figures">
        <h2>The numbers</h2>
        {lastQ && (
          <div className="fig-grid">
            <Fig label={`Revenue, ${lastQ.q}`} value={`₹${cr(lastQ.rev)} cr`} sub={lastQ.rev_yoy != null ? <span className={tone(lastQ.rev_yoy)}>{pct(lastQ.rev_yoy)} on a year ago</span> : null} />
            {!s.financial
              ? <Fig label="Operating margin" value={`${lastQ.opm ?? '–'}%`} sub={<>{q.slice(-4).map((x: any) => x.opm ?? '–').join(', ')} over 4 quarters</>} />
              : <Fig label="Net interest income" value={`₹${cr(lastQ.op)} cr`} sub={yoy('op')} />}
            <Fig label="Profit after tax" value={`₹${cr(lastQ.pat)} cr`} sub={yoy('pat')} />
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
            <Fig label="Debt to equity" value={s.de != null ? minus(s.de) : '–'} sub={s.debt != null ? `₹${cr(s.debt)} cr borrowed` : null} />
            <Fig label="Cash conversion cycle" value={s.ccc?.length ? `${minus(s.ccc[s.ccc.length - 1])} days` : '–'}
              sub={s.ccc?.length > 1 ? `${minus(s.ccc[0])} days in ${fyLabel(s.years[0])}` : null} />
            <Fig label="Return on capital" value={s.roce?.length ? `${minus(s.roce[s.roce.length - 1])}%` : '–'} sub={s.roce?.length > 1 ? `${minus(s.roce[0])}% in ${fyLabel(s.years[0])}` : null} />
          </div>
        )}
      </section>

      {(c.bull.length > 0 || c.bear.length > 0) && (
        <section className="case">
          <div><h2>For</h2><ul>{c.bull.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ul></div>
          <div><h2>Against</h2><ul>{c.bear.map((x, i) => <li key={i}>{rupees(x)}</li>)}</ul></div>
        </section>
      )}

      <footer className="sources">
        <h2>Read for this page</h2>
        <ul>
          {c.calls.map(x => (
            <li key={x.period}><Src href={x.url}>{x.period} call</Src>
              <span className="sub"> {x.error ? 'could not be read' : `${x.pages} pages, ${x.found} ${x.found === 1 ? 'promise' : 'promises'} found, quotes checked`}</span></li>
          ))}
          <li><Src href={c.source}>Financial tables</Src><span className="sub"> screener.in, {c.basis}, compiled from filed results</span></li>
        </ul>
        <p className="sub">Read {pages} pages. Every quote above was matched to its page in the PDF{dropped ? `; ${dropped} that didn't match ${dropped === 1 ? 'was' : 'were'} thrown out` : ''}. Nothing here comes from news, brokers or the model's own memory.</p>
        {c.usage && <p className="sub">{c.usage.calls} model calls, {Math.round((c.usage.tokens_in + c.usage.tokens_out) / 1000)}k tokens, about ${c.usage.usd_if_billed.toFixed(2)} if billed. {grader(c.usage.by_model)}</p>}
      </footer>
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

function Fig({ label, value, sub }: { label: string; value: string; sub: any }) {
  return <div className="fig"><div className="fig-label">{label}</div><div className="fig-value num">{value}</div>{sub && <div className="fig-sub">{sub}</div>}</div>
}

function LedgerRow({ p, i, open, toggle }: { p: Promise_; i: number; open: boolean; toggle: () => void }) {
  return (
    <li className={`ledger-row st-${p.status} ${open ? 'open' : ''}`}>
      <button className="ledger-btn" aria-expanded={open} onClick={toggle}>
        <Mark status={p.status} delay={120 + i * 70} />
        <div className="ledger-main">
          <div className="ledger-target"><b>{cap(rupees(p.target))}</b> <span className="sub">{deadline(p)}</span></div>
          {verdictText(p) && <div className="ledger-verdict">{verdictText(p)}</div>}
        </div>
        <span className="ledger-when sub">{p.period.replace(/ 20/, ' ’')}</span>
      </button>
      {open && (
        <div className="ledger-detail">
          <div className="said">
            <h4>Said</h4>
            <blockquote>“{p.quote}”</blockquote>
            <p className="sub">{p.speaker}, <Src href={`${p.url}#page=${p.page}`}>{p.period} call, page {p.page}</Src>
              {p.restated?.length ? <>. Said again: {p.restated.map((r, k) => <span key={k}>{k ? ', ' : ' '}<Src href={`${r.url}#page=${r.page}`}>{r.period}</Src></span>)}</> : null}</p>
          </div>
          {p.evidence && (
            <div className="did">
              <h4>{p.evidence_kind === 'quote' ? 'Latest call' : 'Reported'}</h4>
              {p.evidence_kind === 'quote'
                ? <><blockquote>“{p.evidence}”</blockquote><p className="sub"><Src href={p.evidence_url ? `${p.evidence_url}#page=${p.evidence_page}` : undefined}>page {p.evidence_page}</Src></p></>
                : <p className="num-ev">{rupees(p.evidence.replace(/(\d)\.0\b/g, '$1'))}</p>}
            </div>
          )}
        </div>
      )}
    </li>
  )
}
