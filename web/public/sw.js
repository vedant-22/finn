// Offline copy of the last snapshot, for FINN opened from the home screen with no signal.
// The page and data always try the network first, so a new deploy or snapshot is never hidden;
// the cached copy is used only when the network fails or gives no answer in 4 s. Hashed assets never change, so
// they come from cache.
// /api (live lookups) is never touched.
const CACHE = 'finn-v1'
// The page asks for its code and fonts in CORS mode; a server's Vary must not stop a same-origin copy matching
const ANY = { ignoreVary: true }

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
))

self.addEventListener('fetch', e => {
  const req = e.request
  const url = new URL(req.url)
  if (req.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return
  if (url.pathname.startsWith('/assets/')) {
    e.respondWith(caches.match(req, ANY).then(hit => hit || fetch(req).then(r => keep(req, r))))
  } else if (req.mode === 'navigate' || url.pathname.startsWith('/data/') || /\.(svg|png|webmanifest)$/.test(url.pathname)) {
    // Navigations are stored under '/' so any hash route opens offline; only FINN's page, never a file opened in the tab
    const nav = req.mode === 'navigate', key = nav ? '/' : req
    const net = fetch(req).then(r => nav && !(r.headers.get('content-type') || '').startsWith('text/html') ? r : keep(key, r))
    e.waitUntil(net.catch(() => {}))
    const saved = () => caches.match(key, ANY)
    // A weak signal is not no signal: with no answer in 4 s, the saved copy, while the fetch still refreshes it
    const slow = new Promise(res => setTimeout(res, 4000)).then(saved).then(hit => hit || net).catch(() => Response.error())
    e.respondWith(Promise.race([net.catch(() => saved().then(hit => hit || Response.error())), slow]))
  }
})

// The first visit loaded the page, its code and the snapshot before this worker was in charge. The page sends
// those URLs once the worker is ready, so a first visit opens with no signal too. Only FINN's own page, assets and
// data are taken, never /api, at most 80, and each is fetched by the worker itself.
self.addEventListener('message', e => {
  const urls = e.data && Array.isArray(e.data.cache) ? e.data.cache.slice(0, 80) : []
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(urls.map(u => {
    let url
    try { url = new URL(u, location.origin) } catch { return }
    if (url.origin !== location.origin || !(url.pathname === '/' || /^\/(assets|data)\//.test(url.pathname))) return
    const key = url.pathname === '/' ? '/' : url.href
    return c.match(key, ANY).then(hit => hit || fetch(url.href).then(r => { if (r.ok) return c.put(key, r) })).catch(() => {})
  }))))
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
