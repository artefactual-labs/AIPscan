"""Acceptance steps describe observable reports, not implementation details."""

import charts
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from workflow import aip_row
from workflow import report_rows

scenarios("features/reports.feature")


@when(
    parsers.parse("I export AIP contents for the {package} package"),
    target_fixture="contents",
)
def export_contents(imported_repository, package):
    return aip_row(imported_repository[package])


@then(parsers.parse('its name is "{name}"'))
def package_name(contents, name):
    assert contents["AIP Name"] == name


@then(parsers.parse("its original files total {size:d} bytes"))
def package_size(contents, size):
    assert int(contents["Size (bytes)"]) == size


@then(parsers.parse('its formats are "{formats}"'))
def package_formats(contents, formats):
    assert contents["Formats"] == formats


@when("I export the format count report", target_fixture="formats")
def export_formats():
    return {
        row["Format"]: (int(row["Count"]), int(row["Size (bytes)"]))
        for row in report_rows("report_formats_count")
    }


@then(parsers.parse("plain text originals total {count:d} files and {size:d} bytes"))
def text_totals(formats, count, size):
    assert formats["Plain Text"] == (count, size)


@then(parsers.parse("unidentified originals total {count:d} file and {size:d} bytes"))
def unknown_totals(formats, count, size):
    assert formats["Unknown"] == (count, size)


@then("there are no other formats")
def format_names(formats):
    assert set(formats) == {"Plain Text", "Unknown"}


@then(parsers.parse("the {chart} chart shows the imported data without browser errors"))
def chart_data(chart, page, browser_errors):
    checks = {
        "pie": charts.pie,
        "scatter": charts.scatter,
        "timeline": charts.timeline,
        "time series": charts.time_series,
    }
    checks[chart](page, browser_errors)
    assert not browser_errors, browser_errors
