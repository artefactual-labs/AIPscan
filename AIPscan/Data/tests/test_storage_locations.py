import pytest

from AIPscan.conftest import (
    STORAGE_LOCATION_1_DESCRIPTION,
    STORAGE_LOCATION_1_UUID,
    STORAGE_LOCATION_2_DESCRIPTION,
    STORAGE_LOCATION_2_UUID,
)
from AIPscan.Data import fields, report_data

UNORDERED_LIST = [{fields.FIELD_AIPS: 3}, {fields.FIELD_AIPS: 8}]

ORDERED_LIST = [{fields.FIELD_AIPS: 8}, {fields.FIELD_AIPS: 3}]


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
    "storage_service_id, storage_service_name, locations_count",
    [
        # Request for a Storage Service populated with two locations, each
        # containing AIPs and files.
        (1, "test storage service", 2),
        # Request for a non-existent Storage Service.
        (4, None, 0),
        # Request for a None Storage Service.
        (None, None, 0),
    ],
)
def test_storage_locations_data(
    storage_locations, storage_service_id, storage_service_name, locations_count
):
    """Test response from report_data.storage_locations endpoint."""
    report = report_data.storage_locations(storage_service_id=storage_service_id)

    assert report[fields.FIELD_STORAGE_NAME] == storage_service_name

    locations = report[fields.FIELD_LOCATIONS]
    assert len(locations) == locations_count

    if locations_count < 1:
        return

    first_location = locations[0]
    assert first_location[fields.FIELD_UUID] == STORAGE_LOCATION_1_UUID
    assert (
        first_location[fields.FIELD_STORAGE_LOCATION] == STORAGE_LOCATION_1_DESCRIPTION
    )
    assert first_location[fields.FIELD_AIPS] == 2
    assert first_location[fields.FIELD_SIZE] == 1600

    second_location = locations[1]
    assert second_location[fields.FIELD_UUID] == STORAGE_LOCATION_2_UUID
    assert (
        second_location[fields.FIELD_STORAGE_LOCATION] == STORAGE_LOCATION_2_DESCRIPTION
    )
    assert second_location[fields.FIELD_AIPS] == 1
    assert second_location[fields.FIELD_SIZE] == 5000
