import os

import pytest
from flask import current_app

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")

EXPECTED_CSV_CONTENTS = b"UUID,Location,AIPs,Size,Size (bytes),File Count\r\n2bbcea40-eb4d-4076-a81d-1ab046e34f6a,AIP Store Location 1,2,1.6 kB,1600,3\r\ne69beb57-0e32-4c45-8db7-9b7723724a05,AIP Store Location 2,1,5.0 kB,5000,2\r\n"


def test_storage_locations(storage_locations):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/storage_locations/?amss_id=1")
        assert response.status_code == 200


def test_storage_locations_csv(storage_locations):
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


def test_storage_locations_usage_over_time(storage_locations):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            "/reporter/storage_locations_usage_over_time/?amss_id=1"
        )
        assert response.status_code == 200


@pytest.mark.parametrize(
    "metric, cumulative, fixture",
    [
        # Differential totals
        ("aips", False, "storage_location_usage_differential_aips.csv"),
        ("size", False, "storage_location_usage_differential_size.csv"),
        ("files", False, "storage_location_usage_differential_files.csv"),
        # Cumulative totals
        ("aips", True, "storage_location_usage_cumulative_aips.csv"),
        ("size", True, "storage_location_usage_cumulative_size.csv"),
        ("files", True, "storage_location_usage_cumulative_files.csv"),
    ],
)
def test_storage_locations_usage_over_time_csv(
    storage_locations, metric, cumulative, fixture
):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            f"/reporter/storage_locations_usage_over_time/?amss_id=1&csv=True&start_date=2020-01-01&end_date=2020-06-30&metric={metric}&cumulative={cumulative}"
        )
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=storage_locations_usage_over_time.csv"
        )
        assert response.mimetype == "text/csv"

        csv_fixture_path = os.path.join(FIXTURES_DIR, fixture)
        with open(csv_fixture_path, "rb") as csv_file:
            assert response.data == csv_file.read()
