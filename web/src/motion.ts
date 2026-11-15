// Scroll motion, after the reference design: each effect is one small hook, transform and opacity only, read and
// written once a frame. With reduced motion asked for, none of them runs and everything sits in place.
import { useEffect, useLayoutEffect, type RefObject } from 'react'
import { gsap } from 'gsap'

export const calm = () => matchMedia('(prefers-reduced-motion: reduce)').matches
// The page's own scroll, kept inside the page, so the bounce at either end of a phone's scroll reads as no move at all
const pageY = () => Math.min(Math.max(scrollY, 0), Math.max(0, document.documentElement.scrollHeight - innerHeight))

// The header comes down into place as the app opens, as the reference design's does on load (y −100% to 0, 0.6s,
// expo.out). Once a load: a header that mounts within that first 0.6s (the loading screen's, then the real one)
// takes the slide up where it has got to, and any header after it is simply there. Set before paint, so it never flashes.
let firstAt = 0
export function useEnter(ref: RefObject<HTMLElement>) {
  useLayoutEffect(() => {
    const el = ref.current
    if (!el || calm()) return
    const now = performance.now(), k = (now - (firstAt ||= now)) / 600
    if (k >= 1) return
    const t = gsap.fromTo(el, { yPercent: -100 }, { yPercent: 0, duration: 0.6, ease: 'expo.out' }).progress(k)
    return () => { t.kill() }
  }, [ref])
}

// The header slides up out of the way on the way down, and back on the way up. Near the top it always shows,
// and a key press that lands inside it (Back, the wordmark) brings it back.
export function useHideOnScroll(ref: RefObject<HTMLElement>) {
  useEnter(ref)
  useEffect(() => {
    const el = ref.current
    if (!el || calm()) return
    let y0 = pageY(), hidden = false, frame = 0
    const set = (h: boolean) => {
      if (h === hidden) return
      hidden = h
      gsap.to(el, { yPercent: h ? -100 : 0, duration: 0.6, ease: 'expo.out', overwrite: true })
    }
    const tick = () => {
      frame = 0
      const y = pageY()
      if (Math.abs(y - y0) < 6) return
      set(y > y0 && y > 80); y0 = y
    }
    const on = () => { if (!frame) frame = requestAnimationFrame(tick) }
    const show = () => set(false)
    addEventListener('scroll', on, { passive: true }); el.addEventListener('focusin', show)
    return () => {
      removeEventListener('scroll', on); el.removeEventListener('focusin', show)
      cancelAnimationFrame(frame); gsap.killTweensOf(el); gsap.set(el, { clearProps: 'transform' })
    }
  }, [ref])
}

// The opening drifts: as the page scrolls it away, its content lags behind by up to 30px, a soft parallax. It sits in
// place at the top, and the block's own bottom padding takes the lag, so it never reaches what follows. The children
// move, not the block, so a warm block's ground stays put.
export function useDrift(ref: RefObject<HTMLElement>) {
  useEffect(() => {
    const el = ref.current
    if (!el || calm()) return
    let frame = 0
    const tick = () => {
      frame = 0
      const p = Math.min(pageY() / (el.offsetTop + el.offsetHeight || 1), 1)
      gsap.set(el.children, { y: 30 * p })
    }
    const on = () => { if (!frame) frame = requestAnimationFrame(tick) }
    addEventListener('scroll', on, { passive: true }); on()
    return () => { removeEventListener('scroll', on); cancelAnimationFrame(frame); gsap.set(el.children, { clearProps: 'transform' }) }
  }, [ref])
}

// A sideways row's thumb: the thin bar under it, as wide as the share of the row in view and placed where the scroll
// is, read and written once a frame. With reduced motion the row is a plain list and this doesn't run.
export function useThumb(row: RefObject<HTMLElement>, thumb: RefObject<HTMLElement>, n: number) {
  useEffect(() => {
    const el = row.current, th = thumb.current
    if (!el || !th || calm()) return
    let frame = 0
    const tick = () => {
      frame = 0
      const w = el.clientWidth, sw = el.scrollWidth, k = Math.min(w / (sw || 1), 1)
      th.parentElement!.style.visibility = k < 1 ? '' : 'hidden'
      gsap.set(th, { x: (sw > w ? el.scrollLeft / (sw - w) : 0) * (1 - k) * w, scaleX: k })
    }
    const on = () => { if (!frame) frame = requestAnimationFrame(tick) }
    el.addEventListener('scroll', on, { passive: true }); addEventListener('resize', on); on()
    return () => { el.removeEventListener('scroll', on); removeEventListener('resize', on); cancelAnimationFrame(frame) }
  }, [row, thumb, n])
}

// The reveal: blocks fade in and rise 12px as they enter the view, on expo.out, and the ones that come in together
// follow each other by 80ms (four at most, so nothing waits long). Seen is a data attribute, not a class: React
// rewrites className when a fold opens, and a class would be lost with it. GSAP's inline values are cleared when a
// block lands, and the CSS for [data-seen] holds it in place from then on.
export function startReveal(sel: string, root: HTMLElement) {
  if (typeof IntersectionObserver === 'undefined' || typeof MutationObserver === 'undefined' || calm()) return
  const io = new IntersectionObserver(es => {
    const els = es.filter(e => e.isIntersecting).map(e => e.target as HTMLElement)
    if (!els.length) return
    els.forEach(el => { el.setAttribute('data-seen', ''); io.unobserve(el) })
    gsap.fromTo(els, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.9, ease: 'expo.out', stagger: i => Math.min(i, 4) * 0.08, clearProps: 'opacity,transform' })
  }, { rootMargin: '0px 0px -40px 0px' })
  const scan = () => document.querySelectorAll(`:is(${sel}):not([data-rv])`).forEach(el => {
    el.setAttribute('data-rv', ''); io.observe(el)
  })
  new MutationObserver(scan).observe(root, { childList: true, subtree: true })
  document.documentElement.classList.add('rv-on')
}

// The cursor label, after the reference design's hover element: over a card's picture, a small "Read more" pill
// follows the pointer a beat behind and grows out of it, and shrinks away off it. Only the picture, as the reference
// keeps its label to media: over the words it would cover what you are reading. Desktop with a mouse only (a fine
// pointer that hovers, a wide window), never on touch, never with reduced motion. One label serves the page, so
// cards come and go without listeners of their own.
const TAG = '.cards .card-img'
const desk = matchMedia('(hover: hover) and (pointer: fine) and (min-width: 1024px)')
export function startCursorTag(text = 'Read more') {
  if (calm()) return
  const tag = document.createElement('div')
  tag.className = 'cursor-tag'; tag.textContent = text; tag.setAttribute('aria-hidden', 'true')
  document.body.append(tag)
  gsap.set(tag, { scale: 0, opacity: 0 })
  const toX = gsap.quickTo(tag, 'x', { duration: 0.3, ease: 'power2.out' }), toY = gsap.quickTo(tag, 'y', { duration: 0.3, ease: 'power2.out' })
  let x = 0, y = 0, on = false, frame = 0
  const show = (v: boolean) => {
    if (v === on) return
    on = v
    gsap.to(tag, { scale: v ? 1 : 0, opacity: v ? 1 : 0, duration: v ? 0.4 : 0.3, ease: 'power2.out', overwrite: 'auto' })
  }
  const over = (t: Element | null) => !!t?.closest(TAG)
  const move = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse' || !desk.matches) return show(false)
    x = e.clientX + 14; y = e.clientY + 14
    const v = over(e.target as Element)
    if (v && !on) gsap.set(tag, { x, y }); else { toX(x); toY(y) }
    show(v)
  }
  // A scroll moves the cards under a still pointer: look again once a frame
  const look = () => { frame = 0; show(over(document.elementFromPoint(x - 14, y - 14))) }
  const scrolled = () => { if (on && !frame) frame = requestAnimationFrame(look) }
  // A press opens the card: the label goes at once, so it isn't caught in the card's morph
  const press = () => { if (on) { on = false; gsap.killTweensOf(tag, 'scale,opacity'); gsap.set(tag, { scale: 0, opacity: 0 }) } }
  addEventListener('pointermove', move, { passive: true })
  addEventListener('scroll', scrolled, { passive: true })
  addEventListener('pointerdown', press, { capture: true, passive: true })
  document.documentElement.addEventListener('pointerleave', () => show(false))
}

// Where the label shows, a click does what it says: the picture opens its card
export const tagClick = (go: () => void) => (e: { target: EventTarget }) => {
  if (desk.matches && !calm() && (e.target as Element).closest(TAG)) go()
}

// A card's picture settles, after the reference design's scale-up image: 1.15 as its top comes in at the bottom of
// the view, 1 once it has risen 40% of the view, tied to the scroll. It scales about the latest price (the right
// edge, at the last close's height), so that point never moves and is never clipped; only the oldest sessions on the
// left wait outside the plate, and they are in before the picture is anywhere you would read it. Its wrapper clips,
// so nothing around it moves. One listener serves every picture: all boxes read, then all scales written, a frame.
const UP = 1.15
const settling = new Map<HTMLElement, (v: number) => void>()
let upFrame = 0
const upTick = () => {
  upFrame = 0
  const h = innerHeight
  const ps = [...settling].map(([el, set]) => [set, (h - el.getBoundingClientRect().top) / (0.4 * h)] as const)
  ps.forEach(([set, p]) => set(UP - (UP - 1) * Math.min(Math.max(p, 0), 1)))
}
const upOn = () => { if (!upFrame) upFrame = requestAnimationFrame(upTick) }
export function useSettle(ref: RefObject<HTMLElement>) {
  useEffect(() => {
    const el = ref.current, img = el?.firstElementChild as SVGSVGElement | null
    if (!el || !img || calm()) return
    const end = img.querySelector('.line')?.getAttribute('d')?.match(/([\d.]+)$/), vh = img.viewBox?.baseVal?.height
    img.style.transformOrigin = `100% ${end && vh ? (+end[1] / vh) * 100 : 50}%`
    if (!settling.size) { addEventListener('scroll', upOn, { passive: true }); addEventListener('resize', upOn) }
    // A plain write, not GSAP's: GSAP would set the scale property to none, and the hover's 4% rides on it
    settling.set(el, v => { img.style.transform = `scale(${v.toFixed(4)})` }); upOn()
    return () => {
      settling.delete(el); img.style.transform = img.style.transformOrigin = ''
      if (!settling.size) { removeEventListener('scroll', upOn); removeEventListener('resize', upOn) }
    }
  }, [ref])
}
