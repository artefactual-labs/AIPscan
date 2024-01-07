$(document).ready(function () {
  var storageServiceId = $("#ss").val();
  var storageLocationId = $("#sl").val();

  function reloadPage(ignoreLocation) {
    var storageServiceId = $("#ss").val();
    var storageLocationId = $("#sl").val();

    var url = new URL("/reporter/aips", $("body").data("url-root"));
    var params = {
      amss_id: storageServiceId,
    };

    if (ignoreLocation !== true) {
      params["storage_location"] = storageLocationId;
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
});
