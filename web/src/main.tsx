/// <reference types="vite/client" />
import { createRoot } from 'react-dom/client'
import './fonts/fonts.css'
import './styles.css'
import { App } from './App'
import { startCursorTag, startReveal } from './motion'

// One reveal: blocks fade and rise a little as they enter the view, together ones a beat apart (motion.ts)
startReveal('.card, .book-card, .tile, .company > section, .company > .co-pic, .fold, .og-panel, .end-band-in, .ask.lead', document.getElementById('root')!)
// Over a card's picture, on a desktop with a mouse, a small Read more follows the pointer (motion.ts)
startCursorTag()

// iOS Safari only applies :active once a touch listener exists
document.addEventListener('touchstart', () => {}, { passive: true })

// Keeps the last snapshot for opening with no signal (public/sw.js); network first, so nothing goes stale.
// What this visit loaded before the worker was in charge is handed to it, so even a first visit opens offline.
if (import.meta.env.PROD && 'serviceWorker' in navigator) addEventListener('load', () => {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
  const handOver = () => navigator.serviceWorker.ready.then(reg => reg.active?.postMessage({
    cache: ['/', ...performance.getEntriesByType('resource').map(e => e.name)
      .filter(u => { const x = new URL(u); return x.origin === location.origin && /^\/(assets|data)\//.test(x.pathname) })],
  })).catch(() => {})
  handOver()
  navigator.serviceWorker.addEventListener('controllerchange', handOver, { once: true })
})

createRoot(document.getElementById('root')!).render(<App />)
