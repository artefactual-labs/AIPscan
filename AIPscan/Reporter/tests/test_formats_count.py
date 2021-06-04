from flask import current_app

EXPECTED_CSV_CONTENTS = (
    b"Format,Count,Size\r\nJPEG,2,3.0 kB\r\nISO Disk Image File,1,0 Bytes\r\n"
)


def test_formats_count(app_with_populated_format_versions):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/report_formats_count/?amss_id=1")
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
