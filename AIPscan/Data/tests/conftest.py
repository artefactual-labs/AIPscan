# -*- coding: utf-8 -*-

"""This module defines shared Data blueprint pytest fixtures."""

from datetime import datetime

import pytest

from AIPscan import create_app, db, test_helpers
from AIPscan.models import FileType

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


@pytest.fixture
def app_with_populated_files(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the Data.aips_by_file_format and Data.aips_by_puid endpoints.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service()
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        _ = test_helpers.create_test_aip(
            uuid="111111111111-1111-1111-11111111",
            create_date=AIP_CREATION_TIME,
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        original_file = test_helpers.create_test_file(
            file_type=FileType.original,
            size=ORIGINAL_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
        )

        _ = test_helpers.create_test_file(
            file_type=FileType.preservation,
            size=PRESERVATION_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
        )

        user_agent = test_helpers.create_test_agent()

        event = test_helpers.create_test_event(
            type="ingestion", date=INGEST_EVENT_CREATION_TIME, file_id=original_file.id
        )

        _ = test_helpers.create_test_event_agent(
            event_id=event.id, agent_id=user_agent.id
        )

        yield app

        db.drop_all()


@pytest.fixture
def app_with_populated_files_no_ingestion_event(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the Data.aips_by_file_format and Data.aips_by_puid endpoints.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service()
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        _ = test_helpers.create_test_aip(
            uuid="111111111111-1111-1111-11111111",
            create_date=AIP_CREATION_TIME,
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        test_helpers.create_test_file(
            file_type=FileType.original,
            size=ORIGINAL_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
        )

        _ = test_helpers.create_test_file(
            file_type=FileType.preservation,
            size=PRESERVATION_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
        )

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

        storage_service = test_helpers.create_test_storage_service()
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        aip1 = test_helpers.create_test_aip(
            create_date=datetime.strptime(AIP_1_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        aip2 = test_helpers.create_test_aip(
            create_date=datetime.strptime(AIP_2_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )

        _ = test_helpers.create_test_file(
            size=ORIGINAL_FILE_SIZE,
            puid=JPEG_1_01_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_01_FORMAT_VERSION,
            aip_id=aip1.id,
        )

        _ = test_helpers.create_test_file(
            size=PRESERVATION_FILE_SIZE,
            puid=JPEG_1_02_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_02_FORMAT_VERSION,
            aip_id=aip2.id,
        )

        _ = test_helpers.create_test_file(
            size=None,
            puid="fmt/468",
            file_format="ISO Disk Image File",
            format_version=None,
            aip_id=aip2.id,
        )

        yield app

        db.drop_all()
