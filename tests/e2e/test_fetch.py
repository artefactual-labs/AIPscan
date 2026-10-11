"""Observe jobs through their HTTP endpoints and the real browser UI."""

from playwright.sync_api import expect
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from workflow import fetch_repository
from workflow import report_rows
from workflow import request

scenarios("features/fetch.feature")


@when("I fetch the repository again", target_fixture="fetch_job")
def repeat_fetch():
    return fetch_repository()


@then("all three imports finish successfully")
def successful_imports(fetch_job):
    assert len(fetch_job["imports"]) == 3, fetch_job
    assert {row["state"] for row in fetch_job["imports"]} == {"SUCCESS"}


@then("the report still contains exactly the three packages")
def unchanged_contents(imported_repository):
    rows = report_rows("aip_contents")
    assert len(rows) == 3, rows
    assert {row["UUID"] for row in rows} == set(imported_repository.values())
    assert sorted(int(row["Size (bytes)"]) for row in rows) == [4, 4, 25]


@then("the fetch job has a recorded duration")
def recorded_duration(fetch_job):
    from lxml import html

    page = html.fromstring(
        request("GET", "http://aipscan:5000/aggregator/storage_service/1").text
    )
    row = page.xpath(f"//tr[.//*[@id='stats-{fetch_job['fetchJobId']}']]")[0]
    assert row.xpath("./td[2]/text()")[0].strip()


@when("I start a fetch using the New fetch job button", target_fixture="previous_jobs")
def launch_fetch(page):
    page.goto("http://aipscan:5000/aggregator/storage_service/1")
    jobs = page.locator("#infotable tr").count()
    with page.expect_response(
        lambda response: (
            "/aggregator/new_fetch_job/" in response.url
            and response.request.method == "POST"
        )
    ) as response:
        page.get_by_role("button", name="New fetch job").click()
    return {"count": jobs, "id": response.value.json()["fetchJobId"]}


@then("the browser reports that METS downloads completed")
def browser_completed(page):
    expect(page.locator("#console")).to_contain_text(
        "METS download completed", timeout=180_000
    )
    expect(page.locator("#console")).not_to_contain_text("FAILURE")


@then("the new job shows a duration and no new AIPs")
def browser_job_row(page, previous_jobs):
    expect(page.locator("#infotable tr")).to_have_count(
        previous_jobs["count"] + 1, timeout=90_000
    )
    row = page.locator("#infotable tr").filter(
        has=page.locator(f"#stats-{previous_jobs['id']}")
    )
    expect(row.locator("td").nth(1)).not_to_be_empty()
    expect(row.locator("td").nth(3)).to_have_text("0")
    expect(page.get_by_role("button", name="New fetch job")).to_be_enabled()


@when(
    parsers.parse("I export AIPs created between {start} and {end}"),
    target_fixture="filtered_rows",
)
def filter_dates(start, end):
    return report_rows("aip_contents", start_date=start, end_date=end)


@then("only the legacy and unidentified packages are included")
def legacy_dates(filtered_rows, imported_repository):
    assert {row["UUID"] for row in filtered_rows} == {
        imported_repository["legacy"],
        imported_repository["unknown"],
    }


@then("no packages are included")
def empty_report(filtered_rows):
    assert filtered_rows == []
