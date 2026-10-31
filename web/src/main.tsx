/// <reference types="vite/client" />
import { createRoot } from 'react-dom/client'
import './fonts/fonts.css'
import './styles.css'
import './looks.css'
import { App } from './App'

// Colour trial (section 9): ?look=a|b|c
const look = new URLSearchParams(location.search).get('look')
if (look) document.documentElement.dataset.look = look

// iOS Safari only applies :active once a touch listener exists
document.addEventListener('touchstart', () => {}, { passive: true })

// Keeps the last snapshot for opening with no signal (public/sw.js); network first, so nothing goes stale
if (import.meta.env.PROD && 'serviceWorker' in navigator) addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))

createRoot(document.getElementById('root')!).render(<App />)
