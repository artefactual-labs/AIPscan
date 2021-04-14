$(document).ready(function() {
  
  // Download CSV version of current report
  $('#downloadCSV').on('click', function() {
    window.location.href = window.location.href + '&csv=True';
  });

});
