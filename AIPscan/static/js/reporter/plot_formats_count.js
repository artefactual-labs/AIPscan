$(document).ready(function () {
  var data = [
    {
      x: JSON.parse($("#plot_x_axis").val()),
      y: JSON.parse($("#plot_y_axis").val()),
      text: JSON.parse($("#plot_format").val()),
      customdata: JSON.parse($("#plot_humansize").val()),
      marker: { size: 7 },
      hovertemplate:
        "<b>%{text}</b><br />" +
        "count: %{y}<br />" +
        "size: %{customdata}<br />" +
        "size in bytes: %{x}" +
        "<extra></extra>",
      type: "scatter",
      mode: "markers",
    },
  ];
  var layout = {
    hovermode: "closest",
    yaxis: { title: "format occurence count" },
    xaxis: { title: "total size in bytes" },
    showlegend: false,
  };

  Plotly.newPlot("scatterplot", data, layout, { displayModeBar: false });
});
