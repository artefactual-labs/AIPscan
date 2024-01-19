import { resolve } from "path";
import { defineConfig } from "vite";
import inject from "@rollup/plugin-inject";

export default defineConfig({
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
  ],
});
