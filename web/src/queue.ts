// The brief: the few things to read in a window, and what the investor has done with each.
// Pure functions over the snapshot, so they can be tested without a browser.
import { triage, type Lines, type Move, type Push, type Story } from './lib.ts'
import { load, loadJSON, save, saveJSON } from './storage.ts'

// What the network noticed (web/public/data/network.json). A join across filings that Push reads one by one, with one
// person to ask, carries a card: the companies, one sentence, and for one call each company's question
export interface NetNotice {
  kind: string; line: string; why: string; at: string; symbol: string; q?: string; key?: string
  contact?: { id: string; name: string; last: string } | null
  card?: { symbols: string[]; line: string; rows?: { symbol: string; line: string; ask: string }[]; sheet?: string }
}

export interface Item {
  key: string; symbol: string; at: string
  kind: 'results' | 'people' | 'move' | 'filing' | 'network'
  story?: Story; move?: Move; notice?: NetNotice
  // A management change filed the same day as the company's results travels with them: one story, not two rows
  with?: Story
  crossed: { line: 'price' | 'volume' | 'filing'; category?: string }[]
}

// However busy the window, a brief stays short: past this many, items wait as one-liners
export const MAX_ITEMS = 6

// The first day of a window, as the network's notices are dated
export const windowFrom = (asof: string, hours: number) => new Date(new Date(asof).getTime() - hours * 3600e3).toISOString().slice(0, 10)

// At most one notice raises a card in a window, ranked as the fold ranks: what filings say together first, then one call.
// A pattern at a company that already has a card stays with that card, whose full view carries it
export function raisedNotice(notices: NetNotice[], asof: string, hours: number, skip: string[]): NetNotice | null {
  const from = windowFrom(asof, hours), rank = (n: NetNotice) => n.kind === 'seats' ? 0 : 1
  return notices.map((n, k) => ({ n, k })).filter(({ n }) => n.card && n.at >= from && !(n.kind === 'seats' && skip.includes(n.symbol)))
    .sort((a, b) => rank(a.n) - rank(b.n) || a.k - b.k)[0]?.n ?? null
}
// Its key is what it is, not its words, so the deep link to it survives a rebuild that rewords it
export const netKey = (n: NetNotice) => `net|${n.kind}|${[...(n.card?.symbols || [])].sort().join(',')}|${n.at}|${n.contact?.id ?? ''}`

// The fold, "From your network": only what is dated inside the window, never what a card above already carries
// (the raised notice, or a company's own pattern, path or reason to call). Patterns first, one call, someone you know, the rest
export function foldNotices(notices: NetNotice[], asof: string, hours: number, skip: string[], raised?: NetNotice | null) {
  const from = windowFrom(asof, hours)
  const rank = (n: NetNotice) => ['seats', 'exits'].includes(n.kind) ? 0 : n.kind === 'onecall' ? 1 : n.kind === 'contact' ? 2 : 3
  return notices.filter(n => n !== raised && !!n.at && n.at >= from && !(skip.includes(n.symbol) && ['event', 'exits', 'seats', 'path', 'warm'].includes(n.kind)))
    .map((n, k) => ({ n, k })).sort((a, b) => rank(a.n) - rank(b.n) || a.k - b.k).map(x => x.n).slice(0, 6)
}

export function buildBrief(push: Push, lines: Lines, notices?: NetNotice[]) {
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
  // Chosen by weight, then read newest first, so the list and the reader run in the order things happened
  const shown = items.filter(i => chosen.has(i)).sort((a, b) => b.at.localeCompare(a.at))
  // One card from the network, last, apart from what needs you: it crossed none of the investor's lines, so it is not
  // in the count and raises no notification
  const n = notices ? raisedNotice(notices, push.asof, lines.hours, shown.map(i => i.symbol)) : null
  const asItem = (x: NetNotice): Item => ({ key: netKey(x), symbol: x.card!.symbols[0], at: `${x.at}T12:00:00`, kind: 'network', notice: x, crossed: [] })
  const net: Item | null = n ? asItem(n) : null
  // A notice with a card that this window leaves in the fold opens the same full view from there
  const from = windowFrom(push.asof, lines.hours)
  const netFold = (notices || []).filter(x => x.card && x !== n && x.at >= from).map(asItem)
  return {
    items: shown, net, netFold,
    spill: items.filter(i => !chosen.has(i)),
    notes: t.notes, folded: t.folded, filings: t.filings,
    routine: t.folded.reduce((n, s) => n + s.filings.length, 0),
  }
}
export type Brief = ReturnType<typeof buildBrief>

// ---------- what the investor has done ----------
export interface Done { cleared: string[]; kept: string[]; notes: string[] }
export const NO_DONE: Done = { cleared: [], kept: [], notes: [] }
export function loadDone(): Done {
  const d = loadJSON<Partial<Done>>('brief', {})
  return { ...NO_DONE, ...(d && typeof d === 'object' ? d : {}) }
}
export const saveDone = (d: Done) => { saveJSON('brief', d) }

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
export function lastSeen(): string | null { return load('seen') }
export const markSeen = (iso: string) => { save('seen', iso) }

// A question for the company's next call, from what just happened: a CEO, CFO or MD leaving first, then a margin
// that fell a point or more on a year ago, then profit down a fifth or more. Null when the news raises none.
const ROLE = (r: string) => r.replace(/\bChief Financial Officer\b/i, 'CFO').replace(/\bChief Executive Officer\b/i, 'CEO').replace(/\bManaging Director\b/i, 'MD')
const departed = (i: Item) => [i.with?.lead, i.story?.lead].flatMap(f => f?.people || []).find(p => p.seniority === 'top' && ['resigned', 'ceased', 'retired'].includes(p.action))
// The kind of question an item raises, decided once, so the person beside it fits it everywhere (the card, Who to ask,
// the end band): a CEO, CFO or MD leaving, or the numbers (results, or a move on results). Null for anything else:
// an arrival keeps its path, and a deal or a tax order keeps who fits that event
export type Kind = 'leave' | 'numbers'
export function questionKind(i: Item): Kind | null {
  if (departed(i)) return 'leave'
  return i.story?.lead?.results || i.kind === 'results' || i.move?.explainedBy?.category === 'results' ? 'numbers' : null
}
// Which of the numbers a question is about, so the person's own question follows it: a margin that fell, profit that
// fell, a lender's credit cost, or none of these (the person's own seat question)
export type Topic = 'margin' | 'profit' | 'credit'
export const topicOf = (q: string): Topic | null =>
  /the margin fell/.test(q) ? 'margin' : /^Profit fell/.test(q) ? 'profit' : /\bcredit costs?\b/i.test(q) ? 'credit' : null
export function newsTopic(i: Item, push: Push): Topic | null {
  const q = departed(i) ? null : newsQuestion(i, push)
  return q ? topicOf(q) : null
}
export function newsQuestion(i: Item, push: Push): string | null {
  const gone = departed(i)
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
  if (dm <= -1 && rev?.yoy != null) return `Revenue ${grew(rev.yoy)} on a year ago${eb?.yoy != null ? ` and operating profit (EBITDA) ${eb.yoy >= 0 ? 'only ' : ''}${grew(eb.yoy).replace(/^grew /, '')}` : ''}: the margin fell ${Math.abs(dm).toFixed(1)} percentage points. Which costs rose faster, and do they ease from here?`
  if (pat?.yoy != null && pat.yoy <= -20) return `Profit fell ${Math.abs(pat.yoy).toFixed(0)}% on a year ago. How much of that is one-off?`
  return null
}
