import datetime
import uuid

import pytest

from AIPscan import db
from AIPscan import typesense_helpers
from AIPscan import typesense_test_helpers
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.Data import report_data_typesense
from AIPscan.Data.tests import MOCK_AIP
from AIPscan.Data.tests import MOCK_AIP_NAME
from AIPscan.Data.tests import MOCK_AIP_UUID
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_ID
from AIPscan.helpers import parse_datetime_bound
from AIPscan.models import File
from AIPscan.models import FileType

TEST_FILES = [
    File(
        uuid=uuid.uuid4(),
        name="test.csv",
        size=1234567,
        aip_id=1,
        file_type=FileType.original,
        file_format="Comma Separated Values",
        filepath="/path/to/file.csv",
        date_created=datetime.datetime.now(),
        checksum_type="md5",
        checksum_value="fakemd5",
    ),
    File(
        uuid=uuid.uuid4(),
        name="test.txt",
        size=12345,
        aip_id=2,
        file_type=FileType.original,
        file_format="Plain Text File",
        puid="x-fmt/111",
        filepath="/path/to/file.txt",
        date_created=datetime.datetime.now(),
        checksum_type="md5",
        checksum_value="anotherfakemd5",
    ),
    File(
        uuid=uuid.uuid4(),
        name="test.pdf",
        size=12345678,
        aip_id=1,
        file_type=FileType.preservation,
        file_format="Acrobat PDF/A - Portable Document Format",
        format_version="1b",
        filepath="/path/to/test.pdf",
        date_created=datetime.datetime.now(),
        checksum_type="md5",
        checksum_value="yetanotherfakemd5",
        original_file_id=1,
    ),
]


@pytest.mark.parametrize(
    "storage_location_id, storage_location_description, start_date, end_date, file_count, largest_file_size, second_largest_file_size",
    [
        # Test all AIPs.
        (None, None, "2020-01-01", "2022-12-31", 7, 2500, 2500),
        # Test filtering by date.
        (None, None, "2020-01-01", "2020-06-01", 4, 1000, 300),
        # Test filtering by storage location.
        (1, "AIP Store Location 1", "2020-01-01", "2022-12-31", 4, 1000, 300),
        (2, "AIP Store Location 2", "2020-01-01", "2022-12-31", 3, 2500, 2500),
    ],
)
def test_largest_files(
    storage_locations,
    storage_location_id,
    storage_location_description,
    start_date,
    end_date,
    file_count,
    largest_file_size,
    second_largest_file_size,
):
    """Test that files and order returned by report_data.largest_files match expectations."""
    report = report_data.largest_files(
        storage_service_id=1,
        start_date=parse_datetime_bound(start_date),
        end_date=parse_datetime_bound(end_date, upper=True),
        storage_location_id=storage_location_id,
    )
    report_files = report[fields.FIELD_FILES]
    assert report[fields.FIELD_STORAGE_NAME] == "test storage service"
    assert report[fields.FIELD_STORAGE_LOCATION] == storage_location_description

    assert len(report_files) == file_count
    assert report_files[0][fields.FIELD_SIZE] == largest_file_size
    assert report_files[1][fields.FIELD_SIZE] == second_largest_file_size


@pytest.mark.parametrize(
    "test_file, has_format_version, has_puid",
    [
        (TEST_FILES[0], False, False),
        (TEST_FILES[1], False, True),
        (TEST_FILES[2], True, False),
    ],
)
def test_largest_files_elements(
    app_instance, mocker, test_file, has_format_version, has_puid
):
    """Test that returned file data matches expected values."""
    mock_query = mocker.patch("AIPscan.Data.report_data._largest_files_query")
    mock_query.return_value = [test_file]

    mock_get_ss_name = mocker.patch("AIPscan.Data._get_storage_service")
    mock_get_ss_name.return_value = MOCK_STORAGE_SERVICE

    mock_get_aip = mocker.patch("AIPscan.Data.report_data.db.session.get")
    mock_get_aip.return_value = MOCK_AIP

    report = report_data.largest_files(
        MOCK_STORAGE_SERVICE_ID,
        start_date=parse_datetime_bound("2000-01-01"),
        end_date=parse_datetime_bound("2022-12-31", upper=True),
    )
    report_file = report[fields.FIELD_FILES][0]

    # Required elements
    assert test_file.name == report_file.get(fields.FIELD_NAME)
    assert test_file.file_format == report_file.get(fields.FIELD_FORMAT)

    # Optional elements
    if has_format_version:
        assert test_file.format_version == report_file.get(fields.FIELD_VERSION)
    else:
        assert report_file.get(fields.FIELD_VERSION) is None

    if has_puid:
        assert test_file.puid == report_file.get(fields.FIELD_PUID)
    else:
        assert report_file.get(fields.FIELD_PUID) is None

    # AIP information
    assert report_file.get(fields.FIELD_AIP_NAME) == MOCK_AIP_NAME
    assert report_file.get(fields.FIELD_AIP_UUID) == MOCK_AIP_UUID


def test_largest_files_typesense(app_with_populated_files, enable_typesense, mocker):
    doc = typesense_helpers.model_instance_to_document(File, db.session.get(File, 1))
    doc["transfer_name"] = "Test AIP"
    doc["aip_uuid"] = "111111111111-1111-1111-11111111"

    fake_results = {"hits": [{"document": doc}]}

    typesense_test_helpers.fake_collection(mocker, fake_results)

    expected_result = {
        "Files": [
            {
                "AIPName": "Test AIP",
                "AIPUUID": "111111111111-1111-1111-11111111",
                "ID": "1",
                "UUID": "222222222222-2222-2222-22222222",
                "Name": "file_name.ext",
                "Size": 1000,
                "FileType": "original",
                "Format": "Tagged Image File Format",
                "Version": "0.0.0",
                "PUID": "fmt/353",
            }
        ],
        "StorageName": "test storage service",
        "StorageLocation": "test storage location",
    }

    report = report_data_typesense.largest_files(
        storage_service_id=1,
        start_date=parse_datetime_bound("2019-01-01"),
        end_date=parse_datetime_bound("2019-10-10"),
        storage_location_id=1,
    )
    assert report == expected_result
