from flask import current_app

EXPECTED_CSV_CONTENTS = b"UUID,Filename,Size,Size (bytes),Type,Format,Version,PUID,AIP Name,AIP UUID\r\n555555555555-5555-5555-55555555,preservation.jpg,2.0 kB,2000,original,JPEG,1.02,fmt/44,Test AIP,222222222222-2222-2222-22222222\r\n333333333333-3333-3333-33333333,original.jpg,1.0 kB,1000,original,JPEG,1.01,fmt/43,Test AIP,111111111111-1111-1111-11111111\r\n444444444444-4444-4444-44444444,original.iso,0 Bytes,0,original,ISO Disk Image File,,fmt/468,Test AIP,222222222222-2222-2222-22222222\r\n"


def test_largest_files(app_with_populated_format_versions):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/largest_files/?amss_id=1")
        assert response.status_code == 200


def test_largest_files_csv(app_with_populated_format_versions):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/largest_files/?amss_id=1&csv=True")
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=largest_files.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS
