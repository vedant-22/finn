import { readFileSync } from 'node:fs'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// The two faces the first screen needs, fetched alongside the CSS instead of after it
const preloadFonts = (): Plugin => ({
  name: 'preload-fonts',
  apply: 'build',
  transformIndexHtml: {
    order: 'post',
    handler: (_html, ctx) => Object.keys(ctx.bundle || {})
      .filter(f => /(inter-latin-wght-normal|pt-serif-latin-400-normal)-[\w-]+\.woff2$/.test(f))
      .map(f => ({ tag: 'link', attrs: { rel: 'preload', href: `/${f}`, as: 'font', type: 'font/woff2', crossorigin: '' }, injectTo: 'head' as const })),
  },
})

// `vite preview` serves the same security headers as Vercel, so e2e runs under the real policy
const vercel = JSON.parse(readFileSync(new URL('../vercel.json', import.meta.url), 'utf8'))
// FINN_API_PORT moves the local API off 3001, so a second preview can run beside one already open
const api = `http://localhost:${process.env.FINN_API_PORT || 3001}`
const siteHeaders = Object.fromEntries(vercel.headers.find((h: any) => h.source === '/(.*)').headers.map((h: any) => [h.key, h.value]))

export default defineConfig({
  plugins: [react(), preloadFonts()],
  server: { proxy: { '/api': api } },
  // the preview reaches the local API too (pipeline/dev_api.py), so e2e can put a question to the Network
  preview: { headers: siteHeaders, proxy: { '/api': api } },
})
