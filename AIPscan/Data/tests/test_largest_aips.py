import pytest

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_datetime_bound


@pytest.mark.parametrize(
    "storage_location_id, storage_location_description, start_date, end_date, aip_count,largest_aip_size,second_largest_aip_size",
    [
        # Test all AIPs.
        (None, None, "2020-01-01", "2022-12-31", 5, 10000, 750),
        # Test filtering by date.
        (None, None, "2020-01-01", "2020-06-01", 2, 10000, 250),
        # Test filtering by storage location.
        (1, "storage location 1", "2020-01-01", "2022-12-31", 2, 10000, 250),
        (2, "storage location 2", "2020-01-01", "2022-12-31", 3, 750, 500),
    ],
)
def test_largest_aips(
    largest_aips,
    storage_location_id,
    storage_location_description,
    start_date,
    end_date,
    aip_count,
    largest_aip_size,
    second_largest_aip_size,
):
    """Test that outputs of report_data.largest_aips match expectations."""
    report = report_data.largest_aips(
        storage_service_id=1,
        start_date=parse_datetime_bound(start_date),
        end_date=parse_datetime_bound(end_date, upper=True),
        storage_location_id=storage_location_id,
    )
    report_aips = report[fields.FIELD_AIPS]
    assert report[fields.FIELD_STORAGE_NAME] == "test storage service"
    assert report[fields.FIELD_STORAGE_LOCATION] == storage_location_description

    assert len(report_aips) == aip_count
    assert report_aips[0][fields.FIELD_SIZE] == largest_aip_size
    assert report_aips[1][fields.FIELD_SIZE] == second_largest_aip_size
