import { resolve } from "path";
import { defineConfig } from "vite";
import inject from "@rollup/plugin-inject";

const rawLogLevel = process.env.LOG_LEVEL ?? "warning";
const logLevel = rawLogLevel === "warning" ? "warn" : rawLogLevel;

export default defineConfig({
  logLevel: logLevel,
  base: "/static/dist/chart_formats_count",
  build: {
    rollupOptions: {
      input: {
        chart_formats_count: resolve(
          __dirname,
          "entry/chart_formats_count.entry.js",
        ),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
    outDir: "AIPscan/static/dist/chart_formats_count",
  },
  plugins: [
    inject({
      include: "**/*.js",
      $: "jquery",
      jQuery: "jquery",
    }),
  ],
});
