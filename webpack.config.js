const path = require('path');

module.exports = {
  target: 'web',
  mode: "production",
  entry: {
    "base": "./AIPscan/static/js/base.entry.js",
    "datatables": "./AIPscan/static/js/datatables.entry.js",
    "report_base": "./AIPscan/static/js/report_base.entry.js"
  },
  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, 'AIPscan/static/js/build')
  },
  module: {
    rules: [
      {
        test: require.resolve("jquery"),
        loader: "expose-loader",
        options: {
          exposes: ["$", "jQuery"],
        },
      },
      {
        test: /\.css$/,
        use: [
          'style-loader',
          'css-loader'
        ]
      }
    ]
  }
};
