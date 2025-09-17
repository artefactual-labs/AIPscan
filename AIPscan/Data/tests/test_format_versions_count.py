from datetime import datetime

import pytest

from AIPscan.conftest import AIP_1_CREATION_DATE
from AIPscan.conftest import AIP_2_CREATION_DATE
from AIPscan.conftest import ORIGINAL_FILE_SIZE as JPEG_1_01_FILE_SIZE
from AIPscan.conftest import PRESERVATION_FILE_SIZE as JPEG_1_02_FILE_SIZE
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.Data import report_data_typesense
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_ID
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_NAME
from AIPscan.helpers import parse_datetime_bound
from AIPscan.test_helpers import create_test_storage_location

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
    query = mocker.patch("AIPscan.Data.report_data._format_versions_count_query")
    query.return_value = query_results

    get_ss = mocker.patch("AIPscan.Data._get_storage_service")
    get_ss.return_value = MOCK_STORAGE_SERVICE

    test_location = create_test_storage_location()
    get_location = mocker.patch("AIPscan.Data._get_storage_location")
    get_location.return_value = test_location

    report = report_data.format_versions_count(
        storage_service_id=MOCK_STORAGE_SERVICE_ID,
        start_date=datetime.min,
        end_date=datetime.max,
        storage_location_id=test_location.id,
    )
    assert report[fields.FIELD_STORAGE_NAME] == MOCK_STORAGE_SERVICE_NAME
    assert report[fields.FIELD_STORAGE_LOCATION] == test_location.description
    assert len(report[fields.FIELD_FORMAT_VERSIONS]) == results_count


@pytest.mark.parametrize(
    "test_format_version", [mock_result for mock_result in MOCK_QUERY_RESULTS]
)
def test_format_versions_count_elements(app_instance, mocker, test_format_version):
    """Test that structure of versions data matches expectations."""
    mock_query = mocker.patch("AIPscan.Data.report_data._format_versions_count_query")
    mock_query.return_value = [test_format_version]

    mock_get_ss_name = mocker.patch("AIPscan.Data._get_storage_service")
    mock_get_ss_name.return_value = MOCK_STORAGE_SERVICE

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


def test_format_versions_count_no_results_typesense(
    app_with_populated_files, enable_typesense, mocker
):
    mocker.patch("typesense.collections.Collections.__getitem__")
    mocker.patch("typesense.multi_search.MultiSearch.perform")
    mocker.patch("AIPscan.typesense_helpers.facet_value_counts")

    expected_result = {
        "StorageName": "test storage service",
        "StorageLocation": "test storage location",
        "FormatVersions": [],
    }

    start_date = "2019-01-01"
    end_date = "2019-10-01"

    report = report_data_typesense.format_versions_count(
        1,
        datetime.strptime(start_date, "%Y-%m-%d"),
        datetime.strptime(end_date, "%Y-%m-%d"),
        1,
    )
    assert report == expected_result
