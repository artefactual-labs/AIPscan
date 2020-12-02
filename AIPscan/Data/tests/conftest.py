# -*- coding: utf-8 -*-

"""This module defines shared Data blueprint pytest fixtures."""

from datetime import datetime
import pytest

from AIPscan import db, create_app
from AIPscan.models import (
    Agent,
    AIP,
    Event,
    EventAgent,
    FetchJob,
    File,
    FileType,
    StorageService,
)


TIFF_FILE_FORMAT = "Tagged Image File Format"
TIFF_PUID = "fmt/353"

ORIGINAL_FILE_SIZE = 1000
PRESERVATION_FILE_SIZE = 2000


def _datetime_obj_from_string(date_string):
    """Return a datetime object from a given string to aid in the
    assignment of consistent and reliable test dates.
    """
    return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")


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

        storage_service = StorageService(
            name="test storage service",
            url="http://example.com",
            user_name="test",
            api_key="test",
            download_limit=20,
            download_offset=10,
            default=True,
        )
        db.session.add(storage_service)
        db.session.commit()

        fetch_job = FetchJob(
            total_packages=1,
            total_aips=1,
            total_deleted_aips=0,
            download_start=datetime.now(),
            download_end=datetime.now(),
            download_directory="/some/dir",
            storage_service_id=storage_service.id,
        )
        db.session.add(fetch_job)
        db.session.commit()

        aip = AIP(
            uuid="111111111111-1111-1111-11111111",
            transfer_name="test aip",
            create_date=AIP_CREATION_TIME,
            storage_service_id=storage_service.id,
            fetch_job_id=fetch_job.id,
        )
        db.session.add(aip)
        db.session.commit()

        original_file = File(
            name="original.tif",
            filepath="/path/to/original.tif",
            uuid="111111111111-1111-1111-11111111",
            file_type=FileType.original,
            size=ORIGINAL_FILE_SIZE,
            date_created=datetime.now(),
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
            checksum_type="test",
            checksum_value="test",
            aip_id=1,
        )
        preservation_file = File(
            name="preservation.tif",
            filepath="/path/to/preservation.tif",
            uuid="222222222222-2222-2222-22222222",
            file_type=FileType.preservation,
            size=PRESERVATION_FILE_SIZE,
            date_created=datetime.now(),
            puid=TIFF_PUID,
            file_format=TIFF_FILE_FORMAT,
            checksum_type="test",
            checksum_value="test",
            aip_id=1,
        )
        db.session.add(preservation_file)
        db.session.add(original_file)
        db.session.commit()

        user_agent = Agent(
            linking_type_value="Archivematica user pk-1",
            agent_type="Archivematica user",
            agent_value='username="user one", first_name="", last_name=""',
        )

        event = Event(
            type="ingestion",
            uuid="333333333333-3333-3333-33333333",
            date=INGEST_EVENT_CREATION_TIME,
            detail="ingestion detail",
            outcome="success",
            outcome_detail="outcome detail",
            file_id=original_file.id,
        )

        db.session.add(user_agent)
        db.session.add(event)

        db.session.commit()

        event_relationship = EventAgent.insert().values(
            event_id=event.id, agent_id=user_agent.id
        )

        db.session.execute(event_relationship)
        db.session.commit()

        yield app

        db.drop_all()
