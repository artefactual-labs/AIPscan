from flask import current_app

EXPECTED_CSV_CONTENTS = b"UUID,Location,AIPs,Size\r\n2bbcea40-eb4d-4076-a81d-1ab046e34f6a,AIP Store Location 1,2,1.6 kB\r\ne69beb57-0e32-4c45-8db7-9b7723724a05,AIP Store Location 2,1,5.0 kB\r\n"


def test_storage_locations(storage_locations):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/storage_locations/?amss_id=1")
        assert response.status_code == 200


def test_formats_count_csv(storage_locations):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/storage_locations/?amss_id=1&csv=True")
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=storage_locations.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS
