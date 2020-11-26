# -*- coding: utf-8 -*-

from datetime import datetime
import pytest

from AIPscan.helpers import parse_datetime_bound
from AIPscan.Data import fields, report_data
from AIPscan.Data.tests import (
    MOCK_STORAGE_SERVICE,
    MOCK_STORAGE_SERVICE_ID,
    MOCK_STORAGE_SERVICE_NAME,
)
from AIPscan.Data.tests.conftest import (
    AIP_1_CREATION_DATE,
    AIP_2_CREATION_DATE,
    ORIGINAL_FILE_SIZE as JPEG_1_01_FILE_SIZE,
    PRESERVATION_FILE_SIZE as JPEG_1_02_FILE_SIZE,
)

TOTAL_FILE_SIZE = JPEG_1_01_FILE_SIZE + JPEG_1_02_FILE_SIZE

DATE_BEFORE_AIP_1 = "2019-01-01"
DATE_AFTER_AIP_1 = "2020-01-02"
DATE_BEFORE_AIP_2 = "2020-05-30"
DATE_AFTER_AIP_2 = "2020-06-02"


class MockFormatVersionsCountQueryResult:
    """Fixture for mocking SQLAlchemy query results."""

    def __init__(self, puid, file_format, format_version, file_count, total_size):
        self.puid = puid
        self.file_format = file_format
        self.format_version = format_version
        self.file_count = file_count
        self.total_size = total_size


MOCK_QUERY_RESULTS = [
    MockFormatVersionsCountQueryResult(
        puid="fmt/43",
        file_format="JPEG",
        format_version="1.01",
        file_count=5,
        total_size=12345678,
    ),
    MockFormatVersionsCountQueryResult(
        puid="fmt/44",
        file_format="JPEG",
        format_version="1.02",
        file_count=3,
        total_size=1234567,
    ),
    MockFormatVersionsCountQueryResult(
        puid="fmt/199",
        file_format="MPEG-4 Media File",
        format_version=None,
        file_count=1,
        total_size=12345,
    ),
]


@pytest.mark.parametrize(
    "query_results, results_count",
    [
        # Empty result set, count is 0.
        ([], 0),
        # Test the return of complete result set, count is the length
        # of all results.
        (MOCK_QUERY_RESULTS, len(MOCK_QUERY_RESULTS)),
        # Test the return of only the first two results, count is 2.
        (MOCK_QUERY_RESULTS[:2], 2),
    ],
)
def test_format_versions_count(app_instance, mocker, query_results, results_count):
    """Test that results match high-level expectations."""
    mock_query = mocker.patch("AIPscan.Data.report_data._format_versions_count_query")
    mock_query.return_value = query_results

    mock_get_ss = mocker.patch("AIPscan.Data.report_data._get_storage_service")
    mock_get_ss.return_value = MOCK_STORAGE_SERVICE

    report = report_data.format_versions_count(
        MOCK_STORAGE_SERVICE_ID, datetime.min, datetime.max
    )
    assert report[fields.FIELD_STORAGE_NAME] == MOCK_STORAGE_SERVICE_NAME
    assert len(report[fields.FIELD_FORMAT_VERSIONS]) == results_count


@pytest.mark.parametrize(
    "test_format_version", [mock_result for mock_result in MOCK_QUERY_RESULTS]
)
def test_format_versions_count_elements(app_instance, mocker, test_format_version):
    """Test that structure of versions data matches expectations."""
    mock_query = mocker.patch("AIPscan.Data.report_data._format_versions_count_query")
    mock_query.return_value = [test_format_version]

    mock_get_ss = mocker.patch("AIPscan.Data.report_data._get_storage_service")
    mock_get_ss.return_value = MOCK_STORAGE_SERVICE

    report = report_data.format_versions_count(
        MOCK_STORAGE_SERVICE_ID, datetime.min, datetime.max
    )
    report_format_version = report[fields.FIELD_FORMAT_VERSIONS][0]

    assert test_format_version.puid == report_format_version.get(fields.FIELD_PUID)
    assert test_format_version.file_format == report_format_version.get(
        fields.FIELD_FORMAT
    )
    assert test_format_version.format_version == report_format_version.get(
        fields.FIELD_VERSION
    )
    assert test_format_version.file_count == report_format_version.get(
        fields.FIELD_COUNT
    )
    assert test_format_version.total_size == report_format_version.get(
        fields.FIELD_SIZE
    )


@pytest.mark.parametrize(
    "start_date, end_date, version_count, total_file_count, total_file_size",
    [
        # Not specifying dates should return all files and versions.
        (None, None, 3, 3, TOTAL_FILE_SIZE),
        # Start date before first AIP was ingested hould return all
        # files and versions.
        (DATE_BEFORE_AIP_1, None, 3, 3, TOTAL_FILE_SIZE),
        # Start date that's the same day our first AIP was ingested
        # should return all files and versions.
        (AIP_1_CREATION_DATE, None, 3, 3, TOTAL_FILE_SIZE),
        # Start date after our first AIP was ingested should return
        # only the second JPEG version and ISO disk image.
        (DATE_AFTER_AIP_1, None, 2, 2, JPEG_1_02_FILE_SIZE),
        # End date before second AIP was ingested should return only
        # the first JPEG version.
        (None, DATE_BEFORE_AIP_2, 1, 1, JPEG_1_01_FILE_SIZE),
        # End date that's the same day our second AIP was ingested
        # should return all files and versions.
        (None, AIP_2_CREATION_DATE, 3, 3, TOTAL_FILE_SIZE),
        # End date that's after our second AIP was ingested should
        # return all files and versions.
        (None, DATE_AFTER_AIP_2, 3, 3, TOTAL_FILE_SIZE),
        # Start and end dates that define a range in which we haven't
        # ingested any AIPs should return no files or versions.
        ("2019-01-01", "2019-01-02", 0, 0, 0),
        # Invalid values for start and end dates should be treated as
        # None values and return both JPEG versions.
        (True, "NOT A DATE", 3, 3, TOTAL_FILE_SIZE),
    ],
)
def test_format_versions_count_contents(
    app_with_populated_format_versions,
    start_date,
    end_date,
    version_count,
    total_file_count,
    total_file_size,
):
    """Test that content of response matches expectations.

    This integration test uses a pre-populated fixture to verify that
    the database access layer of our endpoint returns what we expect.
    """
    results = report_data.format_versions_count(
        storage_service_id=1,
        start_date=parse_datetime_bound(start_date),
        end_date=parse_datetime_bound(end_date, upper=True),
    )
    versions = results[fields.FIELD_FORMAT_VERSIONS]
    assert len(versions) == version_count
    assert (
        sum(version.get(fields.FIELD_COUNT, 0) for version in versions)
        == total_file_count
    )
    assert (
        sum(version.get(fields.FIELD_SIZE, 0) for version in versions)
        == total_file_size
    )
