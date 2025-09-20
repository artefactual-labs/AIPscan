import { resolve } from "path";
import { defineConfig } from "vite";
import inject from "@rollup/plugin-inject";

const rawLogLevel = process.env.LOG_LEVEL ?? "warning";
const logLevel = rawLogLevel === "warning" ? "warn" : rawLogLevel;

export default defineConfig({
  logLevel: logLevel,
  base: "/static/dist/report_base",
  build: {
    rollupOptions: {
      input: {
        report_base: resolve(__dirname, "entry/report_base.entry.js"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
    outDir: "AIPscan/static/dist/report_base",
  },
  plugins: [
    inject({
      include: "**/*.js",
      $: "jquery",
      jQuery: "jquery",
    }),
  ],
});
