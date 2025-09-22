import pytest

from AIPscan import db
from AIPscan import typesense_helpers
from AIPscan import typesense_test_helpers
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.Data import report_data_typesense
from AIPscan.helpers import parse_datetime_bound
from AIPscan.models import AIP


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


def test_largest_aips_typesense(app_with_populated_files, enable_typesense, mocker):
    doc = typesense_helpers.model_instance_to_document(AIP, db.session.get(AIP, 1))
    fake_results = {"hits": [{"document": doc}]}

    typesense_test_helpers.fake_collection(mocker, fake_results)

    expected_result = {
        "AIPs": [
            {
                "UUID": "111111111111-1111-1111-11111111",
                "Name": "Test AIP",
                "Size": 100,
                "FileCount": 1,
            }
        ],
        "StorageName": "test storage service",
        "StorageLocation": "test storage location",
    }

    report = report_data_typesense.largest_aips(
        storage_service_id=1,
        start_date=parse_datetime_bound("2019-01-01"),
        end_date=parse_datetime_bound("2019-10-10"),
        storage_location_id=1,
    )

    assert report == expected_result
