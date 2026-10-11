"""Compare actual SQL and Typesense responses for the same persisted AIPs."""

import pytest
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from workflow import fetch_repository
from workflow import report_rows
from workflow import request

scenarios("features/indexed_reports.feature")


@pytest.fixture
def legacy_format_index(imported_repository):
    request(
        "PATCH",
        "http://typesense:8108/collections/aipscan_file",
        headers={"X-TYPESENSE-API-KEY": "acceptance-tests-only"},
        json={
            "fields": [
                {"name": "format_name", "drop": True},
                {"name": "format_group", "drop": True},
            ]
        },
    )
    try:
        yield
    finally:
        # Rebuild through the application so later cases get the current schema.
        fetch_repository()


@when("the existing index uses the previous format schema")
def old_index(legacy_format_index):
    pass


@when(
    parsers.parse("I export {report} from SQL and Typesense"),
    target_fixture="report_pair",
)
def report_pair(report):
    return report_rows(report, prefix="/sql"), report_rows(report)


@when(
    parsers.parse("I filter formats in {scope} using SQL and Typesense"),
    target_fixture="report_pair",
)
def filtered_pair(scope):
    filters = {
        "legacy dates": {"start_date": "2017-01-01", "end_date": "2017-12-31"},
        "current location": {"storage_location": "1"},
    }[scope]
    return (
        report_rows("report_formats_count", prefix="/sql", **filters),
        report_rows("report_formats_count", **filters),
    )


@then("both reports have the same rows and values")
def equal_reports(report_pair):
    sql, indexed = report_pair
    assert sql, "Expected the imported corpus to produce report rows"

    def normalize(rows):
        return sorted(tuple(sorted(row.items())) for row in rows)

    assert normalize(sql) == normalize(indexed)
