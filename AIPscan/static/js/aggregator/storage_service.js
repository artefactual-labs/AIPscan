function consolePrepend(message) {
  $("#console").prepend(`<div class="log">${message}</div>`);
}

function consoleAppend(message) {
  $("#console").append(`<div class="log">${message}</div>`);
  $("#console").scrollTop($("#console")[0].scrollHeight);
}

// Temporary guard against double-clicking the launch button.
let fetchButton = null;

function setFetchButtonDisabled(disabled) {
  if (fetchButton) {
    fetchButton.prop("disabled", disabled);
  }
}

// TODO: Follow 701fb93538d0's warning: the browser still chains the workflow
// and the POST spin-waits up to a minute. Refactor front/back ends so the
// server owns orchestration, status is durable, and requests stay sub-second
// even if the tab closes.
function newFetchJob(storageServiceId) {
  setFetchButtonDisabled(true);
  var url = new URL(
    `aggregator/new_fetch_job/${storageServiceId}`,
    $("body").data("url-root"),
  );

  $.ajax({
    type: "POST",
    url: url,
    datatype: "json",

    success: function (data) {
      $("#console").css("background-color", "#000");

      consolePrepend(`Fetch job started ${data["timestamp"]}`);
      consoleAppend("Downloading package lists");

      packageListTaskStatus(data["taskId"], false, data["fetchJobId"]);
    },

    error: function (response) {
      setFetchButtonDisabled(false);
      if (response.hasOwnProperty("responseJSON")) {
        alert(response.responseJSON["message"]);
      } else {
        alert("Storage Service connection error. Check URL and credentials.");
      }
    },
  });
}

function packageListTaskStatus(taskId, showcount, fetchJobId) {
  const statusPending = "PENDING";
  const statusProgress = "IN PROGRESS";

  var url = new URL(
    `aggregator/package_list_task_status/${taskId}`,
    $("body").data("url-root"),
  );

  $.ajax({
    type: "GET",
    url: url,
    datatype: "json",

    success: function (data) {
      let state = data["state"];
      if (state != statusPending && state != statusProgress) {
        consoleAppend("Downloading AIP METS files");

        getMetsTaskStatus(data["coordinatorId"], 0, fetchJobId);
      } else {
        if (showcount == false) {
          if ("message" in data) {
            consoleAppend(data["message"]);
            showcount = true;
          }
        }

        // Re-run in 1 seconds
        setTimeout(function () {
          packageListTaskStatus(taskId, showcount, fetchJobId);
        }, 1000);
      }
    },

    error: function () {
      setFetchButtonDisabled(false);
      alert("Unexpected error");
    },
  });
}

function getMetsTaskStatus(coordinatorId, totalAIPs, fetchJobId) {
  var url = new URL(
    `aggregator/get_mets_task_status/${coordinatorId}`,
    $("body").data("url-root"),
  );

  $.ajax({
    type: "GET",
    url: url,
    data: { totalAIPs: totalAIPs, fetchJobId: fetchJobId },
    datatype: "json",

    success: function (data) {
      if (data["state"] == "PENDING") {
        setTimeout(function () {
          getMetsTaskStatus(coordinatorId, totalAIPs, fetchJobId);
        }, 1000);
      } else if (data["state"] == "COMPLETED") {
        consoleAppend("METS download completed");
        setTimeout(function () {
          indexStart(fetchJobId);
        }, 3000);
      } else {
        for (var i = 0; i < data.length; i++) {
          var item = data[i];
          consoleAppend(
            `${item["state"]} parsing ${item["totalAIPs"]}. ${item["package"]}`,
          );

          if (i == data.length - 1) {
            totalAIPs = data[i]["totalAIPs"];
          }
        }
        setTimeout(function () {
          getMetsTaskStatus(coordinatorId, totalAIPs, fetchJobId);
        }, 1000);
      }
    },

    error: function () {
      setFetchButtonDisabled(false);
      alert("Unexpected error");
    },
  });
}

function indexStart(fetchJobId) {
  var url = new URL(
    `aggregator/index_refresh/${fetchJobId}`,
    $("body").data("url-root"),
  );

  $.ajax({
    type: "GET",
    url: url,
    data: { fetchJobId: fetchJobId },
    datatype: "json",

    success: function (data) {
      indexRefreshStatus(fetchJobId);
    },

    error: function (data) {
      setFetchButtonDisabled(false);
      if (data.status == 422) {
        // Fetching is complete and indexing isn't needed
        setTimeout(function () {
          location.reload(true);
        }, 3000);
      } else {
        alert("Unexpected error");
      }
    },
  });
}

function indexRefreshStatus(fetchJobId) {
  var url = new URL(
    `aggregator/indexing_status/${fetchJobId}`,
    $("body").data("url-root"),
  );

  $.ajax({
    type: "GET",
    url: url,
    data: { fetchJobId: fetchJobId },
    datatype: "json",

    success: function (data) {
      if (data["state"] == "PENDING") {
        if (data["progress"] !== null) {
          consoleAppend(data["progress"]);
        }

        setTimeout(function () {
          indexRefreshStatus(fetchJobId);
        }, 1000);
      } else if (data["state"] == "COMPLETED") {
        consoleAppend("Indexing completed");
        setFetchButtonDisabled(false);
        setTimeout(function () {
          location.reload(true);
        }, 3000);
      }
    },

    error: function () {
      setFetchButtonDisabled(false);
      alert("Unexpected error");
    },
  });
}

var scriptElement = document.currentScript;

$(document).ready(function () {
  fetchButton = $("#newfetchjob");
  var storageServiceId = $(scriptElement).data("storage-service-id");
  var storageServiceApiKey = $(scriptElement).data("storage-service-api-key");

  $("#newfetchjob").on("click", function () {
    newFetchJob(storageServiceId);
  });

  $(".stats").hide();

  $(".fa-circle-info").click(function () {
    $(`#stats-${this.id}`).toggle();
  });

  // Handle API key visibility
  let apiKeyVisible = false;
  let apiKeyHiddenText = "&bull;".repeat(16);

  $("#apikeyBtn").on("click", function () {
    apiKeyVisible = !apiKeyVisible;
    if (apiKeyVisible === true) {
      $("#apikey").text(storageServiceApiKey);
    } else {
      $("#apikey").html(apiKeyHiddenText);
    }
  });
});
