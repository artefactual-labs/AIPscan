import csv
import io

import pytest
from flask import current_app
from lxml import html

from AIPscan import test_helpers

EXPECTED_CSV_CONTENTS = b"UUID,AIP Name,Created Date,Size,Size (bytes),Formats\r\n111111111111-1111-1111-11111111,Test AIP,2020-01-01 00:00:00,0 Bytes,0,fmt/43 (ACME File Format 0.0.0): 1 file|fmt/61 (ACME File Format 0.0.0): 1 file\r\n222222222222-2222-2222-22222222,Test AIP,2020-06-01 00:00:00,0 Bytes,0,x-fmt/111 (ACME File Format 0.0.0): 3 files|fmt/61 (ACME File Format 0.0.0): 2 files\r\n"


def test_aip_contents(aip_contents):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/aip_contents/?amss_id=1")
        assert response.status_code == 200


def test_aip_contents_csv(aip_contents):
    """Test CSV export."""
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/aip_contents/?amss_id=1&csv=True")
        assert response.status_code == 200
        assert (
            response.headers["Content-Disposition"]
            == "attachment; filename=aip_contents.csv"
        )
        assert response.mimetype == "text/csv"
        assert response.data == EXPECTED_CSV_CONTENTS


@pytest.mark.parametrize(
    "puid, format_name, format_version, expected_label",
    [
        (
            None,
            "Unregistered format",
            None,
            "Unregistered format (Unregistered format)",
        ),
        (
            "",
            "Unregistered format",
            "1.0",
            "Unregistered format (Unregistered format 1.0)",
        ),
        (None, None, None, "Unknown (Unknown)"),
        (
            None,
            "Unregistered <format> & data",
            "<v1>",
            "Unregistered <format> & data (Unregistered <format> & data <v1>)",
        ),
    ],
    ids=["missing-puid", "empty-puid", "unknown-format", "markup-in-format"],
)
@pytest.mark.parametrize("csv_export", [False, True], ids=["html", "csv"])
def test_aip_contents_retains_files_without_puids(
    app_instance, puid, format_name, format_version, expected_label, csv_export
):
    aip = test_helpers.create_test_aip()
    for size in (123, 456):
        test_helpers.create_test_file(
            aip_id=aip.id,
            size=size,
            puid=puid,
            file_format=format_name,
            format_version=format_version,
        )
    response = app_instance.test_client().get(
        "/reporter/aip_contents/",
        query_string={
            "amss_id": aip.storage_service_id,
            "csv": str(csv_export).lower(),
        },
    )
    assert response.status_code == 200
    expected_formats = f"{expected_label}: 2 files"
    if csv_export:
        assert response.mimetype == "text/csv"
        (row,) = csv.DictReader(io.StringIO(response.get_data(as_text=True)))
        assert int(row["Size (bytes)"]) == 579
        assert row["Formats"] == expected_formats
    else:
        document = html.fromstring(response.data)
        (row,) = document.xpath("//table[@id='aip-contents']/tbody/tr")
        cells = row.xpath("./td")
        assert cells[2].text_content().strip() == "579 Bytes"
        assert cells[3].text_content().strip() == expected_formats
