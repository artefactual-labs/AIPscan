from datetime import datetime

import pytest

from AIPscan.conftest import STORAGE_LOCATION_1_DESCRIPTION
from AIPscan.conftest import STORAGE_LOCATION_1_UUID
from AIPscan.conftest import STORAGE_LOCATION_2_DESCRIPTION
from AIPscan.conftest import STORAGE_LOCATION_2_UUID
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_datetime_bound

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
    "storage_service_id, storage_service_name, start_date, end_date, locations_count, location_1_aips_count, location_1_total_size, location_1_file_count, location_2_aips_count, location_2_total_size, location_2_file_count",
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
            3,
            1,
            5000,
            2,
        ),
        # Request for a non-existent Storage Service.
        (4, None, DATE_BEFORE_AIP_1, DATE_BEFORE_AIP_3, 0, 0, 0, 0, 0, 0, 0),
        # Request for a None Storage Service.
        (None, None, DATE_BEFORE_AIP_1, DATE_BEFORE_AIP_3, 0, 0, 0, 0, 0, 0, 0),
        # Test date filtering.
        (
            1,
            "test storage service",
            DATE_AFTER_AIP_1,
            DATE_AFTER_AIP_2,
            2,
            1,
            1000,
            1,
            0,
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
            2,
            0,
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
            3,
            0,
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
            0,
            1,
            5000,
            2,
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
    location_1_file_count,
    location_2_aips_count,
    location_2_total_size,
    location_2_file_count,
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
        assert first_location[fields.FIELD_FILE_COUNT] == location_1_file_count
    else:
        assert first_location[fields.FIELD_UUID] == STORAGE_LOCATION_2_UUID
        assert (
            first_location[fields.FIELD_STORAGE_LOCATION]
            == STORAGE_LOCATION_2_DESCRIPTION
        )
        assert first_location[fields.FIELD_AIPS] == location_2_aips_count
        assert first_location[fields.FIELD_SIZE] == location_2_total_size
        assert first_location[fields.FIELD_FILE_COUNT] == location_2_file_count

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
        assert second_location[fields.FIELD_FILE_COUNT] == location_2_file_count
    else:
        assert second_location[fields.FIELD_UUID] == STORAGE_LOCATION_1_UUID
        assert (
            second_location[fields.FIELD_STORAGE_LOCATION]
            == STORAGE_LOCATION_1_DESCRIPTION
        )
        assert second_location[fields.FIELD_AIPS] == location_1_aips_count
        assert second_location[fields.FIELD_SIZE] == location_1_total_size
        assert second_location[fields.FIELD_FILE_COUNT] == location_1_file_count


@pytest.mark.parametrize(
    "start_date, end_date, expected_output",
    [
        # Test span within month.
        (
            "2022-01-01",
            "2022-01-04",
            ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"],
        ),
        # Test span across months.
        (
            "2022-02-27",
            "2022-03-02",
            ["2022-02-27", "2022-02-28", "2022-03-01", "2022-03-02"],
        ),
        # Test what happens if end is before start.
        ("2022-06-01", "2022-05-01", []),
        # Test that datetime.min is replaced by earliest AIP created date
        (datetime.min, "2020-01-03", ["2020-01-01", "2020-01-02", "2020-01-03"]),
        # Test that datetime.max is replaced by datetime.now()
        (
            datetime.now().isoformat()[:10],
            datetime.max,
            [datetime.now().isoformat()[:10]],
        ),
    ],
)
def test_get_days_covered_by_date_range(
    storage_locations, start_date, end_date, expected_output
):
    if start_date != datetime.min:
        start_date = parse_datetime_bound(start_date)
    if end_date != datetime.max:
        end_date = parse_datetime_bound(end_date)
    assert (
        report_data._get_days_covered_by_date_range(1, start_date, end_date)
        == expected_output
    )


@pytest.mark.parametrize(
    "cumulative",
    [
        # Differential totals
        (False),
        # Cumulative totals
        (True),
    ],
)
def test_storage_locations_usage_over_time(storage_locations, cumulative):
    """Test response from report_data.storage_locations_usage_over_time endpoint."""
    report = report_data.storage_locations_usage_over_time(
        storage_service_id=1,
        start_date=parse_datetime_bound(DATE_BEFORE_AIP_1),
        end_date=parse_datetime_bound(DATE_AFTER_AIP_3, upper=True),
        cumulative=cumulative,
    )

    assert report[fields.FIELD_STORAGE_NAME] == "test storage service"

    locations = report[fields.FIELD_LOCATIONS_USAGE_OVER_TIME]

    # Assert that every day between Jan 1, 2020 and June 1, 2021, inclusive, is
    # accounted for.
    assert len(locations) == 884

    first_day = locations["2020-01-01"]

    # Test that we have data for both storage locations.
    assert len(first_day) == 2

    # Test correctness of that data.
    first_location = first_day[0]
    assert first_location[fields.FIELD_AIPS] == 1
    assert first_location[fields.FIELD_SIZE] == 600
    assert first_location[fields.FIELD_FILE_COUNT] == 2

    second_location = first_day[1]
    assert second_location[fields.FIELD_AIPS] == 0
    assert second_location[fields.FIELD_SIZE] == 0
    assert second_location[fields.FIELD_FILE_COUNT] == 0

    last_day = locations["2021-06-01"]

    # Test that we have data for both storage locations.
    assert len(last_day) == 2

    if cumulative:
        # All AIPs in fixture should be accounted for.
        first_location = last_day[0]
        assert first_location[fields.FIELD_AIPS] == 2
        assert first_location[fields.FIELD_SIZE] == 1600
        assert first_location[fields.FIELD_FILE_COUNT] == 3

        second_location = last_day[1]
        assert second_location[fields.FIELD_AIPS] == 1
        assert second_location[fields.FIELD_SIZE] == 5000
        assert second_location[fields.FIELD_FILE_COUNT] == 2
    else:
        # Data should reflect no ingests this day.
        first_location = last_day[0]
        assert first_location[fields.FIELD_AIPS] == 0
        assert first_location[fields.FIELD_SIZE] == 0
        assert first_location[fields.FIELD_FILE_COUNT] == 0

        second_location = last_day[1]
        assert second_location[fields.FIELD_AIPS] == 0
        assert second_location[fields.FIELD_SIZE] == 0
        assert second_location[fields.FIELD_FILE_COUNT] == 0
