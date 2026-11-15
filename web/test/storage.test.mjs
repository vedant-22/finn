// What FINN keeps on this phone, held to one registry (src/storage.ts). Run: npm test
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { CACHE, CACHE_GROUP, GROUPS, OWNED, STORED, clearPhone, load, loadJSON, save } from '../src/storage.ts'
import { plainError } from '../src/lib.ts'

const src = new URL('../src/', import.meta.url).pathname
const files = fs.readdirSync(src, { recursive: true }).filter(f => /\.(ts|tsx)$/.test(f)).map(f => path.join(src, f))

test('no file but storage.ts touches storage, caches or indexedDB, or names a key of its own', () => {
  assert.ok(files.length > 10, 'the scan found the source')
  const touch = /\b(localStorage|sessionStorage|indexedDB)\b|\bcaches\s*\./
  const key = /['"`]finn[.-]/
  for (const f of files) {
    if (path.basename(f) === 'storage.ts') continue
    const text = fs.readFileSync(f, 'utf8')
    assert.ok(!touch.test(text), `${path.basename(f)} touches storage directly: ${text.match(touch)?.[0]}`)
    assert.ok(!key.test(text), `${path.basename(f)} names a storage key: ${text.match(key)?.[0]}`)
  }
  // index.html and the public folder: only the worker uses Cache Storage, and nothing else stores anything
  const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8')
  assert.ok(!touch.test(html))
})

test("the worker's cache is the registry's, and FINN's own", () => {
  const sw = fs.readFileSync(new URL('../public/sw.js', import.meta.url), 'utf8')
  assert.equal(sw.match(/const CACHE = '([^']+)'/)?.[1], CACHE)
  assert.ok(OWNED.test(CACHE))
  assert.ok(!/\b(localStorage|sessionStorage|indexedDB)\b/.test(sw))
})

test('every key is FINN-owned, every group is listed in the sheet, and every listed group holds something', () => {
  const listed = new Set(GROUPS.map(g => g.group))
  const held = new Set([...STORED.map(s => s.group), CACHE_GROUP])
  for (const s of STORED) assert.ok(OWNED.test(s.key), s.key)
  assert.deepEqual([...held].sort(), [...listed].sort())
  assert.equal(new Set(STORED.map(s => s.key)).size, STORED.length)
})

// A Storage with the browser's interface
function fakeStorage(init = {}, { full = false } = {}) {
  const m = new Map(Object.entries(init))
  return {
    get length() { return m.size }, key: i => [...m.keys()][i] ?? null,
    getItem: k => (m.has(k) ? m.get(k) : null), removeItem: k => { m.delete(k) },
    setItem: (k, v) => { if (full) throw new Error('QuotaExceededError'); m.set(k, String(v)) },
    keys: () => [...m.keys()].sort(),
  }
}
function fakeCaches(names) {
  const s = new Set(names)
  return { keys: async () => [...s], delete: async n => s.delete(n), names: () => [...s].sort() }
}

test('Clear this phone removes every FINN key and cache, and nothing else', async () => {
  const local = fakeStorage({ 'finn.lines': '{}', 'finn.brief': '{}', 'finn.seen': 'x', 'finn.identity': '{}',
    'finn.identity.views': '{}', 'finn.recent': '[]', 'finn.c.ASTRAL': '{}', 'finn.c.KPIL': '{}', 'finn.alerts': 'on',
    'finn.old-build-key': '1', 'other.app': 'keep', 'finnish': 'keep' })
  const session = fakeStorage({ 'finn-sieved': '1', 'other.session': 'keep' })
  const caches = fakeCaches(['finn-v1', 'finn-v0', 'someone-else'])
  Object.assign(globalThis, { localStorage: local, sessionStorage: session, caches })
  try {
    // every registered key is in the fixture, so the test covers the whole registry
    for (const s of STORED) assert.ok((s.area === 'local' ? local : session).keys().some(k => k.startsWith(s.key)), s.key)
    await clearPhone()
    assert.deepEqual(local.keys(), ['finnish', 'other.app'])
    assert.deepEqual(session.keys(), ['other.session'])
    assert.deepEqual(caches.names(), ['someone-else'])
  } finally {
    for (const k of ['localStorage', 'sessionStorage', 'caches']) delete globalThis[k]
  }
})

test('reads and writes never throw: full storage keeps nothing, unreadable JSON is the fallback', () => {
  Object.assign(globalThis, { localStorage: fakeStorage({ 'finn.lines': '{not json' }, { full: true }), sessionStorage: fakeStorage() })
  try {
    assert.equal(save('alerts', 'on'), false)
    assert.equal(load('alerts'), null)
    assert.deepEqual(loadJSON('lines', { a: 1 }), { a: 1 })
    assert.equal(save('sieved', '1'), true)
    assert.equal(load('sieved'), '1')
  } finally {
    delete globalThis.localStorage; delete globalThis.sessionStorage
  }
  // no storage at all (a locked-down browser): still no throw
  assert.equal(load('lines'), null)
  assert.equal(save('lines', '{}'), false)
})

test('an error never reaches the screen as raw text', () => {
  const quiet = console.error
  console.error = () => {}
  try {
    for (const raw of ['<!doctype html><html><head><title>500 Internal Server Error</title>', 'Unexpected token < in JSON at position 0',
      'HTTP 500', 'TypeError: Cannot read properties of undefined (reading \'x\')', 'Could not load filings']) {
      const said = plainError(raw)
      assert.ok(!said.includes(raw) && !/[<>{}]|TypeError|JSON|HTTP/.test(said), `${raw} -> ${said}`)
      assert.match(said, /^[A-Z].*\.$/)
    }
    assert.match(plainError('Failed to fetch'), /No connection/)
    assert.match(plainError('busy'), /Too many requests/)
  } finally {
    console.error = quiet
  }
})
