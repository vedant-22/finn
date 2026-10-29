/// <reference types="vite/client" />
import { createRoot } from 'react-dom/client'
import './fonts/fonts.css'
import './styles.css'
import { App } from './App'

// One reveal style: blocks fade in as they enter the view (CSS under 'reveal'); a before-and-after plays its steps
const REVEAL = '.card, .company > section, .fold, .chips-sec, .end-band-in, .fo-trail'
if (typeof IntersectionObserver !== 'undefined' && typeof MutationObserver !== 'undefined') {
  const io = new IntersectionObserver(es => es.forEach(e => {
    // A data attribute, not a class: React rewrites className when a fold opens, and a class would be lost with it
    if (e.isIntersecting) { e.target.setAttribute('data-seen', ''); io.unobserve(e.target) }
  }), { rootMargin: '0px 0px -40px 0px' })
  const scan = () => document.querySelectorAll(`:is(${REVEAL}):not([data-rv])`).forEach(el => {
    el.setAttribute('data-rv', ''); io.observe(el)
  })
  new MutationObserver(scan).observe(document.getElementById('root')!, { childList: true, subtree: true })
  document.documentElement.classList.add('rv-on')
}

// iOS Safari only applies :active once a touch listener exists
document.addEventListener('touchstart', () => {}, { passive: true })

// Keeps the last snapshot for opening with no signal (public/sw.js); network first, so nothing goes stale
if (import.meta.env.PROD && 'serviceWorker' in navigator) addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))

createRoot(document.getElementById('root')!).render(<App />)
