import pytest

from AIPscan.conftest import STORAGE_LOCATION_1_DESCRIPTION
from AIPscan.conftest import STORAGE_LOCATION_2_DESCRIPTION
from AIPscan.Data import data
from AIPscan.Data import fields
from AIPscan.Data.tests import MOCK_STORAGE_SERVICES
from AIPscan.helpers import parse_datetime_bound

DATE_BEFORE_AIP_1 = "2019-01-01"
DATE_AFTER_AIP_1 = "2020-01-02"
DATE_BEFORE_AIP_2 = "2020-05-30"
DATE_AFTER_AIP_2 = "2020-06-02"
DATE_BEFORE_AIP_3 = "2021-05-30"
DATE_AFTER_AIP_3 = "2021-06-01"


TEST_AIP_1_EXPECTED = {
    "AIPName": "TestAIP1",
    "CreatedDate": "2020-01-01 00:00:00",
    "Formats": {
        "fmt/43": {"Count": 1, "Name": "JPEG", "Version": "1.01"},
        "fmt/test-1": {"Count": 1, "Name": "txt", "Version": "0.0.0"},
    },
    "Size": 300,
    "UUID": "111111111111-1111-1111-11111111",
}

TEST_AIP_2_EXPECTED = {
    "AIPName": "TestAIP2",
    "CreatedDate": "2020-06-01 00:00:00",
    "Formats": {"fmt/44": {"Count": 1, "Name": "JPEG", "Version": "1.02"}},
    "Size": 1000,
    "UUID": "222222222222-2222-2222-22222222",
}

TEST_AIP_3_EXPECTED = {
    "AIPName": "TestAIP3",
    "CreatedDate": "2021-05-31 00:00:00",
    "Formats": {
        "fmt/test-1": {"Count": 2, "Name": "ACME File Format", "Version": "0.0.0"}
    },
    "Size": 2500,
    "UUID": "333333333333-3333-3333-33333333",
}


@pytest.mark.parametrize(
    "storage_service_id, storage_service_name, storage_location_id, storage_location_description, start_date, end_date, expected_aips_count, expected_first_aip",
    [
        # Request for a Storage Service populated with two locations, each
        # containing AIPs and files.
        (
            1,
            "test storage service",
            None,
            None,
            DATE_BEFORE_AIP_1,
            DATE_AFTER_AIP_3,
            3,
            TEST_AIP_1_EXPECTED,
        ),
        # Request for a non-existent Storage Service.
        (4, None, None, None, DATE_BEFORE_AIP_1, DATE_BEFORE_AIP_3, 0, None),
        # Request for a None Storage Service.
        (None, None, None, None, DATE_BEFORE_AIP_1, DATE_BEFORE_AIP_3, 0, None),
        # Request with valid Storage Location.
        (
            1,
            "test storage service",
            1,
            STORAGE_LOCATION_1_DESCRIPTION,
            DATE_BEFORE_AIP_1,
            DATE_AFTER_AIP_3,
            2,
            TEST_AIP_1_EXPECTED,
        ),
        (
            1,
            "test storage service",
            2,
            STORAGE_LOCATION_2_DESCRIPTION,
            DATE_BEFORE_AIP_1,
            DATE_AFTER_AIP_3,
            1,
            TEST_AIP_3_EXPECTED,
        ),
        # Request for a non-existent Storage Location.
        (
            1,
            "test storage service",
            4,
            None,
            DATE_BEFORE_AIP_1,
            DATE_BEFORE_AIP_3,
            0,
            None,
        ),
        # Test date filtering.
        (
            1,
            "test storage service",
            None,
            None,
            DATE_AFTER_AIP_1,
            DATE_AFTER_AIP_2,
            1,
            TEST_AIP_2_EXPECTED,
        ),
        (
            1,
            "test storage service",
            None,
            None,
            DATE_BEFORE_AIP_1,
            DATE_BEFORE_AIP_2,
            1,
            TEST_AIP_1_EXPECTED,
        ),
        (
            1,
            "test storage service",
            None,
            None,
            DATE_BEFORE_AIP_1,
            DATE_BEFORE_AIP_3,
            2,
            TEST_AIP_1_EXPECTED,
        ),
        (
            1,
            "test storage service",
            None,
            None,
            DATE_AFTER_AIP_2,
            DATE_AFTER_AIP_3,
            1,
            TEST_AIP_3_EXPECTED,
        ),
    ],
)
def test_aip_contents_data(
    storage_locations,
    storage_service_id,
    storage_service_name,
    storage_location_id,
    storage_location_description,
    start_date,
    end_date,
    expected_aips_count,
    expected_first_aip,
):
    """Test response from report_data.storage_locations endpoint."""
    start_date = parse_datetime_bound(start_date)
    end_date = parse_datetime_bound(end_date, upper=True)

    report = data.aip_file_format_overview(
        storage_service_id=storage_service_id,
        start_date=start_date,
        end_date=end_date,
        storage_location_id=storage_location_id,
    )

    assert report[fields.FIELD_STORAGE_NAME] == storage_service_name
    assert report[fields.FIELD_STORAGE_LOCATION] == storage_location_description

    aips = report[fields.FIELD_AIPS]
    aips_count = len(aips)
    assert aips_count == expected_aips_count

    if aips_count < 1:
        return

    assert aips[0] == expected_first_aip


def test_storage_services(app_instance, mocker):
    """Test response from report_data.storage_services endpoint."""
    storage_services = mocker.patch("sqlalchemy.orm.query.Query.all")
    storage_services.return_value = MOCK_STORAGE_SERVICES

    report = data.storage_services()

    assert report == {
        "storage_services": [
            {"id": 1, "name": "some name"},
            {"id": 2, "name": "another name"},
        ]
    }
