import pytest
from flask import current_app
from flask import url_for

from AIPscan import typesense_test_helpers

EXPECTED_CSV_CONTENTS = b"Format,Count,Size,Size (bytes)\r\nJPEG,2,3.0 kB,3000\r\nISO Disk Image File,1,0 Bytes,0\r\n"


@pytest.mark.parametrize(
    "view, url_params",
    [
        ("reporter.report_formats_count", {"amss_id": "1"}),
        (
            "reporter.chart_formats_count",
            {
                "start_date": "2019-01-30",
                "end_date": "2024-02-26",
                "amss_id": 1,
                "storage_location": "",
            },
        ),
        (
            "reporter.plot_formats_count",
            {
                "start_date": "2019-01-30",
                "end_date": "2024-02-26",
                "amss_id": "1",
                "storage_location": "",
            },
        ),
    ],
)
def test_formats_count_reports(app_with_populated_format_versions, view, url_params):
    """Test that report template renders."""
    with current_app.test_request_context():
        url_path_and_params = url_for(view, **url_params)

    with current_app.test_client() as test_client:
        response = test_client.get(url_path_and_params)
        assert response.status_code == 200


@pytest.mark.parametrize(
    "view, url_params",
    [
        ("reporter.report_formats_count", {"amss_id": 1}),
        (
            "reporter.chart_formats_count",
            {
                "start_date": "2019-01-30",
                "end_date": "2024-02-26",
                "amss_id": "1",
                "storage_location": "",
            },
        ),
        (
            "reporter.plot_formats_count",
            {
                "start_date": "2019-01-30",
                "end_date": "2024-02-26",
                "amss_id": "1",
                "storage_location": "",
            },
        ),
    ],
)
def test_formats_count_reports_using_typesense(
    app_with_populated_format_versions, enable_typesense, mocker, view, url_params
):
    """Test that report template renders."""
    with current_app.test_request_context():
        url_path_and_params = url_for(view, **url_params)

    with current_app.test_client() as test_client:
        typesense_test_helpers.fake_collection_format_counts(mocker)

        response = test_client.get(url_path_and_params)
        assert response.status_code == 200


def test_formats_count_csv(app_with_populated_format_versions):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/report_formats_count/?amss_id=1&csv=True")
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=file_formats.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS
