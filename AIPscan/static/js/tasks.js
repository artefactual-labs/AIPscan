function newfetchjob(id){
  $.ajax({
    type: 'GET',
    url: '/aggregator/new_fetch_job/' + id,
    success: function() {
      alert("success")
      },
    error: function() {
      alert('Unexpected error');
      }
  });
}
