"""This module defines shared AIPscan pytest fixtures."""

import uuid
from datetime import datetime

import pytest
from flask import current_app

from AIPscan import create_app
from AIPscan import db
from AIPscan import test_helpers
from AIPscan.models import FileType

AIP_DATE_FORMAT = "%Y-%m-%d"

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
AIP_3_CREATION_DATE = "2021-05-31"

AIP_1_NAME = "TestAIP1"
AIP_2_NAME = "TestAIP2"
AIP_3_NAME = "TestAIP3"

AIP_1_UUID = "111111111111-1111-1111-11111111"
AIP_2_UUID = "222222222222-2222-2222-22222222"
AIP_3_UUID = "333333333333-3333-3333-33333333"

ORIGINAL_FILE_1_NAME = "original-file-1.jpg"
ORIGINAL_FILE_1_UUID = "333333333333-3333-3333-33333333"

ORIGINAL_FILE_2_NAME = "original-file-2.jpg"
ORIGINAL_FILE_2_UUID = "444444444444-4444-4444-44444444"

ORIGIN_PIPELINE_UUID = "777777777777-7777-7777-77777777"
ORIGIN_PIPELINE = f"/api/v2/pipeline/{ORIGIN_PIPELINE_UUID}/"

PRESERVATION_FILE_1_NAME = "preservation-file-1.tif"
PRESERVATION_FILE_2_NAME = "preservation-file-2.tif"

PRESERVATION_FILE_1_UUID = "555555555555-5555-5555-55555555"
PRESERVATION_FILE_2_UUID = "666666666666-6666-6666-66666666"

PRESERVATION_FORMAT = "Very special preservation format"
PRESERVATION_PUID = "fmt/000"

PUID_1 = "fmt/43"
PUID_2 = "fmt/61"
PUID_3 = "x-fmt/111"

STORAGE_LOCATION_1_UUID = "2bbcea40-eb4d-4076-a81d-1ab046e34f6a"
STORAGE_LOCATION_1_CURRENT_LOCATION = f"/api/v2/location/{STORAGE_LOCATION_1_UUID}/"
STORAGE_LOCATION_1_DESCRIPTION = "AIP Store Location 1"

STORAGE_LOCATION_2_UUID = "e69beb57-0e32-4c45-8db7-9b7723724a05"
STORAGE_LOCATION_2_CURRENT_LOCATION = f"/api/v2/location/{STORAGE_LOCATION_2_UUID}/"
STORAGE_LOCATION_2_DESCRIPTION = "AIP Store Location 2"

STORAGE_SERVICE_NAME = "Test Storage Service"


@pytest.fixture
def app_instance(scope="session"):
    """Pytest fixture that returns an instance of our application.

    This fixture provides a Flask application context for tests using
    AIPscan's test configuration.

    This pattern can be extended in additional fixtures to, e.g. load
    state to the test database from a fixture as needed for tests.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


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
        storage_location = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id
        )
        _ = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        _ = test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            create_date=AIP_CREATION_TIME,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
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
            event_type="ingestion",
            date=INGEST_EVENT_CREATION_TIME,
            file_id=original_file.id,
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
        storage_location = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id
        )
        _ = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        _ = test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            create_date=AIP_CREATION_TIME,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
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
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service()
        storage_location = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id
        )
        _ = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        aip1 = test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            create_date=datetime.strptime(AIP_1_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
            fetch_job_id=fetch_job.id,
        )

        aip2 = test_helpers.create_test_aip(
            uuid=AIP_2_UUID,
            create_date=datetime.strptime(AIP_2_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
            fetch_job_id=fetch_job.id,
        )

        _ = test_helpers.create_test_file(
            size=ORIGINAL_FILE_SIZE,
            uuid=ORIGINAL_FILE_1_UUID,
            name="original.jpg",
            puid=JPEG_1_01_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_01_FORMAT_VERSION,
            aip_id=aip1.id,
        )

        _ = test_helpers.create_test_file(
            size=PRESERVATION_FILE_SIZE,
            uuid=PRESERVATION_FILE_1_UUID,
            name="preservation.jpg",
            puid=JPEG_1_02_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_02_FORMAT_VERSION,
            aip_id=aip2.id,
        )

        _ = test_helpers.create_test_file(
            size=None,
            uuid=ORIGINAL_FILE_2_UUID,
            name="original.iso",
            puid="fmt/468",
            file_format="ISO Disk Image File",
            format_version=None,
            aip_id=aip2.id,
        )

        yield app

        db.drop_all()


@pytest.fixture
def preservation_derivatives(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the report_data.preservation_derivatives endpoint.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service(
            name=STORAGE_SERVICE_NAME
        )
        storage_location = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id
        )
        _ = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        aip1 = test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            transfer_name=AIP_1_NAME,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
            fetch_job_id=fetch_job.id,
        )
        aip2 = test_helpers.create_test_aip(
            uuid=AIP_2_UUID,
            transfer_name=AIP_2_NAME,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
            fetch_job_id=fetch_job.id,
        )

        original_file1 = test_helpers.create_test_file(
            file_type=FileType.original,
            name=ORIGINAL_FILE_1_NAME,
            uuid=ORIGINAL_FILE_1_UUID,
            size=ORIGINAL_FILE_SIZE,
            puid=JPEG_1_01_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_01_FORMAT_VERSION,
            aip_id=aip1.id,
        )
        original_file2 = test_helpers.create_test_file(
            file_type=FileType.original,
            name=ORIGINAL_FILE_2_NAME,
            uuid=ORIGINAL_FILE_2_UUID,
            size=ORIGINAL_FILE_SIZE,
            puid=JPEG_1_02_PUID,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_02_FORMAT_VERSION,
            aip_id=aip2.id,
        )

        _ = test_helpers.create_test_file(
            file_type=FileType.preservation,
            name=PRESERVATION_FILE_1_NAME,
            uuid=PRESERVATION_FILE_1_UUID,
            size=PRESERVATION_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
            original_file_id=original_file1.id,
            aip_id=aip1.id,
        )
        _ = test_helpers.create_test_file(
            file_type=FileType.preservation,
            name=PRESERVATION_FILE_2_NAME,
            uuid=PRESERVATION_FILE_2_UUID,
            size=PRESERVATION_FILE_SIZE,
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
            original_file_id=original_file2.id,
            aip_id=aip2.id,
        )

        yield app

        db.drop_all()


@pytest.fixture
def aip_contents(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the Data.aips_by_file_format and Data.aips_by_puid endpoints.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service()
        storage_location = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id
        )
        _ = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        aip1 = test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            create_date=datetime.strptime(AIP_1_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
            fetch_job_id=fetch_job.id,
        )

        aip2 = test_helpers.create_test_aip(
            uuid=AIP_2_UUID,
            create_date=datetime.strptime(AIP_2_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location.id,
            fetch_job_id=fetch_job.id,
        )

        # Create files associated with AIP 1 :
        # - One file with PUID_1
        # - One file with PUID_2
        _ = test_helpers.create_test_file(puid=PUID_1, aip_id=aip1.id)
        _ = test_helpers.create_test_file(puid=PUID_2, aip_id=aip1.id)

        # Create files associated with AIP 2:
        # - Two files with PUID_2
        # - Three files with PUID_3
        _ = test_helpers.create_test_file(puid=PUID_2, aip_id=aip2.id)
        _ = test_helpers.create_test_file(puid=PUID_2, aip_id=aip2.id)
        _ = test_helpers.create_test_file(puid=PUID_3, aip_id=aip2.id)
        _ = test_helpers.create_test_file(puid=PUID_3, aip_id=aip2.id)
        _ = test_helpers.create_test_file(puid=PUID_3, aip_id=aip2.id)

        yield app

        db.drop_all()


@pytest.fixture
def largest_aips(scope="package"):
    """Fixture with pre-populated data.

    This fixture is used to create expected state which is then used to
    test the Data.report_data.largest_aips endpoint.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service()
        storage_location_1 = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id, description="storage location 1"
        )
        storage_location_2 = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id,
            description="storage location 2",
            current_location="/api/v2/location/test-location-2/",
        )
        _ = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        # Create two AIPs in first storage location.
        test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            create_date=datetime.strptime(AIP_1_CREATION_DATE, AIP_DATE_FORMAT),
            size=10000,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location_1.id,
            fetch_job_id=fetch_job.id,
        )

        test_helpers.create_test_aip(
            uuid=AIP_2_UUID,
            create_date=datetime.strptime(AIP_2_CREATION_DATE, AIP_DATE_FORMAT),
            size=250,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location_1.id,
            fetch_job_id=fetch_job.id,
        )

        # Create three AIPS in second storage location.
        test_helpers.create_test_aip(
            uuid=AIP_3_UUID,
            create_date=datetime.strptime(AIP_3_CREATION_DATE, AIP_DATE_FORMAT),
            size=500,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location_2.id,
            fetch_job_id=fetch_job.id,
        )

        test_helpers.create_test_aip(
            uuid=str(uuid.uuid4()),
            create_date=datetime.strptime(AIP_3_CREATION_DATE, AIP_DATE_FORMAT),
            size=25,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location_2.id,
            fetch_job_id=fetch_job.id,
        )

        test_helpers.create_test_aip(
            uuid=str(uuid.uuid4()),
            create_date=datetime.strptime(AIP_3_CREATION_DATE, AIP_DATE_FORMAT),
            size=750,
            storage_service_id=storage_service.id,
            storage_location_id=storage_location_2.id,
            fetch_job_id=fetch_job.id,
        )

        yield app

        db.drop_all()


@pytest.fixture
def storage_locations(scope="package"):
    """Fixture with pre-populated Storage locations."""
    app = create_app("test")
    with app.app_context():
        db.create_all()

        storage_service = test_helpers.create_test_storage_service()
        storage_location1 = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id,
            current_location=STORAGE_LOCATION_1_CURRENT_LOCATION,
            description=STORAGE_LOCATION_1_DESCRIPTION,
        )
        storage_location2 = test_helpers.create_test_storage_location(
            storage_service_id=storage_service.id,
            current_location=STORAGE_LOCATION_2_CURRENT_LOCATION,
            description=STORAGE_LOCATION_2_DESCRIPTION,
        )
        _ = test_helpers.create_test_pipeline(
            origin_pipeline=ORIGIN_PIPELINE, storage_service_id=storage_service.id
        )
        fetch_job = test_helpers.create_test_fetch_job(
            storage_service_id=storage_service.id
        )

        # Create two AIPs associated with Storage Location 1.
        aip1 = test_helpers.create_test_aip(
            uuid=AIP_1_UUID,
            transfer_name=AIP_1_NAME,
            create_date=datetime.strptime(AIP_1_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location1.id,
            fetch_job_id=fetch_job.id,
        )
        aip2 = test_helpers.create_test_aip(
            uuid=AIP_2_UUID,
            transfer_name=AIP_2_NAME,
            create_date=datetime.strptime(AIP_2_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location1.id,
            fetch_job_id=fetch_job.id,
        )

        # Create one AIP associated with Storage Location 2.
        aip3 = test_helpers.create_test_aip(
            uuid=AIP_3_UUID,
            transfer_name=AIP_3_NAME,
            create_date=datetime.strptime(AIP_3_CREATION_DATE, AIP_DATE_FORMAT),
            storage_service_id=storage_service.id,
            storage_location_id=storage_location2.id,
            fetch_job_id=fetch_job.id,
        )

        # Create files associated with AIP 1, each 300 bytes, plus empty file:
        _ = test_helpers.create_test_file(
            size=0, file_type=FileType.original, file_format="txt", aip_id=aip1.id
        )
        _ = test_helpers.create_test_file(
            size=300,
            file_type=FileType.preservation,
            file_format=TIFF_FILE_FORMAT,
            puid=TIFF_PUID,
            aip_id=aip1.id,
        )
        _ = test_helpers.create_test_file(
            size=300,
            file_type=FileType.original,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_01_FORMAT_VERSION,
            puid=JPEG_1_01_PUID,
            aip_id=aip1.id,
        )

        # Create a file associated with AIP 2 of 1000 bytes:
        _ = test_helpers.create_test_file(
            size=1000,
            file_type=FileType.original,
            file_format=JPEG_FILE_FORMAT,
            format_version=JPEG_1_02_FORMAT_VERSION,
            puid=JPEG_1_02_PUID,
            aip_id=aip2.id,
        )

        # Create files associated with AIP 3, each 2500 bytes, plus empty file:
        _ = test_helpers.create_test_file(
            size=2500,
            file_type=FileType.preservation,
            file_format=PRESERVATION_FORMAT,
            puid=PRESERVATION_PUID,
            aip_id=aip3.id,
        )
        _ = test_helpers.create_test_file(
            size=2500, file_type=FileType.original, aip_id=aip3.id
        )
        _ = test_helpers.create_test_file(
            size=0,
            file_type=FileType.original,
            file_format="yet another format",
            aip_id=aip3.id,
        )

        yield app

        db.drop_all()


@pytest.fixture
def enable_typesense(scope="session"):
    current_app.config["TYPESENSE_API_KEY"] = "x0x0x0x0x0"
