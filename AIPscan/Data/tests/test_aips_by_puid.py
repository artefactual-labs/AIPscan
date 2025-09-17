import pytest

from AIPscan.conftest import ORIGINAL_FILE_SIZE
from AIPscan.conftest import PRESERVATION_FILE_SIZE
from AIPscan.conftest import TIFF_PUID
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.Data.tests import (
    MOCK_AIPS_BY_FORMAT_OR_PUID_QUERY_RESULTS as MOCK_QUERY_RESULTS,
)
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_ID
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_NAME
from AIPscan.test_helpers import create_test_storage_location


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
def test_aips_by_puid(app_instance, mocker, query_results, results_count):
    """Test that results match high-level expectations."""
    query = mocker.patch("AIPscan.Data.report_data._query_aips_by_file_format_or_puid")
    query.return_value = query_results

    get_ss = mocker.patch("AIPscan.Data._get_storage_service")
    get_ss.return_value = MOCK_STORAGE_SERVICE

    test_location = create_test_storage_location()
    get_location = mocker.patch("AIPscan.Data._get_storage_location")
    get_location.return_value = test_location

    report = report_data.aips_by_puid(
        storage_service_id=MOCK_STORAGE_SERVICE_ID,
        storage_location_id=test_location.id,
        puid="fmt/###",
    )
    assert report[fields.FIELD_STORAGE_NAME] == MOCK_STORAGE_SERVICE_NAME
    assert report[fields.FIELD_STORAGE_LOCATION] == test_location.description
    assert len(report[fields.FIELD_AIPS]) == results_count


@pytest.mark.parametrize(
    "test_aip", [mock_result for mock_result in MOCK_QUERY_RESULTS]
)
def test_aips_by_puid_aip_elements(app_instance, mocker, test_aip):
    """Test that structure of AIP data matches expectations."""
    mock_query = mocker.patch(
        "AIPscan.Data.report_data._query_aips_by_file_format_or_puid"
    )
    mock_query.return_value = [test_aip]

    mock_get_ss_name = mocker.patch("AIPscan.Data._get_storage_service")
    mock_get_ss_name.return_value = MOCK_STORAGE_SERVICE

    report = report_data.aips_by_puid(MOCK_STORAGE_SERVICE_ID, "fmt/###")
    report_aip = report[fields.FIELD_AIPS][0]

    assert test_aip.id == report_aip.get(fields.FIELD_ID)
    assert test_aip.name == report_aip.get(fields.FIELD_AIP_NAME)
    assert test_aip.uuid == report_aip.get(fields.FIELD_UUID)
    assert test_aip.file_count == report_aip.get(fields.FIELD_COUNT)
    assert test_aip.total_size == report_aip.get(fields.FIELD_SIZE)


@pytest.mark.parametrize(
    "puid, original_files, aip_count, total_file_count, total_file_size",
    [
        # Original format in test data should be included in results.
        (TIFF_PUID, True, 1, 1, ORIGINAL_FILE_SIZE),
        # Original format not in test data should not be included in
        # results.
        ("fmt/1", True, 0, 0, 0),
        # Preservation format in test data should be included in
        # results.
        (TIFF_PUID, False, 1, 1, PRESERVATION_FILE_SIZE),
        # Non-existent preservation format not present in test data
        # should not be included in results.
        ("x-fmt/999999", False, 0, 0, 0),
        # Passing a None value for original_files returns original
        # files.
        (TIFF_PUID, None, 1, 1, ORIGINAL_FILE_SIZE),
        # Passing an incorrect value for original_files returns
        # original files.
        (TIFF_PUID, "invalid", 1, 1, ORIGINAL_FILE_SIZE),
    ],
)
def test_aips_by_file_format_contents(
    app_with_populated_files,
    puid,
    original_files,
    aip_count,
    total_file_count,
    total_file_size,
):
    """Test that content of response matches expectations.

    This integration test uses a pre-populated fixture to verify that
    the database access layer of our endpoint returns what we expect.
    """
    results = report_data.aips_by_puid(
        storage_service_id=1, puid=puid, original_files=original_files
    )
    aips = results[fields.FIELD_AIPS]
    assert len(aips) == aip_count
    assert sum(aip[fields.FIELD_COUNT] for aip in aips) == total_file_count
    assert sum(aip[fields.FIELD_SIZE] for aip in aips) == total_file_size
