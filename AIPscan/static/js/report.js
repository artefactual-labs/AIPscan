$(document).ready(function () {
  // Download CSV of current report
  $("#downloadCSV").on("click", function () {
    window.location.href = window.location.href + "&csv=True";
  });

  // Reload largest files report on change to file type dropdown
  $("#fileTypeSelector").on("change", function () {
    var fileType = $("#fileTypeSelector").val();
    var storageServiceId = $("#storageServiceID").text();
    var storageLocationId = $("#storageLocationID").text();
    var startDate = $("#startDate").text();
    var endDate = $("#endDate").text();
    var limit = $("#limit").text();

    var url = new URL("reporter/largest_files", $("body").data("url-root"));
    const params = {
      amss_id: storageServiceId,
      start_date: startDate,
      end_date: endDate,
      storage_location: storageLocationId,
      file_type: fileType,
      limit: limit,
    };

    url.search = new URLSearchParams(params).toString();
    window.location.href = url;
  });

  // Reload preservation derivatives report on change to AIP dropdown
  $("#aipSelector").on("change", function () {
    var aipUUID = $("#aipSelector").val();
    var storageServiceId = $("#storageServiceID").text();
    var storageLocationId = $("#storageLocationID").text();

    var url = new URL(
      "reporter/preservation_derivatives",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      aip_uuid: aipUUID,
    };

    url.search = new URLSearchParams(params).toString();
    window.location.href = url.href;
  });

  // Reload storage locations timeseries report on change to metrics or
  // cumulative selectors
  $("#metricSelector").on("change", function () {
    var metric = $("#metricSelector").val();
    var cumulative = $("#cumulativeSelector").val();
    var storageServiceId = $("#storageServiceID").text();
    var startDate = $("#startDate").text();
    var endDate = $("#endDate").text();

    var url = new URL(
      "reporter/storage_locations_usage_over_time",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      start_date: startDate,
      end_date: endDate,
      metric: metric,
      cumulative: cumulative,
    };

    url.search = new URLSearchParams(params).toString();
    window.location.href = url;
  });

  $("#cumulativeSelector").on("change", function () {
    var metric = $("#metricSelector").val();
    var cumulative = $("#cumulativeSelector").val();
    var storageServiceId = $("#storageServiceID").text();
    var startDate = $("#startDate").text();
    var endDate = $("#endDate").text();

    var url = new URL(
      "reporter/storage_locations_usage_over_time",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      start_date: startDate,
      end_date: endDate,
      metric: metric,
      cumulative: cumulative,
    };

    url.search = new URLSearchParams(params).toString();
    window.location.href = url.href;
  });
});
