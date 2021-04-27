from flask import current_app

EXPECTED_CSV_CONTENTS = b"UUID,AIP Name,Created Date,AIP Size,fmt/43,fmt/61,x-fmt/111\r\n111111111111-1111-1111-11111111,Test AIP,2020-01-01 00:00:00,0 Bytes,1,1,0\r\n222222222222-2222-2222-22222222,Test AIP,2020-06-01 00:00:00,0 Bytes,0,2,3\r\n"


def test_aip_contents(aip_contents):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/aip_contents/?amss_id=1")
        assert response.status_code == 200


def test_aip_contents_csv(aip_contents):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/aip_contents/?amss_id=1&csv=True")
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=aip_contents.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS
