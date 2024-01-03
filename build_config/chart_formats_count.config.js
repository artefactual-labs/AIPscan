import { resolve } from 'path'
import { defineConfig } from 'vite'
import inject from '@rollup/plugin-inject'

export default defineConfig({
  base: '/static/dist/chart_formats_count',
  build: {
    rollupOptions: {
      input: {
        chart_formats_count: resolve(__dirname, 'entry/chart_formats_count.entry.js')
      },
    },
    outDir: "AIPscan/static/dist/chart_formats_count"
  },
  plugins: [
    inject({
      include: '**/*.js',
      $: 'jquery',
      'jQuery': 'jquery'
    }),
  ]
})
