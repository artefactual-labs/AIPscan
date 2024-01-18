$(document).ready(function () {
  var storageServiceId = $("#ss").val();
  var storageLocationId = $("#sl").val();

  const DATE_ALERT_START = "The start date must be before the end date";
  const DATE_ALERT_END = "The end date must be after the start date";
  const LIMIT_ALERT = "The limit must be numeric and larger than zero.";

  function reloadPage(ignoreLocation) {
    var url = new URL("reporter/reports", $("body").data("url-root"));
    var params = { amss_id: $("#ss").val() };

    if (ignoreLocation !== true) {
      params["storage_location"] = $("#sl").val();
    }

    url.search = new URLSearchParams(params).toString();
    window.location.href = url.href;
  }

  $("#ss").on("change", function () {
    reloadPage(true);
  });

  $("#sl").on("change", function () {
    reloadPage(false);
  });

  $("#startdate").datepicker({
    dateFormat: "yy-mm-dd",
    onSelect: function (date) {
      let enddate = $("#enddate").val();
      if (enddate != "" && enddate < date) {
        alert(DATE_ALERT_START);
      }

      const url = new URL("reporter/update_dates", $("body").data("url-root"));

      fetch(url.href, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_date: date }),
      });
    },
  });

  $("#enddate").datepicker({
    dateFormat: "yy-mm-dd",
    onSelect: function (date) {
      let startdate = $("#startdate").val();
      if (startdate != "" && startdate > date) {
        alert(DATE_ALERT_START);
      }

      const url = new URL("reporter/update_dates", $("body").data("url-root"));

      fetch(url.href, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ end_date: date }),
      });
    },
  });

  $("#report1a").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL(
        "reporter/report_formats_count",
        $("body").data("url-root"),
      );
      const params = {
        start_date: startdate,
        end_date: enddate,
        amss_id: storageServiceId,
        storage_location: storageLocationId,
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#report1b").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL(
        "reporter/chart_formats_count",
        $("body").data("url-root"),
      );
      const params = {
        start_date: startdate,
        end_date: enddate,
        amss_id: storageServiceId,
        storage_location: storageLocationId,
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#report1c").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL(
        "reporter/plot_formats_count",
        $("body").data("url-root"),
      );
      const params = {
        start_date: startdate,
        end_date: enddate,
        amss_id: storageServiceId,
        storage_location: storageLocationId,
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#aipContents").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL("reporter/aip_contents", $("body").data("url-root"));
      const params = {
        amss_id: storageServiceId,
        storage_location: storageLocationId,
        start_date: startdate,
        end_date: enddate,
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#report3a").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL(
        "reporter/report_format_versions_count",
        $("body").data("url-root"),
      );
      const params = {
        amss_id: storageServiceId,
        storage_location: storageLocationId,
        start_date: startdate,
        end_date: enddate,
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#preservationDerivatives").on("click", function () {
    var url = new URL(
      "reporter/preservation_derivatives",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url.href);
  });

  $("#largestAIPs").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    var limit = $("#largestAipsLimit").val();

    if (!$.isNumeric(limit) || limit < 1) {
      alert(LIMIT_ALERT);

      return false;
    }

    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var params = {
        amss_id: storageServiceId,
        start_date: startdate,
        end_date: enddate,
        storage_location: storageLocationId,
        limit: limit,
      };

      var url = new URL("reporter/largest_aips", $("body").data("url-root"));
      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#largestFiles").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    var limit = $("#largestFilesLimit").val();

    if (!$.isNumeric(limit) || limit < 1) {
      alert(LIMIT_ALERT);

      return false;
    }

    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var params = {
        amss_id: storageServiceId,
        start_date: startdate,
        end_date: enddate,
        storage_location: storageLocationId,
        limit: limit,
      };

      var url = new URL("reporter/largest_files", $("body").data("url-root"));
      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });

  $("#aipsByOriginalFormat").on("click", function () {
    var fileFormat = $("#originalFormatSelect").val();

    var url = new URL(
      "reporter/aips_by_file_format",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      file_format: fileFormat,
      original_files: "True",
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url.href);
  });

  $("#aipsByPreservationFormat").on("click", function () {
    var fileFormat = $("#preservationFormatSelect").val();

    var url = new URL(
      "reporter/aips_by_file_format",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      file_format: fileFormat,
      original_files: "False",
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url.href);
  });

  $("#aipsByOriginalPUID").on("click", function () {
    var puid = $("#originalPUIDSelect").val();

    var url = new URL("reporter/aips_by_puid", $("body").data("url-root"));
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      puid: puid,
      original_files: "True",
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url.href);
  });

  $("#aipsByPreservationPUID").on("click", function () {
    var puid = $("#preservationPUIDSelect").val();

    var url = new URL("reporter/aips_by_puid", $("body").data("url-root"));
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      puid: puid,
      original_files: "False",
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url.href);
  });

  $("#transferLogTabular").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();

    var url = new URL(
      "reporter/ingest_log_tabular",
      $("body").data("url-root"),
    );
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      start_date: startdate,
      end_date: enddate,
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url.href);
  });

  $("#transferLogGantt").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();

    var url = new URL("reporter/ingest_log_gantt", $("body").data("url-root"));
    const params = {
      amss_id: storageServiceId,
      storage_location: storageLocationId,
      start_date: startdate,
      end_date: enddate,
    };

    url.search = new URLSearchParams(params).toString();
    window.open(url);
  });

  $("#storageLocations").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL(
        "reporter/storage_locations",
        $("body").data("url-root"),
      );
      const params = {
        amss_id: storageServiceId,
        start_date: startdate,
        end_date: enddate,
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url);
    }
  });

  $("#storageLocationsTimeseries").on("click", function () {
    var startdate = $("#startdate").val();
    var enddate = $("#enddate").val();
    if (enddate < startdate) {
      alert(DATE_ALERT_START);
    } else {
      var url = new URL(
        "reporter/storage_locations_usage_over_time",
        $("body").data("url-root"),
      );
      const params = {
        amss_id: storageServiceId,
        start_date: startdate,
        end_date: enddate,
        metric: "aips",
        cumulative: "false",
      };

      url.search = new URLSearchParams(params).toString();
      window.open(url.href);
    }
  });
});
