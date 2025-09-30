"""Application command-line interface helpers."""

import time

import click
import sqlalchemy as sa
from flask.cli import with_appcontext
from sqlalchemy.exc import SQLAlchemyError

from AIPscan import db
from AIPscan.models import StorageService

DEFAULT_DOWNLOAD_LIMIT = 20
DEFAULT_DOWNLOAD_OFFSET = 0
WRITE_RETRY_ATTEMPTS = 3
WRITE_RETRY_DELAY_SECONDS = 2


def register_cli(app):
    """Register custom CLI commands with the Flask app."""

    app.cli.add_command(storage_service_bootstrap)


@click.command("storage-service-bootstrap")
@click.option("--name", required=True, help="Storage Service name")
@click.option("--url", required=True, help="Storage Service base URL")
@click.option("--username", required=True, help="Storage Service API username")
@click.option("--api-key", required=True, help="Storage Service API key")
@click.option(
    "--default",
    "make_default",
    is_flag=True,
    default=False,
    help="Mark this Storage Service as the default",
)
@click.option(
    "--wait",
    is_flag=True,
    help="Retry database connection until it becomes available.",
)
@click.option(
    "--wait-timeout",
    type=int,
    default=60,
    show_default=True,
    help="Maximum seconds to wait for the database when --wait is set.",
)
@with_appcontext
def storage_service_bootstrap(
    name, url, username, api_key, make_default, wait, wait_timeout
):
    """Create or update a Storage Service from CLI parameters."""

    if wait:
        _wait_for_database(wait_timeout)

    attempts_remaining = WRITE_RETRY_ATTEMPTS
    last_exception = None

    while attempts_remaining > 0:
        try:
            storage_service = _load_storage_service(name)

            if storage_service:
                message = _update_storage_service(
                    storage_service, url, username, api_key, make_default
                )
                if message is None:
                    click.echo(f"Storage service '{name}' already up to date.")
                    return

                db.session.commit()
                click.echo(message)
                return

            message = _create_storage_service(
                name, url, username, api_key, make_default
            )
            db.session.commit()
            click.echo(message)
            return
        except SQLAlchemyError as exc:
            db.session.rollback()
            last_exception = exc
            attempts_remaining -= 1
            if attempts_remaining == 0:
                break
            _wait_before_retry(wait, wait_timeout)

    raise click.ClickException(
        "Failed to write storage service; database not ready?"
    ) from last_exception


def _clear_default_flags(exclude_ids=None):
    """Unset the default flag for all storage services except excluded ones."""

    exclude_ids = list(exclude_ids or [])

    stmt = sa.update(StorageService).values(default=False)
    if exclude_ids:
        stmt = stmt.where(StorageService.id.notin_(exclude_ids))

    db.session.execute(stmt)


def _load_storage_service(name):
    stmt = sa.select(StorageService).where(StorageService.name == name)
    return db.session.execute(stmt).scalar_one_or_none()


def _update_storage_service(storage_service, url, username, api_key, make_default):
    changes = []
    for attr, value in ("url", url), ("user_name", username), ("api_key", api_key):
        if getattr(storage_service, attr) != value:
            setattr(storage_service, attr, value)
            changes.append(attr)

    if make_default and not storage_service.default:
        _clear_default_flags(exclude_ids=[storage_service.id])
        storage_service.default = True
        changes.append("default")

    if not changes:
        return None

    return f"Storage service '{storage_service.name}' updated ({', '.join(changes)})."


def _create_storage_service(name, url, username, api_key, make_default):
    if make_default:
        _clear_default_flags()

    storage_service = StorageService(
        name=name,
        url=url,
        user_name=username,
        api_key=api_key,
        download_limit=DEFAULT_DOWNLOAD_LIMIT,
        download_offset=DEFAULT_DOWNLOAD_OFFSET,
        default=make_default,
    )
    db.session.add(storage_service)
    return f"Storage service '{name}' created."


def _wait_before_retry(wait_enabled, wait_timeout):
    delay = WRITE_RETRY_DELAY_SECONDS
    if wait_enabled:
        delay = min(wait_timeout, WRITE_RETRY_DELAY_SECONDS)

    time.sleep(max(1, delay))


def _wait_for_database(timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            db.session.execute(sa.select(1))
            return
        except SQLAlchemyError as err:
            db.session.rollback()
            if time.monotonic() >= deadline:
                raise click.ClickException(
                    "Database not available within wait timeout."
                ) from err
            time.sleep(1)
