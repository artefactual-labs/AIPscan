$(document).ready(function () {
  let searchParams = new URLSearchParams(window.location.search);

  formatCounts = new FormatCountData(
    searchParams.get("amss_id"),
    searchParams.get("storage_location"),
    searchParams.get("start_date"),
    searchParams.get("end_date"),
  );

  formatCounts.getFormatCountsData().then(function (results) {
    // Calculate labels and values for pie chart
    jsonLabels = [];
    jsonValues = [];

    for (let format in formatCounts.formatCounts) {
      jsonLabels.push(format);
      jsonValues.push(formatCounts.formatCounts[format]);
    }

    // Set number of different formats
    $("#chart_different_formats").text(jsonLabels.length);

    // Draw format chart
    let randCols = [];

    let makeColor = function () {
      let r = Math.floor(Math.random() * 255);
      let g = Math.floor(Math.random() * 255);
      let b = Math.floor(Math.random() * 255);
      return "rgb(" + r + "," + g + "," + b + ")";
    };

    for (let x = 0; x < jsonValues.length; x++) {
      randCols.push(makeColor());
    }

    let canvas = document.getElementById("chart");
    let ctx = canvas.getContext("2d");

    let config = {
      type: "pie",
      data: {
        labels: jsonLabels,
        datasets: [
          {
            data: jsonValues,
            label: "Formats chart",
            backgroundColor: randCols,
          },
        ],
      },
      options: { responsive: true },
    };

    let myPie = new Chart(ctx, config);
  });
});
