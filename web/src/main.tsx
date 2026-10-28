import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter/wght.css'
import '@fontsource/pt-serif/latin-400.css'
import './styles.css'
import { App } from './App'

// One reveal style: blocks fade in and rise as they enter the view (CSS under 'reveal')
const REVEAL = '.card, .book-row, .company section, .fold-group, .chips-sec'
if (typeof IntersectionObserver !== 'undefined' && typeof MutationObserver !== 'undefined') {
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('seen'); io.unobserve(e.target) }
  }), { rootMargin: '0px 0px -40px 0px' })
  const scan = () => document.querySelectorAll(`:is(${REVEAL}):not(.seen):not([data-rv])`).forEach(el => {
    el.setAttribute('data-rv', ''); io.observe(el)
  })
  new MutationObserver(scan).observe(document.getElementById('root')!, { childList: true, subtree: true })
  document.documentElement.classList.add('rv-on')
}

createRoot(document.getElementById('root')!).render(<App />)
