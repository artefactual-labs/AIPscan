import pytest
from flask import current_app

EXPECTED_CSV = b"AIP UUID,AIP Name,UUID,Name,Format,Original UUID,Original Name,Original Format,Original Version,Original PUID\r\n111111111111-1111-1111-11111111,TestAIP1,555555555555-5555-5555-55555555,preservation-file-1.tif,Tagged Image File Format,333333333333-3333-3333-33333333,original-file-1.jpg,JPEG,1.01,fmt/43\r\n222222222222-2222-2222-22222222,TestAIP2,666666666666-6666-6666-66666666,preservation-file-2.tif,Tagged Image File Format,444444444444-4444-4444-44444444,original-file-2.jpg,JPEG,1.02,fmt/44\r\n"
EXPECTED_CSV_FILTERED = b"AIP UUID,AIP Name,UUID,Name,Format,Original UUID,Original Name,Original Format,Original Version,Original PUID\r\n111111111111-1111-1111-11111111,TestAIP1,555555555555-5555-5555-55555555,preservation-file-1.tif,Tagged Image File Format,333333333333-3333-3333-33333333,original-file-1.jpg,JPEG,1.01,fmt/43\r\n"


def test_preservation_derivatives(aip_contents):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/preservation_derivatives/?amss_id=1")
        assert response.status_code == 200


@pytest.mark.parametrize(
    "aip_uuid,expected_csv_contents",
    [
        # No AIP UUID returns all results.
        ("", EXPECTED_CSV),
        # Specifying an AIP UUID filters results to that AIP.
        ("111111111111-1111-1111-11111111", EXPECTED_CSV_FILTERED),
    ],
)
def test_preservation_derivatives_csv(
    preservation_derivatives, aip_uuid, expected_csv_contents
):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            f"/reporter/preservation_derivatives/?amss_id=1&aip_uuid={aip_uuid}&csv=True"
        )
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=preservation_derivatives.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == expected_csv_contents
