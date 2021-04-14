import csv

from AIPscan.Data import fields
from AIPscan.Data.report_data import aips_by_file_format
from AIPscan.Data.tests import (
    MOCK_AIPS_BY_FORMAT_OR_PUID_QUERY_RESULTS as QUERY_RESULTS,
)
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE as STORAGE_SERVICE
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_ID as STORAGE_SERVICE_ID
from AIPscan.Reporter import helpers
from AIPscan.Reporter.report_aips_by_format import HEADERS


def test_download_csv(app_instance, mocker):
    """Test downloading report data as CSV."""
    CSV_FILE = "test.csv"
    CONTENT_DISPOSITION = "attachment; filename={}".format(CSV_FILE)
    CSV_MIMETYPE = "text/csv"

    query_results = QUERY_RESULTS[:2]

    mock_query = mocker.patch(
        "AIPscan.Data.report_data._query_aips_by_file_format_or_puid"
    )
    mock_query.return_value = query_results
    mock_get_ss = mocker.patch("AIPscan.Data.report_data._get_storage_service")
    mock_get_ss.return_value = STORAGE_SERVICE

    headers = helpers.translate_headers(HEADERS)

    report_data = aips_by_file_format(STORAGE_SERVICE_ID, "test")
    response = helpers.download_csv(headers, report_data[fields.FIELD_AIPS], CSV_FILE)

    # Assert response is shaped as we expect.
    assert response is not None
    assert response.headers["Content-Disposition"] == CONTENT_DISPOSITION
    assert response.mimetype == CSV_MIMETYPE

    # Assert that content of CSV file is what we expect.
    content = response.get_data().decode()
    reader = csv.reader(content.splitlines())
    line_count = 0
    for row in reader:
        if line_count == 0:
            assert row == headers
        elif line_count == 1:
            assert row[0] == "aip0"
            assert row[1] == "11111111-1111-1111-1111-111111111111"
            assert row[2] == "5"
            assert row[3] == "12345678"
        else:
            assert row[0] == "aip1"
            assert row[1] == "22222222-2222-2222-2222-222222222222"
            assert row[2] == "3"
            assert row[3] == "123456"
        line_count += 1
    assert line_count == len(query_results) + 1
