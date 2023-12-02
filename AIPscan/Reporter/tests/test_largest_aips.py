from flask import current_app

EXPECTED_CSV_CONTENTS = b"AIP Name,UUID,AIP Size,AIP Size (bytes),File Count\r\nTest AIP,111111111111-1111-1111-11111111,100 Bytes,100,1\r\nTest AIP,222222222222-2222-2222-22222222,100 Bytes,100,2\r\n"


def test_largest_aips(app_with_populated_format_versions):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/largest_aips/?amss_id=1")
        assert response.status_code == 200


def test_largest_aips_csv(app_with_populated_format_versions):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/largest_aips/?amss_id=1&csv=True")
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=largest_aips.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS
