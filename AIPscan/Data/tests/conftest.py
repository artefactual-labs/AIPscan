# -*- coding: utf-8 -*-

"""This module defines shared Data blueprint pytest fixtures."""

import uuid
from datetime import datetime

import pytest

from AIPscan import create_app, db
from AIPscan.models import (
    AIP,
    Agent,
    Event,
    EventAgent,
    FetchJob,
    File,
    FileType,
    StorageService,
)

TIFF_FILE_FORMAT = "Tagged Image File Format"
TIFF_PUID = "fmt/353"

JPEG_FILE_FORMAT = "JPEG"

JPEG_1_01_FORMAT_VERSION = "1.01"
JPEG_1_01_PUID = "fmt/43"

JPEG_1_02_FORMAT_VERSION = "1.02"
JPEG_1_02_PUID = "fmt/44"

ORIGINAL_FILE_SIZE = 1000
PRESERVATION_FILE_SIZE = 2000

AIP_1_CREATION_DATE = "2020-01-01"
AIP_2_CREATION_DATE = "2020-06-01"


def _datetime_obj_from_string(date_string, date_only=False):
    """Return a datetime object from a given string to aid in the
    assignment of consistent and reliable test dates.
    """
    str_format = "%Y-%m-%d %H:%M:%S"
    if date_only is True:
        str_format = "%Y-%m-%d"

    return datetime.strptime(date_string, str_format)


INGEST_EVENT_CREATION_TIME = _datetime_obj_from_string("2020-12-02 10:00:00")
AIP_CREATION_TIME = _datetime_obj_from_string("2020-12-02 10:30:32")


def _add_test_object_to_db(test_object):
    """Add and commit test object to database."""
    db.session.add(test_object)
    db.session.commit()


def _create_test_storage_service(**kwargs):
    """Create and return a Storage Service with overridable defaults."""
    storage_service = StorageService(
        name=kwargs.get("name", "test storage service"),
        url=kwargs.get("name", "http://example.com"),
        user_name=kwargs.get("user_name", "test"),
        api_key=kwargs.get("api_key", "test"),
        download_limit=kwargs.get("download_limit", 0),
        download_offset=kwargs.get("download_offset", 10),
        default=kwargs.get("default", True),
    )
    _add_test_object_to_db(storage_service)
    return storage_service


def _create_test_fetch_job(**kwargs):
    """Create and return a test Fetch Job with overridable defaults."""
    fetch_job = FetchJob(
        total_packages=kwargs.get("total_packages", 1),
        total_aips=kwargs.get("total_aips", 1),
        total_deleted_aips=kwargs.get("total_deleted_aips", 0),
        download_start=kwargs.get("download_start", datetime.now()),
        download_end=kwargs.get("download_end", datetime.now()),
        download_directory=kwargs.get("download_directory", "/some/directory/"),
        storage_service_id=kwargs.get("storage_service_id", 1),
    )
    _add_test_object_to_db(fetch_job)
    return fetch_job


def _create_test_aip(**kwargs):
    """Create and return a test AIP with overridable defaults."""
    aip = AIP(
        uuid=kwargs.get("uuid", str(uuid.uuid4())),
        transfer_name=kwargs.get("transfer_name", "Test AIP"),
        create_date=kwargs.get("create_date", datetime.now()),
        storage_service_id=kwargs.get("storage_service_id", 1),
        fetch_job_id=kwargs.get("fetch_job_id", 1),
    )
    _add_test_object_to_db(aip)
    return aip


def _create_test_file(**kwargs):
    """Create and return a test File with overridable defaults."""
    file_ = File(
        name=kwargs.get("name", "file_name.ext"),
        filepath=kwargs.get("filepath", "/path/to/file_name.ext"),
        uuid=kwargs.get("uuid", str(uuid.uuid4())),
        file_type=kwargs.get("file_type", FileType.original),
        size=kwargs.get("size", 0),
        date_created=kwargs.get("date_created", datetime.now()),
        puid=kwargs.get("puid", "fmt/test-1"),
        file_format=kwargs.get("file_format", "ACME File Format"),
        format_version=kwargs.get("format_version", "0.0.0"),
        checksum_type=kwargs.get("checksum_type", "test"),
        checksum_value=kwargs.get("checksum_value", "test"),
        aip_id=kwargs.get("aip_id", 1),
    )
    _add_test_object_to_db(file_)
    return file_


def _create_test_agent(**kwargs):
    """Create and return a test Agent with overridable defaults."""
    agent = Agent(
        linking_type_value=kwargs.get("linking_type_value", "Archivematica user pk-1"),
        agent_type=kwargs.get("agent_type", "Archivematica user"),
        agent_value=kwargs.get(
            "agent_value", 'username="user one", first_name="", last_name=""'
        ),
    )
    _add_test_object_to_db(agent)
    return agent


def _create_test_event(**kwargs):
    """Create and return a test Event with overridable defaults."""
    event = Event(
        type=kwargs.get("type", "ingestion"),
        uuid=kwargs.get("uuid", str(uuid.uuid4())),
        date=kwargs.get("date", datetime.now()),
        detail=kwargs.get("detail", "ingestion detail"),
        outcome=kwargs.get("outcome", "success"),
        outcome_detail=kwargs.get("outcome_detail", "outcome detail"),
        file_id=kwargs.get("file_id", 1),
    )
    _add_test_object_to_db(event)
    return event


def _create_test_event_agent(**kwargs):
    """Create and return a test EventAgent relationship with overridable defaults."""
    event_relationship = EventAgent.insert().values(
        event_id=kwargs.get("event_id", 1), agent_id=kwargs.get("agent_id", 1)
    )
    db.session.execute(event_relationship)
    db.session.commit()
    return event_relationship


@pytest.fixture
def app_with_populated_files(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the Data.aips_by_file_format and Data.aips_by_puid endpoints.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = _create_test_storage_service()
        fetch_job = _create_test_fetch_job(storage_service_id=storage_service.id)

        _ = _create_test_aip(
            uuid="111111111111-1111-1111-11111111",
            create_date=AIP_CREATION_TIME,
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        original_file = _create_test_file(
            file_type=FileType.original,
            size=ORIGINAL_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
        )

        _ = _create_test_file(
            file_type=FileType.preservation,
            size=PRESERVATION_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
        )

        user_agent = _create_test_agent()

        event = _create_test_event(
            type="ingestion", date=INGEST_EVENT_CREATION_TIME, file_id=original_file.id
        )

        _ = _create_test_event_agent(event_id=event.id, agent_id=user_agent.id)

        yield app

        db.drop_all()


@pytest.fixture
def app_with_populated_format_versions(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the Data.format_versions_count endpoint.
    """
    AIP_DATE_FORMAT = "%Y-%m-%d"

    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = _create_test_storage_service()
        fetch_job = _create_test_fetch_job(storage_service_id=storage_service.id)

        aip1 = _create_test_aip(
            create_date=datetime.strptime(AIP_1_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        aip2 = _create_test_aip(
            create_date=datetime.strptime(AIP_2_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        _ = _create_test_file(
            size=ORIGINAL_FILE_SIZE,
            puid=JPEG_1_01_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_01_FORMAT_VERSION,
            aip_id=aip1.id,
        )

        _ = _create_test_file(
            size=PRESERVATION_FILE_SIZE,
            puid=JPEG_1_02_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_02_FORMAT_VERSION,
            aip_id=aip2.id,
        )

        _ = _create_test_file(
            size=None,
            puid="fmt/468",
            file_format="ISO Disk Image File",
            format_version=None,
            aip_id=aip2.id,
        )

        yield app

        db.drop_all()
