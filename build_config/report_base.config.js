import { resolve } from 'path'
import { defineConfig } from 'vite'
import inject from '@rollup/plugin-inject'

export default defineConfig({
  base: '/static/dist/report_base',
  build: {
    rollupOptions: {
      input: {
        report_base: resolve(__dirname, 'entry/report_base.entry.js')
      }
    },
    outDir: "AIPscan/static/dist/report_base"
  },
  plugins: [
    inject({
      include: '**/*.js',
      $: 'jquery',
      'jQuery': 'jquery'
    })
  ]
})
