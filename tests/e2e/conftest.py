"""Shared services are supplied by Dagger, never by mocked application code."""

import json
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from pytest_bdd import given
from workflow import HISTORY
from workflow import aip_row
from workflow import configure_storage_service
from workflow import fetch_repository
from workflow import seed_repository
from workflow import wait_for


def pytest_bdd_apply_tag(tag, function):
    if tag == "indexed":
        pytest.mark.skipif(
            os.getenv("AIPSCAN_INDEXED") != "1", reason="Requires the Typesense service"
        )(function)
        return True


@pytest.fixture(scope="session", autouse=True)
def artifact_dir():
    path = Path(os.getenv("AIPSCAN_ARTIFACTS", "output/e2e"))
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def browser_errors():
    return []


@pytest.fixture
def page(browser, browser_errors, artifact_dir, request):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    page.on("pageerror", lambda error: browser_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            browser_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on("requestfailed", lambda req: browser_errors.append(f"Failed: {req.url}"))
    yield page
    failed = any(
        getattr(request.node, f"report_{phase}", None)
        and getattr(request.node, f"report_{phase}").failed
        for phase in ("setup", "call")
    )
    if failed:
        name = re.sub(r"[^a-zA-Z0-9_-]", "_", request.node.name)
        page.screenshot(path=str(artifact_dir / f"{name}.png"), full_page=True)
        context.tracing.stop(path=str(artifact_dir / f"{name}.zip"))
    else:
        context.tracing.stop()
    context.close()


@pytest.fixture(scope="session")
def imported_repository():
    packages = seed_repository()
    configure_storage_service(download_limit="1")
    job = fetch_repository()
    assert len(job["imports"]) == len(packages), job
    for uuid in packages.values():
        wait_for(f"import {uuid}", lambda uuid=uuid: aip_row(uuid), timeout=120)
    return packages


@given("modern and legacy AIPs have been fetched")
def imported_aips(imported_repository):
    pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"report_{report.when}", report)
    if report.failed:
        artifact_dir = item.funcargs.get("artifact_dir")
        if artifact_dir:
            name = re.sub(r"[^a-zA-Z0-9_-]", "_", item.name)
            (artifact_dir / f"{name}-http.json").write_text(
                json.dumps(list(HISTORY), indent=2)
            )
        report.sections.append(
            ("Recent HTTP responses", json.dumps(list(HISTORY), indent=2))
        )
