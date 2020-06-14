function new_fetch_job(storageServiceId){
  $.ajax({
    type: 'POST',
    url: '/aggregator/new_fetch_job/' + storageServiceId,
    datatype: "json",
    success: function(data) {
      $('#console').css('background-color', '#000');
      $('#console').prepend('<div class="log">Fetch job started ' + data["timestamp"] + '</div>');
      task_status(data["taskId"]);
      },
    error: function() {
      alert('Unexpected error');
      }
  });
}

function task_status(taskId){
  $.ajax({
    type: 'GET',
    url: '/aggregator/task_status/' + taskId,
    datatype: "json",
    success: function(data) {
      if (data['state'] != 'PENDING' && data['state'] != 'IN PROGRESS') {
        $('#console').append('<div class="log">' + data["state"] +'</div>')
      }
      else {
        if (data['state'] == 'IN PROGRESS'){
          $('#console').append('<div class="log">' + data['message'] + '</div>')
          }
        // rerun in 1 seconds
        setTimeout(function() {task_status(taskId);}, 1000);
      }
    },
    error: function() {
      alert('Unexpected error');
      }
  });
}
