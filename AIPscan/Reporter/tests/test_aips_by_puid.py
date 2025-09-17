import datetime
import uuid

import pytest
from flask import current_app

from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.Reporter.report_aips_by_puid import get_format_string_from_puid

EXPECTED_CSV_ORIGINAL = b"AIP Name,UUID,Count,Size,Size (bytes)\r\nTest AIP,111111111111-1111-1111-11111111,1,1.0 kB,1000\r\n"
EXPECTED_CSV_PRESERVATION = b"AIP Name,UUID,Count,Size,Size (bytes)\r\nTest AIP,111111111111-1111-1111-11111111,1,2.0 kB,2000\r\n"

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
    app_instance, mocker, puid, mock_file, expected_return_value
):
    """Test that helper function returns expected string or None."""
    mock_get_file = mocker.patch("sqlalchemy.orm.query.Query.first")
    mock_get_file.return_value = mock_file
    assert expected_return_value == get_format_string_from_puid(puid)


@pytest.mark.parametrize(
    "original_files",
    [
        # Original files.
        ("True"),
        # Preservation files.
        ("False"),
    ],
)
def test_aips_by_puid(app_with_populated_files, original_files):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            f"/reporter/aips_by_puid/?amss_id=1&puid=fmt/353&original_files={original_files}"
        )
        assert response.status_code == 200


@pytest.mark.parametrize(
    "original_files,expected_csv",
    [
        # Original files.
        ("True", EXPECTED_CSV_ORIGINAL),
        # Preservation files.
        ("False", EXPECTED_CSV_PRESERVATION),
    ],
)
def test_aips_by_puid_csv(app_with_populated_files, original_files, expected_csv):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get(
            f"/reporter/aips_by_puid/?amss_id=1&puid=fmt/353&original_files={original_files}&csv=True"
        )
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=aips_by_puid_fmt/353.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == expected_csv
