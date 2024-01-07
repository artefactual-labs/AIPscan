$(document).ready(function () {
  // Draw format chart
  let randCols = [];
  let jsonLabels = JSON.parse($("#chart_labels").val());
  let jsonValues = JSON.parse($("#chart_values").val());

  let makeColor = function () {
    var r = Math.floor(Math.random() * 255);
    var g = Math.floor(Math.random() * 255);
    var b = Math.floor(Math.random() * 255);
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
