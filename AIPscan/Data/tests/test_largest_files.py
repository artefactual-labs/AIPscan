# -*- coding: utf-8 -*-
import datetime
import pytest
import uuid

from AIPscan.Data import fields, report_data
from AIPscan.Data.tests import (
    MOCK_AIP,
    MOCK_AIP_NAME,
    MOCK_AIP_UUID,
    MOCK_STORAGE_SERVICE,
    MOCK_STORAGE_SERVICE_ID,
    MOCK_STORAGE_SERVICE_NAME,
)
from AIPscan.models import File, FileType


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
    "file_data, file_count", [([], 0), (TEST_FILES, 3), (TEST_FILES[:2], 2)]
)
def test_largest_files(app_instance, mocker, file_data, file_count):
    """Test that return value conforms to expected structure.
    """
    mock_query = mocker.patch("AIPscan.Data.report_data._largest_files_query")
    mock_query.return_value = file_data

    mock_get_ss = mocker.patch("AIPscan.Data.report_data._get_storage_service")
    mock_get_ss.return_value = MOCK_STORAGE_SERVICE

    mock_get_aip = mocker.patch("sqlalchemy.orm.query.Query.get")
    mock_get_aip.return_value = MOCK_AIP

    report = report_data.largest_files(MOCK_STORAGE_SERVICE_ID)
    report_files = report[fields.FIELD_FILES]
    assert report[fields.FIELD_STORAGE_NAME] == MOCK_STORAGE_SERVICE_NAME
    assert len(report_files) == file_count


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
    """Test that returned file data matches expected values.
    """
    mock_query = mocker.patch("AIPscan.Data.report_data._largest_files_query")
    mock_query.return_value = [test_file]

    mock_get_ss = mocker.patch("AIPscan.Data.report_data._get_storage_service")
    mock_get_ss.return_value = MOCK_STORAGE_SERVICE

    mock_get_aip = mocker.patch("sqlalchemy.orm.query.Query.get")
    mock_get_aip.return_value = MOCK_AIP

    report = report_data.largest_files(MOCK_STORAGE_SERVICE_ID)
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
