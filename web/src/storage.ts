// Everything FINN keeps on this phone, declared once. The Your data sheet lists these groups, Clear this
// phone removes exactly FINN's own keys and caches, and test/storage.test.mjs fails if any other file
// touches storage, or names a key that isn't here. No imports: node's tests load this file directly.

export type Group = 'lines' | 'reading' | 'answers' | 'lookups' | 'alerts' | 'offline'

// In the order the sheet lists them
export const GROUPS: { group: Group; label: string }[] = [
  { group: 'lines', label: 'Your alert levels' },
  { group: 'reading', label: 'What you’ve read and cleared' },
  { group: 'answers', label: 'Your answers on whether two names are the same person' },
  { group: 'lookups', label: 'The companies you looked up' },
  { group: 'alerts', label: 'Whether alerts are on' },
  { group: 'offline', label: 'A copy of the latest announcements and the companies you opened, for when there is no signal' },
]

type Area = 'local' | 'session'
const KEYS = {
  lines: { key: 'finn.lines', area: 'local', group: 'lines' },
  brief: { key: 'finn.brief', area: 'local', group: 'reading' },             // cleared, kept, notes read
  seen: { key: 'finn.seen', area: 'local', group: 'reading' },               // when the brief was last opened
  sieved: { key: 'finn-sieved', area: 'session', group: 'reading' },         // the count has rolled this visit
  identity: { key: 'finn.identity', area: 'local', group: 'answers' },       // Same person or Someone else
  identityViews: { key: 'finn.identity.views', area: 'local', group: 'answers' }, // the views rebuilt from them
  recent: { key: 'finn.recent', area: 'local', group: 'lookups' },
  company: { key: 'finn.c.', area: 'local', group: 'lookups' },              // a prefix: finn.c.<SYMBOL>
  alerts: { key: 'finn.alerts', area: 'local', group: 'alerts' },
} as const satisfies Record<string, { key: string; area: Area; group: Group }>
export type Key = keyof typeof KEYS
export const STORED: readonly { name: Key; key: string; area: Area; group: Group }[] =
  (Object.keys(KEYS) as Key[]).map(name => ({ name, ...KEYS[name] }))

// The service worker's cache (public/sw.js uses the same name; a test holds them equal)
export const CACHE = 'finn-v1'
export const CACHE_GROUP: Group = 'offline'

// FINN's namespace: every key above, and any an older FINN left behind. Clear this phone removes these and nothing else.
export const OWNED = /^finn[.-]/

const store = (a: Area): Storage | null => {
  try { return a === 'local' ? globalThis.localStorage : globalThis.sessionStorage } catch { return null }
}

// Reads and writes never throw: in private mode or with storage full, FINN works for this visit and keeps nothing
export function load(k: Key, sub = ''): string | null {
  try { return store(KEYS[k].area)?.getItem(KEYS[k].key + sub) ?? null } catch { return null }
}
export function loadJSON<T>(k: Key, fallback: T, sub = ''): T {
  const s = load(k, sub)
  if (s == null) return fallback
  try { return JSON.parse(s) as T } catch { return fallback }
}
export function save(k: Key, value: string, sub = ''): boolean {
  try { store(KEYS[k].area)!.setItem(KEYS[k].key + sub, value); return true } catch { return false }
}
export const saveJSON = (k: Key, value: unknown, sub = '') => save(k, JSON.stringify(value), sub)

// Clear this phone: every FINN key in both stores and every FINN cache. The caller reloads to a first visit.
export async function clearPhone(): Promise<void> {
  for (const a of ['local', 'session'] as Area[]) {
    const s = store(a)
    if (!s) continue
    try {
      const mine: string[] = []
      for (let i = 0; i < s.length; i++) { const k = s.key(i); if (k && OWNED.test(k)) mine.push(k) }
      mine.forEach(k => s.removeItem(k))
    } catch { /* storage unreadable: nothing of FINN's could be kept there either */ }
  }
  try {
    const c = (globalThis as any).caches as CacheStorage | undefined
    if (c) for (const name of await c.keys()) if (OWNED.test(name)) await c.delete(name)
  } catch { /* no cache storage on this phone */ }
}
