import { useEffect, useState } from 'react'
import { plainTerms } from './lib'
import { Fold, Src } from './ui'

// The FY26 annual report's notes, as FINN's rules read them (finn/annual.py, served from /data/annual/<SYM>.json).
// Every sentence here was made by code from fields read off a page, and every quote is checked against that page
// by evals/run_annual.py. A filing is untrusted text: it is rendered as text, never as markup or instructions.
type Ref = { label: string; page: number; quote?: string }
type Calls = { text: string; quote?: string; url?: string; page?: number; negative: boolean }
type Item = { text: string; quote: string; src: Ref; calls?: Calls }
type Block = { title: string; text?: string; items?: Item[]; src?: Ref[]; trail?: { text: string; src: Ref[] }; going_concern?: Ref[]; printed?: string; quote?: string }
export type Annual = { symbol: string; read: boolean; url: string; filed: string; verdict: string; why?: string; blocks: Block[]; questions: string[]; foot: string }
type State = Annual | 'none' | 'error' | null

let builtP: Promise<Set<string>> | null = null
const built = () => (builtP ??= fetch('/data/companies.json').then(r => r.json())
  .then(d => new Set<string>(Array.isArray(d) ? d : Object.keys(d))).catch(() => { builtP = null; return new Set<string>() }))

const seen = new Map<string, Annual | 'none'>()

// The company's annual-report file; 'none' for a company outside the 22 built in, 'error' if it couldn't be fetched
export function useAnnual(sym: string): State {
  const [a, setA] = useState<State>(seen.get(sym) ?? null)
  useEffect(() => {
    if (seen.has(sym)) { setA(seen.get(sym)!); return }
    let live = true
    built().then(async b => {
      if (!b.size) return 'error' as const
      if (!b.has(sym)) return 'none' as const
      const r = await fetch(`/data/annual/${sym}.json`)
      return r.ok ? (await r.json() as Annual) : 'error' as const
    }).catch(() => 'error' as const).then(v => {
      if (v !== 'error') seen.set(sym, v)
      if (live) setA(v)
    })
    return () => { live = false }
  }, [sym])
  return a
}

export const annualQuestions = (a: State) => (a && typeof a === 'object' && a.read ? a.questions : [])

// One tap away: the paragraph the sentence above was read from, with its page
function Reveal({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return <>
    <button className="text-btn ar-more" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Hide' : label}</button>
    {open && <div className="ar-reveal">{children}</div>}
  </>
}

function ItemRow({ it, href }: { it: Item; href: (p: number) => string }) {
  const c = it.calls
  return (
    <li>
      <p className="ar-t">{it.text}</p>
      {c && <p className="ar-calls">{c.text}</p>}
      <Reveal label="Read the paragraph">
        <blockquote>“{it.quote}”</blockquote>
        <p className="sub"><Src href={href(it.src.page)}>{it.src.label}</Src></p>
        {c?.quote && <>
          <blockquote>“{c.quote}”</blockquote>
          <p className="sub"><Src href={c.url ? `${c.url}#page=${c.page}` : undefined}>{c.text.match(/latest is ([^,]+)/)?.[1] ?? 'The call'} call, page {c.page}</Src></p>
        </>}
      </Reveal>
    </li>
  )
}

// The auditor's two-word verdict, said first as a person would: 'not modified' means no reservations
const CLEAN = 'The auditor signed off with no reservations'
const auditWords = (t: string) => t.replace(/^Opinion not modified(?: \(a clean opinion\))?/, `${CLEAN} (opinion “not modified”)`)
// A note's name, plain words first: only the heading changes, never the sentence read off the page
const TITLE: Record<string, string> = { 'Contingent liabilities': 'Money it may have to pay later (contingent liabilities)' }

function BlockView({ b, href }: { b: Block; href: (p: number) => string }) {
  return (
    <section className="ar-block">
      <h3 className="lbl lbl-quiet">{TITLE[b.title] || plainTerms(b.title)}</h3>
      {b.text && <p className="ar-t">{b.title === 'The auditor' ? auditWords(b.text) : b.text}</p>}
      {!!b.items?.length && <ul className="ar-items">{b.items.map((it, i) => <ItemRow key={i} it={it} href={href} />)}</ul>}
      {b.going_concern?.map((g, i) => <p key={i} className="ar-t">A material uncertainty on going concern: <Src href={href(g.page)}>{g.label}</Src></p>)}
      {b.quote && <blockquote>“{b.quote}”</blockquote>}
      {b.printed && <p className="sub">{b.printed}</p>}
      {!!b.src?.length && <p className="ar-src">{b.src.map((s, i) => <Src key={i} href={href(s.page)}>{s.label}</Src>)}</p>}
      {b.trail && <div className="ar-trail">
        <p className="sub">{b.trail.text}</p>
        <p className="ar-src">{b.trail.src.map((s, i) => <Src key={i} href={href(s.page)}>{s.label}</Src>)}</p>
        <Reveal label="Read the clause">{b.trail.src.map((s, i) => <div key={i}><blockquote>“{s.quote}{/[.:;]$/.test(s.quote ?? '') ? '' : ' …'}”</blockquote><p className="sub">{s.label}</p></div>)}</Reveal>
      </div>}
    </section>
  )
}

export function AnnualFold({ a, open, toggle }: { a: State; open: boolean; toggle: () => void }) {
  if (a === null || a === 'error') return null   // loading, or offline with no saved copy: no row that says nothing
  if (a === 'none') return (
    <Fold title="The annual report" line="Only for the 22 companies FINN has already read" open={open} toggle={toggle}>
      <p className="sub fold-body">FINN reads annual reports ahead of time, by its own rules, for the 22 companies it has already read. A company looked up just now gets its results calls read; its annual report is not fetched.</p>
    </Fold>
  )
  const href = (p: number) => `${a.url}#page=${p}`
  if (!a.read) return (
    <Fold title="The annual report" line="Not read" open={open} toggle={toggle}>
      <div className="fold-body"><p className="ar-t">{a.why}</p>{a.url && <p className="ar-src"><Src href={a.url}>The filing{a.filed ? `, ${a.filed}` : ''}</Src></p>}</div>
    </Fold>
  )
  return (
    <Fold title="The annual report" line={a.verdict === 'Opinion not modified' ? `${CLEAN}.` : a.verdict} open={open} toggle={toggle}>
      <div className="ar fold-body">
        {a.blocks.map(b => <BlockView key={b.title} b={b} href={href} />)}
        <p className="who-wrote">{a.foot}</p>
      </div>
    </Fold>
  )
}
