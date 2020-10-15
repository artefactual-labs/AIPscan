# -*- coding: utf-8 -*-

import pytest

from AIPscan.Data import data
from AIPscan.Data.tests import (
    MOCK_AIPS_BY_FORMAT_OR_PUID_QUERY_RESULTS as MOCK_QUERY_RESULTS,
    MOCK_STORAGE_SERVICE,
    MOCK_STORAGE_SERVICE_ID,
    MOCK_STORAGE_SERVICE_NAME,
)


@pytest.mark.parametrize(
    "query_results, results_count",
    [([], 0), (MOCK_QUERY_RESULTS, 4), (MOCK_QUERY_RESULTS[:2], 2)],
)
def test_aips_by_puid(mocker, query_results, results_count):
    """Test that return value conforms to expected structure.
    """
    mock_query = mocker.patch("AIPscan.Data.data._aips_by_puid_query")
    mock_query.return_value = query_results

    mock_get_ss = mocker.patch("AIPscan.Data.data._get_storage_service")
    mock_get_ss.return_value = MOCK_STORAGE_SERVICE

    report = data.aips_by_puid(MOCK_STORAGE_SERVICE_ID, "fmt/###")
    assert report[data.FIELD_STORAGE_NAME] == MOCK_STORAGE_SERVICE_NAME
    assert len(report[data.FIELD_AIPS]) == results_count


@pytest.mark.parametrize(
    "test_aip",
    [
        (MOCK_QUERY_RESULTS[0]),
        (MOCK_QUERY_RESULTS[1]),
        (MOCK_QUERY_RESULTS[2]),
        (MOCK_QUERY_RESULTS[3]),
    ],
)
def test_aips_by_puid_elements(mocker, test_aip):
    """Test that returned data matches expected values.
    """
    mock_query = mocker.patch("AIPscan.Data.data._aips_by_puid_query")
    mock_query.return_value = [test_aip]

    mock_get_ss = mocker.patch("AIPscan.Data.data._get_storage_service")
    mock_get_ss.return_value = MOCK_STORAGE_SERVICE

    report = data.aips_by_puid(MOCK_STORAGE_SERVICE_ID, "fmt/###")
    report_aip = report[data.FIELD_AIPS][0]

    assert test_aip.id == report_aip.get("id")
    assert test_aip.name == report_aip.get(data.FIELD_AIP_NAME)
    assert test_aip.uuid == report_aip.get(data.FIELD_UUID)
    assert test_aip.file_count == report_aip.get(data.FIELD_COUNT)
    assert test_aip.total_size == report_aip.get(data.FIELD_SIZE)
