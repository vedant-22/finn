// Promised against delivered: management's words in the book serif on the warm panel, then what the filings showed.
// The one form a promise takes everywhere: in the brief, in an answer, on the company page.
import { markQuote, numbersOnly, plainTerms, tidyEvidence, type Promise_ } from './lib'
import { clip, promiseLine, verdictText } from './Trail'
import { Src, StatusLabel } from './ui'

export const said = (p: Promise_) => p.period.replace(/ 20(\d\d)$/, ' ’$1')

// inRow: opened under its own row, which already names the promise
// lead: the verdict before the quote, where the reader has ten seconds (a results item); else the quote first
// bare: the quote alone, where the verdict is already said above it (a results item)
// src: the financial table a 'Reported' line comes from
export function BeforeAfter({ p, compact, inRow, lead, bare, src }: { p: Promise_; compact?: boolean; inRow?: boolean; lead?: boolean; bare?: boolean; src?: string }) {
  const quote = compact ? clip(markQuote(p.quote, p.target, p.by_when).parts).map(x => x.t).join('') : p.quote
  const v = verdictText(p)
  return (
    <div className={`ba${lead ? ' ba-lead' : ''}`}>
      <figure className="ba-said">
        <blockquote className="quote">“{quote}”</blockquote>
        <figcaption className="small">{compact ? 'Said on the' : `${p.speaker}, on the`} <Src href={`${p.url}#page=${p.page}`}>{said(p)} call, page {p.page}</Src></figcaption>
      </figure>
      {!bare && <div className="ba-then">
        {!inRow && <p className="ba-promise">{promiseLine(p)}</p>}
        {/* Opened under its row, the status word is already on the row: say only what happened */}
        {inRow ? v && <p className="ba-verdict">{v.replace(/\.?$/, '.')}</p> : <p className="ba-verdict"><StatusLabel status={p.status} />{v && <span> {v}</span>}</p>}
        {!compact && p.evidence && (p.evidence_kind === 'quote'
          ? <p className="small ba-ev">On the latest call: “{p.evidence}” <Src href={p.evidence_url ? `${p.evidence_url}#page=${p.evidence_page}` : undefined}>page {p.evidence_page}</Src></p>
          : (ev => ev && <p className="small ba-ev">From its reported numbers: {plainTerms(ev)} {src && <Src href={src}>The tables</Src>}</p>)(numbersOnly(tidyEvidence(p.evidence), v)))}
      </div>}
    </div>
  )
}
