function new_fetch_job(storageServiceId){
  $.ajax({
    type: 'POST',
    url: '/aggregator/new_fetch_job/' + storageServiceId,
    datatype: "json",
    success: function(data) {
      $('#console').css('background-color', '#000');
      $('#console').prepend('<div class="log">Fetch job started ' + data["timestamp"] + '</div>');
      $('#console').append('<div class="log">Downloading package lists</div>')
      var showcount = false
      package_list_task_status(data["taskId"], showcount, data["fetchJobId"]);
      },
    error: function() {
      alert('Unexpected error');
      }
  });
}

function package_list_task_status(taskId, showcount, fetchJobId){
  $.ajax({
    type: 'GET',
    url: '/aggregator/package_list_task_status/' + taskId,
    datatype: "json",
    success: function(data) {
      if (data['state'] != 'PENDING' && data['state'] != 'IN PROGRESS') {
        $('#console').append('<div class="log">' + data["state"] +'</div>')
        $('#console').append('<div class="log">Downloading AIP METS files</div>')
        get_mets_task_status(data["coordinatorId"], 0, fetchJobId);
      }
      else {
        if (showcount == false) {
          if ('message' in data){
            $('#console').append('<div class="log">' + data["message"] +'</div>')
            showcount = true
          }
        }
        $('#console').append('<div class="log">' + data['state'] + '</div>')
        // rerun in 1 seconds
        setTimeout(function() {package_list_task_status(taskId, showcount, fetchJobId);}, 1000);
      }
    },
    error: function() {
      alert('Unexpected error');
      }
  });
}

function get_mets_task_status(coordinatorId, totalAIPs, fetchJobId){
  $.ajax({
    type: 'GET',
    url: '/aggregator/get_mets_task_status/' + coordinatorId,
    data: {"totalAIPs" : totalAIPs, "fetchJobId": fetchJobId},
    datatype: "json",
    success: function(data) {
      if (data['state'] == "PENDING")  {
        setTimeout(function() {get_mets_task_status(coordinatorId, totalAIPs, fetchJobId)}, 1000)
      }
      else if (data['state'] == "COMPLETED")
        {
          $('#console').append('<div class="log">METS download completed</div>')
          location.reload(true);
        }
      else {
        for(var i = 0; i < data.length; i++){
          $('#console').append('<div class="log">' + data[i]['state'] + ' parsing ' + data[i]['totalAIPs'] + '. ' + data[i]['package'] + '</div>')
          if (i == data.length - 1){
            totalAIPs = data[i]['totalAIPs']
          }
        }
        setTimeout(function() {get_mets_task_status(coordinatorId, totalAIPs, fetchJobId)}, 1000)
      }
    },
    error: function() {
      alert('Unexpected error');
      }
  });
}
