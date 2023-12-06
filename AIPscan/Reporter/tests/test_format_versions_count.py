from flask import current_app

EXPECTED_CSV_CONTENTS = b"PUID,Format,Version,Count,Size,Size (bytes)\r\nfmt/44,JPEG,1.02,1,2.0 kB,2000\r\nfmt/43,JPEG,1.01,1,1.0 kB,1000\r\nfmt/468,ISO Disk Image File,,1,0 Bytes,0\r\n"


def test_format_versions_count(app_with_populated_format_versions):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/report_format_versions_count/?amss_id=1")
        assert response.status_code == 200


def test_format_versions_count_csv(app_with_populated_format_versions):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            "/reporter/report_format_versions_count/?amss_id=1&csv=True"
        )
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=format_versions.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS
