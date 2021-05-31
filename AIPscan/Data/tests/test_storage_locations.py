import pytest

from AIPscan.conftest import (
    STORAGE_LOCATION_1_DESCRIPTION,
    STORAGE_LOCATION_1_UUID,
    STORAGE_LOCATION_2_DESCRIPTION,
    STORAGE_LOCATION_2_UUID,
)
from AIPscan.Data import fields, report_data

ORDERED_LIST = [{fields.FIELD_AIPS: 8}, {fields.FIELD_AIPS: 3}]
UNORDERED_LIST = [{fields.FIELD_AIPS: 3}, {fields.FIELD_AIPS: 8}]

DATE_BEFORE_AIP_1 = "2019-01-01"
DATE_AFTER_AIP_1 = "2020-01-02"
DATE_BEFORE_AIP_2 = "2020-05-30"
DATE_AFTER_AIP_2 = "2020-06-02"
DATE_BEFORE_AIP_3 = "2021-05-30"
DATE_AFTER_AIP_3 = "2021-06-01"


@pytest.mark.parametrize(
    "input_list, expected_output",
    [
        # Test that out-of-order list is sorted.
        (UNORDERED_LIST, ORDERED_LIST),
        # Test that list already in desired order is kept as-is.
        (ORDERED_LIST, ORDERED_LIST),
        # Test empty list.
        ([], []),
    ],
)
def test_sort_storage_locations(input_list, expected_output):
    assert report_data._sort_storage_locations(input_list) == expected_output


@pytest.mark.parametrize(
    "storage_service_id, storage_service_name, start_date, end_date, locations_count, location_1_aips_count, location_1_total_size, location_2_aips_count, location_2_total_size",
    [
        # Request for a Storage Service populated with two locations, each
        # containing AIPs and files.
        (
            1,
            "test storage service",
            DATE_BEFORE_AIP_1,
            DATE_AFTER_AIP_3,
            2,
            2,
            1600,
            1,
            5000,
        ),
        # Request for a non-existent Storage Service.
        (4, None, DATE_BEFORE_AIP_1, DATE_BEFORE_AIP_3, 0, 0, 0, 0, 0),
        # Request for a None Storage Service.
        (None, None, DATE_BEFORE_AIP_1, DATE_BEFORE_AIP_3, 0, 0, 0, 0, 0),
        # Test date filtering.
        (
            1,
            "test storage service",
            DATE_AFTER_AIP_1,
            DATE_AFTER_AIP_2,
            2,
            1,
            1000,
            0,
            0,
        ),
        (
            1,
            "test storage service",
            DATE_BEFORE_AIP_1,
            DATE_BEFORE_AIP_2,
            2,
            1,
            600,
            0,
            0,
        ),
        (
            1,
            "test storage service",
            DATE_BEFORE_AIP_1,
            DATE_BEFORE_AIP_3,
            2,
            2,
            1600,
            0,
            0,
        ),
        (
            1,
            "test storage service",
            DATE_AFTER_AIP_2,
            DATE_AFTER_AIP_3,
            2,
            0,
            0,
            1,
            5000,
        ),
    ],
)
def test_storage_locations_data(
    storage_locations,
    storage_service_id,
    storage_service_name,
    start_date,
    end_date,
    locations_count,
    location_1_aips_count,
    location_1_total_size,
    location_2_aips_count,
    location_2_total_size,
):
    """Test response from report_data.storage_locations endpoint."""
    report = report_data.storage_locations(
        storage_service_id=storage_service_id, start_date=start_date, end_date=end_date
    )

    assert report[fields.FIELD_STORAGE_NAME] == storage_service_name

    locations = report[fields.FIELD_LOCATIONS]
    assert len(locations) == locations_count

    if locations_count < 1:
        return

    first_location = locations[0]
    # Account for sorting changes made possible by date filtering.
    if location_1_aips_count > location_2_aips_count:
        assert first_location[fields.FIELD_UUID] == STORAGE_LOCATION_1_UUID
        assert (
            first_location[fields.FIELD_STORAGE_LOCATION]
            == STORAGE_LOCATION_1_DESCRIPTION
        )
        assert first_location[fields.FIELD_AIPS] == location_1_aips_count
        assert first_location[fields.FIELD_SIZE] == location_1_total_size
    else:
        assert first_location[fields.FIELD_UUID] == STORAGE_LOCATION_2_UUID
        assert (
            first_location[fields.FIELD_STORAGE_LOCATION]
            == STORAGE_LOCATION_2_DESCRIPTION
        )
        assert first_location[fields.FIELD_AIPS] == location_2_aips_count
        assert first_location[fields.FIELD_SIZE] == location_2_total_size

    second_location = locations[1]
    # Account for sorting changes made possible by date filtering.
    if location_1_aips_count > location_2_aips_count:
        assert second_location[fields.FIELD_UUID] == STORAGE_LOCATION_2_UUID
        assert (
            second_location[fields.FIELD_STORAGE_LOCATION]
            == STORAGE_LOCATION_2_DESCRIPTION
        )
        assert second_location[fields.FIELD_AIPS] == location_2_aips_count
        assert second_location[fields.FIELD_SIZE] == location_2_total_size
    else:
        assert second_location[fields.FIELD_UUID] == STORAGE_LOCATION_1_UUID
        assert (
            second_location[fields.FIELD_STORAGE_LOCATION]
            == STORAGE_LOCATION_1_DESCRIPTION
        )
        assert second_location[fields.FIELD_AIPS] == location_1_aips_count
        assert second_location[fields.FIELD_SIZE] == location_1_total_size
