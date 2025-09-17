import csv
import datetime
import uuid

import pytest

from AIPscan.Data import fields
from AIPscan.Data.report_data import aips_by_file_format
from AIPscan.Data.tests import (
    MOCK_AIPS_BY_FORMAT_OR_PUID_QUERY_RESULTS as QUERY_RESULTS,
)
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE as STORAGE_SERVICE
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_ID as STORAGE_SERVICE_ID
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.Reporter import helpers
from AIPscan.Reporter.report_aip_contents import CSV_HEADERS as AIP_CONTENTS_HEADERS
from AIPscan.Reporter.report_aips_by_format import HEADERS as AIPS_BY_FORMAT_HEADERS

ROWS_WITH_SIZE = [
    {
        fields.FIELD_AIP_UUID: "test uuid",
        fields.FIELD_AIP_NAME: "test name",
        fields.FIELD_SIZE: 1560321,
    },
    {
        fields.FIELD_AIP_UUID: "test uuid2",
        fields.FIELD_AIP_NAME: "test name2",
        fields.FIELD_SIZE: 123423,
    },
]

ROWS_WITH_SIZE_FORMATTED = [
    {
        fields.FIELD_AIP_UUID: "test uuid",
        fields.FIELD_AIP_NAME: "test name",
        fields.FIELD_SIZE: "1.6 MB",
        fields.FIELD_SIZE_BYTES: 1560321,
    },
    {
        fields.FIELD_AIP_UUID: "test uuid2",
        fields.FIELD_AIP_NAME: "test name2",
        fields.FIELD_SIZE: "123.4 kB",
        fields.FIELD_SIZE_BYTES: 123423,
    },
]

ROWS_WITHOUT_SIZE = [
    {fields.FIELD_NAME: "test name", fields.FIELD_UUID: "test uuid"},
    {fields.FIELD_NAME: "test name2", fields.FIELD_UUID: "test uuid2"},
]


def test_download_csv(app_instance, mocker):
    """Test downloading report data as CSV."""
    CSV_FILE = "test.csv"
    CONTENT_DISPOSITION = f"attachment; filename={CSV_FILE}"
    CSV_MIMETYPE = "text/csv"

    query_results = QUERY_RESULTS[:2]

    mock_query = mocker.patch(
        "AIPscan.Data.report_data._query_aips_by_file_format_or_puid"
    )
    mock_query.return_value = query_results
    mock_get_ss_name = mocker.patch("AIPscan.Data._get_storage_service")
    mock_get_ss_name.return_value = STORAGE_SERVICE

    headers = helpers.translate_headers(AIPS_BY_FORMAT_HEADERS)

    report_data = aips_by_file_format(STORAGE_SERVICE_ID, "test")
    response = helpers.download_csv(headers, report_data[fields.FIELD_AIPS], CSV_FILE)

    # Assert response is shaped as we expect.
    assert response is not None
    assert response.headers["Content-Disposition"] == CONTENT_DISPOSITION
    assert response.mimetype == CSV_MIMETYPE

    # Assert that content of CSV file is what we expect.
    content = response.get_data().decode()
    reader = csv.reader(content.splitlines())
    line_count = 0
    for row in reader:
        if line_count == 0:
            assert row == headers
        elif line_count == 1:
            assert row[0] == "aip0"
            assert row[1] == "11111111-1111-1111-1111-111111111111"
            assert row[2] == "5"
            assert row[3] == "12345678"
        else:
            assert row[0] == "aip1"
            assert row[1] == "22222222-2222-2222-2222-222222222222"
            assert row[2] == "3"
            assert row[3] == "123456"
        line_count += 1
    assert line_count == len(query_results) + 1


@pytest.mark.parametrize(
    "data,expected_output",
    [
        # No adding of header for size in bytes
        (
            {"headers": AIPS_BY_FORMAT_HEADERS, "add_bytes_column": False},
            ["AIP Name", "UUID", "Count", "Size"],
        ),
        # Adding of header for size in bytes at end of header list
        (
            {"headers": AIPS_BY_FORMAT_HEADERS, "add_bytes_column": True},
            ["AIP Name", "UUID", "Count", "Size", "Size (bytes)"],
        ),
        # Adding of header for size in bytes not at end of header list
        (
            {"headers": AIP_CONTENTS_HEADERS, "add_bytes_column": True},
            ["UUID", "AIP Name", "Created Date", "Size", "Size (bytes)", "Formats"],
        ),
    ],
)
def test_translate_headers(data, expected_output):
    headers = helpers.translate_headers(data["headers"], data["add_bytes_column"])

    assert headers == expected_output


@pytest.mark.parametrize(
    "data,expected_output",
    [
        # Dicts with size key should have the corresponding value
        # formatted by filesizeformat.
        (ROWS_WITH_SIZE, ROWS_WITH_SIZE_FORMATTED),
        # Dicts without size key should be unaffected.
        (ROWS_WITHOUT_SIZE, ROWS_WITHOUT_SIZE),
    ],
)
def test_format_size_for_csv(data, expected_output):
    """Test formatting size in report endpoint data."""
    assert helpers.format_size_for_csv(data) == expected_output


def test_get_premis_xml_lines():
    premis_xml = "First line\nSecond line"

    file_ = File(
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
        premis_object=premis_xml,
    )

    lines = file_.get_premis_xml_lines()

    assert len(lines) == 2


@pytest.mark.parametrize(
    "paging",
    [
        # Test paging window at start of results
        {"per_page": 5, "total": 17, "page": 1, "first_item": 1, "last_item": 5},
        # Test paging window on an arbitrary page of results
        {"per_page": 5, "total": 17, "page": 3, "first_item": 11, "last_item": 15},
        # Test paging window with last item being set to the total of items
        {"per_page": 5, "total": 17, "page": 4, "first_item": 16, "last_item": 17},
        # Test paging window at start of results with incomplete page
        {"per_page": 7, "total": 4, "page": 1, "first_item": 1, "last_item": 4},
    ],
)
def test_calculate_paging_window(paging):
    class MockPagination:
        pass

    pagination = MockPagination()
    pagination.page = paging["page"]
    pagination.per_page = paging["per_page"]
    pagination.total = paging["total"]

    first_item, last_item = helpers.calculate_paging_window(pagination)

    assert first_item == paging["first_item"]
    assert last_item == paging["last_item"]


def test_remove_dict_none_values():
    test_values = {"foo": "bar", "nada": None}

    querystring = helpers.remove_dict_none_values(test_values)

    assert querystring == {"foo": "bar", "nada": ""}
