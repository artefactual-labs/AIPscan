import { resolve } from "path";
import { defineConfig } from "vite";
import inject from "@rollup/plugin-inject";

const rawLogLevel = process.env.LOG_LEVEL ?? "warning";
const logLevel = rawLogLevel === "warning" ? "warn" : rawLogLevel;

export default defineConfig({
  logLevel: logLevel,
  base: "/static/dist/base",
  build: {
    rollupOptions: {
      input: {
        base: resolve(__dirname, "entry/base.entry.js"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
    outDir: "AIPscan/static/dist/base",
  },
  plugins: [
    inject({
      include: "**/*.js",
      $: "jquery",
      jQuery: "jquery",
    }),
  ],
});
