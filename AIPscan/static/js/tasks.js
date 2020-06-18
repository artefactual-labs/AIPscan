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
      task_status(data["taskId"], showcount);
      },
    error: function() {
      alert('Unexpected error');
      }
  });
}

function task_status(taskId, showcount){
  $.ajax({
    type: 'GET',
    url: '/aggregator/task_status/' + taskId,
    datatype: "json",
    success: function(data) {
      if (data['state'] != 'PENDING' && data['state'] != 'IN PROGRESS') {
        $('#console').append('<div class="log">' + data["state"] +'</div>')
        $('#console').append('<div class="log">Downloading AIP METS files</div>')
        get_mets_task_status(data["coordinatorId"]);
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
        setTimeout(function() {task_status(taskId, showcount);}, 1000);
      }
    },
    error: function() {
      alert('Unexpected error');
      }
  });
}

function get_mets_task_status(coordinatorId){
  $.ajax({
    type: 'GET',
    url: '/aggregator/get_mets_task_status/' + coordinatorId,
    datatype: "json",
    success: function(data) {
      if (data['state'] != 'PENDING' && data['state'] != 'IN PROGRESS') {
        $('#console').append('<div class="log">' + data["state"] +'</div>')
      }
      else {
        $('#console').append('<div class="log">' + data['state'] + '</div>')
        if ('message' in data){
          $('#console').append('<div class="log">' + data["message"] +'</div>')
        }
        // rerun in 1 seconds
        setTimeout(function() {get_mets_task_status(coordinatorId);}, 1000);
      }
    },
    error: function() {
      alert('Unexpected error');
      }
  });
}
