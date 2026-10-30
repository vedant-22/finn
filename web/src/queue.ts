// The brief: the few things to read in a window, and what the investor has done with each.
// Pure functions over the snapshot, so they can be tested without a browser.
import { triage, type Lines, type Move, type Push, type Story } from './lib.ts'

export interface Item {
  key: string; symbol: string; at: string
  kind: 'results' | 'people' | 'move' | 'filing'
  story?: Story; move?: Move
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
