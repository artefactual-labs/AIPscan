"""Tests for custom Flask CLI commands."""

import pytest

from AIPscan import create_app
from AIPscan import db
from AIPscan.models import StorageService


@pytest.fixture
def cli_app():
    app = create_app("test")
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    try:
        yield app
    finally:
        db.session.remove()
        db.drop_all()
        ctx.pop()


def _run_bootstrap(runner, **kwargs):
    args = ["storage-service-bootstrap"]
    for key, value in kwargs.items():
        if isinstance(value, bool):
            if value:
                args.append(f"--{key.replace('_', '-')}")
            continue
        args.extend([f"--{key.replace('_', '-')}", str(value)])
    return runner.invoke(args=args)


def test_storage_service_bootstrap_creates_storage_service(cli_app):
    runner = cli_app.test_cli_runner()

    result = _run_bootstrap(
        runner,
        name="Primary",
        url="https://storage.example.org",
        username="demo",
        api_key="abc123",
        default=True,
    )

    assert result.exit_code == 0

    storage_service = StorageService.query.filter_by(name="Primary").one()
    assert storage_service.url == "https://storage.example.org"
    assert storage_service.user_name == "demo"
    assert storage_service.api_key == "abc123"
    assert storage_service.default is True
    assert storage_service.download_limit == 20
    assert storage_service.download_offset == 0


def test_storage_service_bootstrap_is_idempotent(cli_app):
    runner = cli_app.test_cli_runner()

    _run_bootstrap(
        runner,
        name="Primary",
        url="https://storage.example.org",
        username="demo",
        api_key="abc123",
        default=True,
    )

    result = _run_bootstrap(
        runner,
        name="Primary",
        url="https://storage.example.org",
        username="demo",
        api_key="abc123",
    )

    assert result.exit_code == 0
    assert StorageService.query.count() == 1


def test_storage_service_bootstrap_updates_default_flag(cli_app):
    runner = cli_app.test_cli_runner()

    _run_bootstrap(
        runner,
        name="Primary",
        url="https://storage.example.org",
        username="demo",
        api_key="abc123",
    )

    _run_bootstrap(
        runner,
        name="Secondary",
        url="https://storage.example.net",
        username="demo",
        api_key="xyz789",
        default=True,
    )

    primary = StorageService.query.filter_by(name="Primary").one()
    secondary = StorageService.query.filter_by(name="Secondary").one()

    assert primary.default is False
    assert secondary.default is True


def test_storage_service_bootstrap_updates_existing_credentials(cli_app):
    runner = cli_app.test_cli_runner()

    _run_bootstrap(
        runner,
        name="Primary",
        url="https://storage.example.org",
        username="demo",
        api_key="abc123",
    )

    result = _run_bootstrap(
        runner,
        name="Primary",
        url="https://storage.example.com",
        username="demo2",
        api_key="xyz789",
    )

    assert result.exit_code == 0

    storage_service = StorageService.query.filter_by(name="Primary").one()
    assert storage_service.url == "https://storage.example.com"
    assert storage_service.user_name == "demo2"
    assert storage_service.api_key == "xyz789"
