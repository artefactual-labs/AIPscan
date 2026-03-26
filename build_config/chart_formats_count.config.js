import { resolve } from "path";
import { defineConfig } from "vite";

const rawLogLevel = process.env.LOG_LEVEL ?? "warning";
const logLevel = rawLogLevel === "warning" ? "warn" : rawLogLevel;

export default defineConfig({
  logLevel: logLevel,
  base: "/static/dist/chart_formats_count",
  build: {
    rolldownOptions: {
      input: {
        chart_formats_count: resolve(
          __dirname,
          "entry/chart_formats_count.entry.js",
        ),
      },
      transform: {
        inject: {
          $: "jquery",
          jQuery: "jquery",
        },
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
    outDir: "AIPscan/static/dist/chart_formats_count",
  },
});
