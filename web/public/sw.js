// Offline copy of the last snapshot, for FINN opened from the home screen with no signal.
// The page and data always try the network first, so a new deploy or snapshot is never hidden;
// the cached copy is only used when the network fails. Hashed assets never change, so they come from cache.
// /api (live lookups) is never touched.
const CACHE = 'finn-v1'

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
))

self.addEventListener('fetch', e => {
  const req = e.request
  const url = new URL(req.url)
  if (req.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return
  if (url.pathname.startsWith('/assets/')) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => keep(req, r))))
  } else if (req.mode === 'navigate' || url.pathname.startsWith('/data/') || /\.(svg|png|webmanifest)$/.test(url.pathname)) {
    // Navigations are stored under '/' so any hash route opens offline
    const key = req.mode === 'navigate' ? '/' : req
    e.respondWith(fetch(req).then(r => keep(key, r)).catch(() => caches.match(key).then(hit => hit || Response.error())))
  }
})

function keep(key, r) {
  if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(key, copy)) }
  return r
}

// A tapped notification opens the brief's reader, in the open window if there is one
self.addEventListener('notificationclick', e => {
  e.notification.close()
  const url = (e.notification.data && e.notification.data.url) || '/'
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cs => {
    const c = cs.find(x => new URL(x.url).origin === location.origin)
    if (c) { c.navigate(url).catch(() => {}); return c.focus() }
    return self.clients.openWindow(url)
  }))
})
