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

export default defineConfig({
  plugins: [react(), preloadFonts()],
  server: { proxy: { '/api': 'http://localhost:3001' } },
})
