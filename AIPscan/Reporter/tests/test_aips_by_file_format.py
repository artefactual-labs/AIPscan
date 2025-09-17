import pytest
from flask import current_app

EXPECTED_CSV_ORIGINAL = b"AIP Name,UUID,Count,Size,Size (bytes)\r\nTest AIP,111111111111-1111-1111-11111111,1,1.0 kB,1000\r\n"
EXPECTED_CSV_PRESERVATION = b"AIP Name,UUID,Count,Size,Size (bytes)\r\nTest AIP,111111111111-1111-1111-11111111,1,2.0 kB,2000\r\n"


@pytest.mark.parametrize(
    "original_files",
    [
        # Original files.
        ("True"),
        # Preservation files.
        ("False"),
    ],
)
def test_aips_by_file_format(app_with_populated_files, original_files):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            f"/reporter/aips_by_file_format/?amss_id=1&file_format=Tagged Image File Format&original_files={original_files}"
        )
        assert response.status_code == 200


@pytest.mark.parametrize(
    "original_files,expected_csv",
    [
        # Original files.
        ("True", EXPECTED_CSV_ORIGINAL),
        # Preservation files.
        ("False", EXPECTED_CSV_PRESERVATION),
    ],
)
def test_aips_by_file_format_csv(
    app_with_populated_files, original_files, expected_csv
):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            f"/reporter/aips_by_file_format/?amss_id=1&file_format=Tagged Image File Format&original_files={original_files}&csv=True"
        )
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=aips_by_file_format_Tagged Image File Format.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == expected_csv
