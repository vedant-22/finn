// The brief: the few things to read in a window, and what the investor has done with each.
// Pure functions over the snapshot, so they can be tested without a browser.
import { triage, type Lines, type Move, type Push, type Story } from './lib.ts'

export interface Item {
  key: string; symbol: string; at: string
  kind: 'results' | 'people' | 'move' | 'filing'
  story?: Story; move?: Move
  // A management change filed the same day as the company's results travels with them: one story, not two rows
  with?: Story
  crossed: { line: 'price' | 'volume' | 'filing'; category?: string }[]
}

// However busy the window, a brief stays short: past this many, items wait as one-liners
export const MAX_ITEMS = 6

export function buildBrief(push: Push, lines: Lines) {
  const t = triage(push, lines)
  const items: Item[] = t.needs.map(s => ({
    key: s.key, symbol: s.symbol, at: s.at, story: s,
    kind: s.lead.results ? 'results' : s.lead.people?.length ? 'people' : 'filing',
    crossed: [{ line: 'filing', category: s.category }],
  }))
  for (const m of t.moves) {
    const crossed = m.why.map(w => ({ line: w as 'price' | 'volume' }))
    // A move on results day belongs to the results: one item, not two
    const host = items.find(i => i.kind === 'results' && i.symbol === m.symbol && !i.move && m.explainedBy?.category === 'results')
    if (host) { host.move = m; host.crossed.push(...crossed); continue }
    items.push({ key: `move|${m.symbol}|${m.d}`, symbol: m.symbol, at: `${m.d}T15:30:00`, kind: 'move', move: m, crossed })
  }
  // The results an item stands on: its own filing, or the results that explain a move
  const resultsAt = (i: Item) => i.kind === 'results' ? i.at : i.kind === 'move' && i.move?.explainedBy?.category === 'results' ? i.move.explainedBy.at : null
  const near = (a: string | null, b: string) => a != null && Math.abs(Date.parse(a) - Date.parse(b)) < 864e5
  for (const p of items.filter(i => i.kind === 'people')) {
    const host = items.find(i => i.symbol === p.symbol && !i.with && near(resultsAt(i), p.at))
    if (!host) continue
    host.with = p.story; host.crossed.push(...p.crossed)
    items.splice(items.indexOf(p), 1)
  }
  // A results-day move whose results came with a management change says so, even when that filing is outside the window
  for (const i of items.filter(i => i.kind === 'move' && !i.with)) {
    const f = push.filings.filter(x => x.symbol === i.symbol && x.people?.length && near(resultsAt(i), x.at))
      .sort((a, b) => +!!b.people!.some(p => p.seniority === 'top') - +!!a.people!.some(p => p.seniority === 'top') || b.at.localeCompare(a.at))[0]
    if (f) i.with = { key: f.id, symbol: f.symbol, category: f.category, tier: f.tier, at: f.at, lead: f, filings: [f] }
  }
  // No one kind takes more than three places, so a week of results can't hide a CFO leaving
  const kind = (i: Item) => i.story?.category ?? 'move'
  const chosen = new Set<Item>(), per = new Map<string, number>()
  for (const i of items) if (chosen.size < MAX_ITEMS && (per.get(kind(i)) ?? 0) < 3) { chosen.add(i); per.set(kind(i), (per.get(kind(i)) ?? 0) + 1) }
  for (const i of items) if (chosen.size < MAX_ITEMS) chosen.add(i)
  return {
    // Chosen by weight, then read newest first, so the list and the reader run in the order things happened
    items: items.filter(i => chosen.has(i)).sort((a, b) => b.at.localeCompare(a.at)),
    spill: items.filter(i => !chosen.has(i)),
    notes: t.notes, folded: t.folded, filings: t.filings,
    routine: t.folded.reduce((n, s) => n + s.filings.length, 0),
  }
}
export type Brief = ReturnType<typeof buildBrief>

// ---------- what the investor has done ----------
export interface Done { cleared: string[]; kept: string[]; notes: string[] }
const KEY = 'finn.brief'
export const NO_DONE: Done = { cleared: [], kept: [], notes: [] }
export function loadDone(): Done {
  try { return { ...NO_DONE, ...JSON.parse(localStorage.getItem(KEY) || '{}') } } catch { return NO_DONE }
}
export const saveDone = (d: Done) => localStorage.setItem(KEY, JSON.stringify(d))

// Clearing and keeping both take an item off the brief; kept ones wait in a list
export function act(d: Done, key: string, how: 'clear' | 'keep' | 'undo'): Done {
  const cleared = d.cleared.filter(k => k !== key), kept = d.kept.filter(k => k !== key)
  if (how === 'clear') cleared.push(key)
  if (how === 'keep') kept.push(key)
  return { ...d, cleared, kept }
}
export const isDone = (d: Done, key: string) => d.cleared.includes(key) || d.kept.includes(key)

// The one-liners are read as a page: clearing it clears every note on it
export const notesKey = (notes: Story[], spill: Item[]) => [...spill.map(i => i.key), ...notes.map(s => s.key)].sort().join(',')

// What's left to read, in order: items not yet cleared or kept, then the one-liners page if it hasn't been read
export function remaining(b: Brief, d: Done) {
  const items = b.items.filter(i => !isDone(d, i.key))
  const nk = notesKey(b.notes, b.spill)
  const notesLeft = (b.notes.length + b.spill.length) > 0 && !d.notes.includes(nk)
  return { items, notesLeft, total: items.length + (notesLeft ? 1 : 0) }
}

// ---------- since you last looked ----------
// The last time the brief was opened, kept for one marker: what's arrived since
const SEEN = 'finn.seen'
export function lastSeen(): string | null { return localStorage.getItem(SEEN) }
export const markSeen = (iso: string) => localStorage.setItem(SEEN, iso)

// A question for the company's next call, from what just happened: a CEO, CFO or MD leaving first, then a margin
// that fell a point or more on a year ago, then profit down a fifth or more. Null when the news raises none.
const ROLE = (r: string) => r.replace(/\bChief Financial Officer\b/i, 'CFO').replace(/\bChief Executive Officer\b/i, 'CEO').replace(/\bManaging Director\b/i, 'MD')
export function newsQuestion(i: Item, push: Push): string | null {
  const gone = [i.with?.lead, i.story?.lead].flatMap(f => f?.people || []).find(p => p.seniority === 'top' && ['resigned', 'ceased', 'retired'].includes(p.action))
  if (gone) return `Why did the ${ROLE(gone.role)}, ${gone.name.replace(/^(Mr|Ms|Mrs|Dr)\.?\s+/, '')}, leave, and who covers the role until a successor joins?`
  const f = i.story?.lead?.results ? i.story.lead : i.move?.explainedBy?.category === 'results'
    ? push.filings.filter(x => x.symbol === i.symbol && x.results && x.at.slice(0, 10) <= i.move!.d).sort((a, b) => b.at.localeCompare(a.at))[0] : undefined
  const r = f?.results
  if (!r) return null
  const rev = r.lines.find(l => l.key === 'revenue'), pat = r.lines.find(l => l.key === 'pat')
  const dm = r.ebitda_margin != null && r.yago_margin != null ? r.ebitda_margin - r.yago_margin : 0
  // The margin question names both growths, so the gap is the question: L&T's revenue up 15.8%, EBITDA up 0.6%
  const eb = r.lines.find(l => l.key === 'ebitda')
  const grew = (v: number) => `${v >= 0 ? 'grew' : 'fell'} ${Math.abs(v).toFixed(1)}%`
  if (dm <= -1 && rev?.yoy != null) return `Revenue ${grew(rev.yoy)} on a year ago${eb?.yoy != null ? ` and EBITDA ${eb.yoy >= 0 ? 'only ' : ''}${grew(eb.yoy).replace(/^grew /, '')}` : ''}: the margin fell ${Math.abs(dm).toFixed(1)} pp. Which costs rose faster, and do they ease from here?`
  if (pat?.yoy != null && pat.yoy <= -20) return `Profit fell ${Math.abs(pat.yoy).toFixed(0)}% on a year ago. How much of that is one-off?`
  return null
}
