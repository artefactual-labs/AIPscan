import { resolve } from "path";
import { defineConfig } from "vite";

const rawLogLevel = process.env.LOG_LEVEL ?? "warning";
const logLevel = rawLogLevel === "warning" ? "warn" : rawLogLevel;

export default defineConfig({
  logLevel: logLevel,
  base: "/static/dist/report_base",
  build: {
    rolldownOptions: {
      input: {
        report_base: resolve(__dirname, "entry/report_base.entry.js"),
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
    outDir: "AIPscan/static/dist/report_base",
  },
});
