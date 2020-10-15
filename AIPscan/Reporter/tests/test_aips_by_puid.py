# -*- coding: utf-8 -*-

import datetime
import pytest
import uuid

from AIPscan.Reporter.report_aips_by_puid import get_format_string_from_puid
from AIPscan.models import File, FileType

FILE_WITH_FORMAT_ONLY = File(
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
)

FILE_WITH_FORMAT_AND_VERSION = File(
    uuid=uuid.uuid4(),
    name="test.pdf",
    size=12345678,
    aip_id=1,
    file_type=FileType.preservation,
    file_format="Acrobat PDF/A - Portable Document Format",
    format_version="1b",
    puid="fmt/354",
    filepath="/path/to/test.pdf",
    date_created=datetime.datetime.now(),
    checksum_type="md5",
    checksum_value="yetanotherfakemd5",
    original_file_id=1,
)

FILE_WITH_NO_FORMAT = File(
    uuid=uuid.uuid4(),
    name="test.txt",
    size=12345,
    aip_id=2,
    file_type=FileType.original,
    file_format=None,
    puid="x-fmt/111",
    filepath="/path/to/file.txt",
    date_created=datetime.datetime.now(),
    checksum_type="md5",
    checksum_value="anotherfakemd5",
)


@pytest.mark.parametrize(
    "puid, mock_file, expected_return_value",
    [
        ("x-fmt/111", FILE_WITH_FORMAT_ONLY, "Plain Text File"),
        (
            "fmt/354",
            FILE_WITH_FORMAT_AND_VERSION,
            "Acrobat PDF/A - Portable Document Format (1b)",
        ),
        ("x-fmt/111", FILE_WITH_NO_FORMAT, None),
        ("fmt/123", None, None),
    ],
)
def test_get_format_name_and_version_from_puid(
    mocker, puid, mock_file, expected_return_value
):
    """Test that helper function returns expected string or None.
    """
    mock_get_file = mocker.patch("sqlalchemy.orm.query.Query.first")
    mock_get_file.return_value = mock_file
    assert expected_return_value == get_format_string_from_puid(puid)
