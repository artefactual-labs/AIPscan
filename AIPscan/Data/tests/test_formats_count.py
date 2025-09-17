from datetime import datetime

import pytest

from AIPscan import typesense_test_helpers
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


class MockFormatsCountQueryResult:
    """Fixture for mocking SQLAlchemy query results."""

    def __init__(self, file_format, file_count, total_size):
        self.file_format = file_format
        self.file_count = file_count
        self.total_size = total_size


MOCK_QUERY_RESULTS = [
    MockFormatsCountQueryResult(file_format="JPEG", file_count=5, total_size=12345678),
    MockFormatsCountQueryResult(file_format="CSV", file_count=3, total_size=123456),
    MockFormatsCountQueryResult(
        file_format="MPEG-4 Media File", file_count=1, total_size=12345
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
def test_formats_count(app_instance, mocker, query_results, results_count):
    """Test that results match high-level expectations."""
    query = mocker.patch("AIPscan.Data.report_data._formats_count_query")
    query.return_value = query_results

    get_ss = mocker.patch("AIPscan.Data._get_storage_service")
    get_ss.return_value = MOCK_STORAGE_SERVICE

    test_location = create_test_storage_location()
    get_location = mocker.patch("AIPscan.Data._get_storage_location")
    get_location.return_value = test_location

    report = report_data.formats_count(
        storage_service_id=MOCK_STORAGE_SERVICE_ID,
        start_date=datetime.min,
        end_date=datetime.max,
        storage_location_id=test_location.id,
    )
    assert report[fields.FIELD_STORAGE_NAME] == MOCK_STORAGE_SERVICE_NAME
    assert report[fields.FIELD_STORAGE_LOCATION] == test_location.description
    assert len(report[fields.FIELD_FORMATS]) == results_count


def test_formats_count_no_results_typesense(
    app_with_populated_files, enable_typesense, mocker
):
    mocker.patch("typesense.collections.Collections.__getitem__")
    mocker.patch("typesense.multi_search.MultiSearch.perform")
    mocker.patch("AIPscan.typesense_helpers.facet_value_counts")

    expected_result = {
        "StorageName": "test storage service",
        "StorageLocation": "test storage location",
        "Formats": [],
    }

    start_date = "2019-01-01"
    end_date = "2019-10-01"

    report = report_data_typesense.formats_count(
        1,
        1,
        datetime.strptime(start_date, "%Y-%m-%d"),
        datetime.strptime(end_date, "%Y-%m-%d"),
    )
    assert report == expected_result


def test_formats_count_typesense(app_with_populated_files, enable_typesense, mocker):
    typesense_test_helpers.fake_collection_format_counts(mocker)

    expected_result = {
        "StorageName": "test storage service",
        "StorageLocation": "test storage location",
        "Formats": [{"Format": "wav", "Count": 10, "Size": 999}],
    }

    start_date = "2019-01-01"
    end_date = "2019-10-01"
    report = report_data_typesense.formats_count(
        1,
        1,
        datetime.strptime(start_date, "%Y-%m-%d"),
        datetime.strptime(end_date, "%Y-%m-%d"),
    )
    assert report == expected_result

    report = report_data_typesense.formats_count(
        1, 1, parse_datetime_bound(start_date), parse_datetime_bound(end_date)
    )
    assert report == expected_result


@pytest.mark.parametrize(
    "test_format", [mock_result for mock_result in MOCK_QUERY_RESULTS]
)
def test_formats_count_elements(app_instance, mocker, test_format):
    """Test that structure of versions data matches expectations."""
    mock_query = mocker.patch("AIPscan.Data.report_data._formats_count_query")
    mock_query.return_value = [test_format]

    mock_get_ss_name = mocker.patch("AIPscan.Data._get_storage_service")
    mock_get_ss_name.return_value = MOCK_STORAGE_SERVICE

    report = report_data.formats_count(
        MOCK_STORAGE_SERVICE_ID, datetime.min, datetime.max
    )
    report_format = report[fields.FIELD_FORMATS][0]

    assert test_format.file_format == report_format.get(fields.FIELD_FORMAT)
    assert test_format.file_count == report_format.get(fields.FIELD_COUNT)
    assert test_format.total_size == report_format.get(fields.FIELD_SIZE)


@pytest.mark.parametrize(
    "start_date, end_date, format_count, total_file_count, total_file_size",
    [
        # Not specifying dates should return all files and versions.
        (None, None, 2, 3, TOTAL_FILE_SIZE),
        # Start date before first AIP was ingested hould return all
        # files and versions.
        (DATE_BEFORE_AIP_1, None, 2, 3, TOTAL_FILE_SIZE),
        # Start date that's the same day our first AIP was ingested
        # should return all files and versions.
        (AIP_1_CREATION_DATE, None, 2, 3, TOTAL_FILE_SIZE),
        # Start date after our first AIP was ingested should return
        # only the second JPEG version and ISO disk image.
        (DATE_AFTER_AIP_1, None, 2, 2, JPEG_1_02_FILE_SIZE),
        # End date before second AIP was ingested should return only
        # the first JPEG version.
        (None, DATE_BEFORE_AIP_2, 1, 1, JPEG_1_01_FILE_SIZE),
        # End date that's the same day our second AIP was ingested
        # should return all files and versions.
        (None, AIP_2_CREATION_DATE, 2, 3, TOTAL_FILE_SIZE),
        # End date that's after our second AIP was ingested should
        # return all files and versions.
        (None, DATE_AFTER_AIP_2, 2, 3, TOTAL_FILE_SIZE),
        # Start and end dates that define a range in which we haven't
        # ingested any AIPs should return no files or versions.
        ("2019-01-01", "2019-01-02", 0, 0, 0),
        # Invalid values for start and end dates should be treated as
        # None values and return both JPEG versions.
        (True, "NOT A DATE", 2, 3, TOTAL_FILE_SIZE),
    ],
)
def test_formats_count_contents(
    app_with_populated_format_versions,
    start_date,
    end_date,
    format_count,
    total_file_count,
    total_file_size,
):
    """Test that content of response matches expectations.

    This integration test uses a pre-populated fixture to verify that
    the database access layer of our endpoint returns what we expect.
    """
    results = report_data.formats_count(
        storage_service_id=1,
        start_date=parse_datetime_bound(start_date),
        end_date=parse_datetime_bound(end_date, upper=True),
    )
    formats = results[fields.FIELD_FORMATS]
    assert len(formats) == format_count
    assert (
        sum(format_.get(fields.FIELD_COUNT, 0) for format_ in formats)
        == total_file_count
    )
    assert (
        sum(format_.get(fields.FIELD_SIZE, 0) for format_ in formats) == total_file_size
    )
