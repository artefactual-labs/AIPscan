import { resolve } from "path";
import { copyFileSync, mkdirSync } from "fs";
import { defineConfig } from "vite";
import inject from "@rollup/plugin-inject";

const rawLogLevel = process.env.LOG_LEVEL ?? "warning";
const logLevel = rawLogLevel === "warning" ? "warn" : rawLogLevel;

const distDir = "AIPscan/static/dist/plot_formats_count";
const plotlySource = resolve(
  process.cwd(),
  "node_modules/plotly.js-dist/plotly.js",
);

const copyPlotlyPlugin = () => ({
  name: "copy-plotly-js",
  writeBundle() {
    const destinationDir = resolve(process.cwd(), distDir);
    mkdirSync(destinationDir, { recursive: true });
    copyFileSync(plotlySource, resolve(destinationDir, "plotly.js"));
  },
});

export default defineConfig({
  logLevel: logLevel,
  base: "/static/dist/plot_formats_count",
  build: {
    rollupOptions: {
      input: {
        plot_formats_count: resolve(
          __dirname,
          "entry/plot_formats_count.entry.js",
        ),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
    outDir: "AIPscan/static/dist/plot_formats_count",
  },
  plugins: [
    inject({
      include: "**/*.js",
      $: "jquery",
      jQuery: "jquery",
      Plotly: "Plotly",
    }),
    copyPlotlyPlugin(),
  ],
});
