$(document).ready(function() {
  
  // Download CSV of current report
  $('#downloadCSV').on('click', function() {
    window.location.href = window.location.href + '&csv=True';
  });

  // Reload largest files report on change to file type dropdown
  $("#fileTypeSelector").on("change", function() {
    var fileType = $('#fileTypeSelector').val();
    var storageServiceId = $('#storageServiceID').text();
    var limit = $('#limit').text();
    var url = window.location.origin +
      '/reporter/largest_files?' +
      'amss_id=' +
      storageServiceId +
      '&file_type=' +
      fileType +
      '&limit=' +
      limit;
    window.location.href = url;
  });

});
