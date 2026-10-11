"""Boundary fixtures use HTTP; imports and failures still run through Celery."""

import os

import pytest
from playwright.sync_api import expect
from pytest_bdd import given
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from workflow import fetch_repository
from workflow import report_rows
from workflow import request

scenarios("features/storage_changes.feature")


def configure(**changes):
    request("POST", "http://fault-storage:8000/control", json=changes)


@pytest.fixture
def boundary_repository(imported_repository):
    # Remove any previous scenario's package through the normal deletion path.
    configure(mode="deleted")
    fetch_repository(2)
    configure(mode="normal", name="boundary-original")
    fetch_repository(2)
    return 2


@given("a boundary package has been fetched")
def boundary_ready(boundary_repository):
    pass


@when(parsers.parse("Storage Service changes the package name to {name}"))
def change_name(name):
    configure(name=name)


@when("Storage Service marks the boundary package deleted")
def deleted():
    configure(mode="deleted")


@when("I fetch the boundary repository")
def fetch_boundary(boundary_repository):
    fetch_repository(boundary_repository)


@then(parsers.parse("the boundary report has one package named {name}"))
def boundary_contents(name):
    rows = report_rows("aip_contents", amss_id=2)
    assert len(rows) == 1, rows
    assert rows[0]["AIP Name"] == name
    assert rows[0]["Size (bytes)"] == "4"
    assert rows[0]["Formats"] == "x-fmt/111 (Plain Text): 1 file"


@then("the boundary report has no packages")
def no_boundary_packages():
    assert report_rows("aip_contents", amss_id=2) == []


@then("the real ingest report still contains three packages")
def unchanged_ingest():
    assert len(report_rows("aip_contents")) == 3


@when(parsers.parse("Storage Service returns {response} for METS"))
def fail_mets(response):
    configure(mode=response)


@when("I start a boundary fetch in the browser")
def launch_boundary(page):
    page.goto("http://aipscan:5000/aggregator/storage_service/2")
    page.get_by_role("button", name="New fetch job").click()


@then(parsers.parse('the browser shows the import error "{message}"'))
def import_error(page, message):
    expect(page.locator("#console")).to_contain_text(message, timeout=90_000)


@then("the browser reports one failed import and allows another fetch")
def failed_completion(page):
    expect(page.locator("#console")).to_contain_text(
        "METS download completed with 1 failed imports", timeout=90_000
    )
    expect(page.get_by_role("button", name="New fetch job")).to_be_enabled(
        timeout=90_000
    )


@when("Storage Service fails after the connection probe")
def fail_listing():
    configure(mode="listing-failure")


@then("the browser shows a package listing failure and allows another fetch")
def listing_error(page):
    expect(page.locator("#console")).to_contain_text(
        "FAILURE downloading package lists", timeout=90_000
    )
    expect(page.locator("#console")).not_to_contain_text("Downloading AIP METS files")
    expect(page.get_by_role("button", name="New fetch job")).to_be_enabled()


@when("Storage Service recovers")
def recovered():
    configure(mode="normal")


@then("the browser reports successful METS completion")
def completed(page):
    expect(page.locator("#console")).to_contain_text(
        "METS download completed", timeout=90_000
    )
    expect(page.locator("#console")).not_to_contain_text("FAILURE")


@then("the image format report counts ten original files")
def image_formats():
    rows = report_rows("report_formats_count", amss_id=2)
    assert len(rows) == 10, rows
    assert sum(int(row["Count"]) for row in rows) == 10
    assert sum(int(row["Size (bytes)"]) for row in rows) == 12_017_244


@then("the format reports count the file with zero known bytes")
def missing_sizes():
    for report in ["report_formats_count", "report_format_versions_count"]:
        rows = report_rows(report, amss_id=2)
        assert len(rows) == 1, rows
        assert rows[0]["Count"] == "1"
        assert rows[0]["Size (bytes)"] == "0"
        if os.getenv("AIPSCAN_INDEXED") == "1":
            assert rows == report_rows(report, prefix="/sql", amss_id=2)


@then("the format reports count 1200 files with 4794 bytes")
def large_format_totals():
    for report in ["report_formats_count", "report_format_versions_count"]:
        rows = report_rows(report, amss_id=2)
        assert len(rows) == 1, rows
        assert rows[0]["Count"] == "1200"
        assert rows[0]["Size (bytes)"] == "4794"
        if os.getenv("AIPSCAN_INDEXED") == "1":
            assert rows == report_rows(report, prefix="/sql", amss_id=2)


@then("the image file report contains six preservation files")
def preservation_files():
    filters = {"amss_id": 2, "file_type": "preservation"}
    rows = report_rows("largest_files", **filters)
    assert len(rows) == 6, rows
    assert {row["Type"] for row in rows} == {"preservation"}
    assert sum(int(row["Size (bytes)"]) for row in rows) == 8_335_888
    if os.getenv("AIPSCAN_INDEXED") == "1":
        assert rows == report_rows("largest_files", prefix="/sql", **filters)
        versions = report_rows("report_format_versions_count", amss_id=2)
        sql_versions = report_rows(
            "report_format_versions_count", prefix="/sql", amss_id=2
        )
        assert versions == sql_versions
        assert any(row["Version"] for row in versions), versions
