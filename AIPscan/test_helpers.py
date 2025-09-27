import hashlib
import logging
import os
import time
import uuid
from datetime import datetime
from io import StringIO

import tzlocal

from AIPscan import db
from AIPscan.models import AIP
from AIPscan.models import Agent
from AIPscan.models import Event
from AIPscan.models import EventAgent
from AIPscan.models import FetchJob
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.models import Pipeline
from AIPscan.models import StorageLocation
from AIPscan.models import StorageService
from AIPscan.models import index_tasks

TEST_SHA_256 = "79c16fa9573ec46c5f60fd54b34f314159e0623ca53d8d2f00c5875dbb4e0dfd"


def file_sha256_hash(filepath):
    """Return SHA256 hash for contents of file."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _add_test_object_to_db(test_object):
    """Add and commit test object to database."""
    db.session.add(test_object)
    db.session.commit()


def create_test_storage_service(**kwargs):
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


def create_test_fetch_job(**kwargs):
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


def create_test_storage_location(**kwargs):
    """Create and return a test Storage Location with overridable defaults."""
    storage_location = StorageLocation(
        current_location=kwargs.get(
            "current_location", "/api/v2/location/test-location/"
        ),
        description=kwargs.get("description", "test storage location"),
        storage_service_id=kwargs.get("storage_service_id", 1),
    )
    _add_test_object_to_db(storage_location)
    return storage_location


def create_test_pipeline(**kwargs):
    """Create and return a test Pipeline with overridable defaults."""
    pipeline = Pipeline(
        origin_pipeline=kwargs.get("origin_pipeline", "/api/v2/pipeline/test-pipeline"),
        dashboard_url=kwargs.get("dashboard_url", "http://example.com"),
    )
    _add_test_object_to_db(pipeline)
    return pipeline


def create_test_aip(**kwargs):
    """Create and return a test AIP with overridable defaults."""
    aip = AIP(
        uuid=kwargs.get("uuid", str(uuid.uuid4())),
        transfer_name=kwargs.get("transfer_name", "Test AIP"),
        create_date=kwargs.get("create_date", datetime.now()),
        mets_sha256=kwargs.get("mets_sha256", TEST_SHA_256),
        size=kwargs.get("size", 100),
        storage_service_id=kwargs.get("storage_service_id", 1),
        storage_location_id=kwargs.get("storage_location_id", 1),
        fetch_job_id=kwargs.get("fetch_job_id", 1),
        origin_pipeline_id=kwargs.get("origin_pipeline_id", 1),
    )
    _add_test_object_to_db(aip)
    return aip


def create_test_file(**kwargs):
    """Create and return a test File with overridable defaults."""
    file_ = File(
        name=kwargs.get("name", "file_name.ext"),
        filepath=kwargs.get("filepath", "/path/to/file_name.ext"),
        uuid=kwargs.get("uuid", "222222222222-2222-2222-22222222"),
        file_type=kwargs.get("file_type", FileType.original),
        size=kwargs.get("size", 0),
        date_created=kwargs.get("date_created", datetime.now()),
        puid=kwargs.get("puid", "fmt/test-1"),
        file_format=kwargs.get("file_format", "ACME File Format"),
        format_version=kwargs.get("format_version", "0.0.0"),
        checksum_type=kwargs.get("checksum_type", "test"),
        checksum_value=kwargs.get("checksum_value", "test"),
        original_file_id=kwargs.get("original_file_id", None),
        aip_id=kwargs.get("aip_id", 1),
    )
    _add_test_object_to_db(file_)
    return file_


def create_test_agent(**kwargs):
    """Create and return a test Agent with overridable defaults."""
    agent = Agent(
        linking_type_value=kwargs.get("linking_type_value", "Archivematica user pk-1"),
        agent_type=kwargs.get("agent_type", "Archivematica user"),
        agent_value=kwargs.get(
            "agent_value", 'username="user one", first_name="", last_name=""'
        ),
        storage_service_id=kwargs.get("storage_service_id", 1),
    )
    _add_test_object_to_db(agent)
    return agent


def create_test_event(**kwargs):
    """Create and return a test Event with overridable defaults."""
    event = Event(
        event_type=kwargs.get("type", "ingestion"),
        uuid=kwargs.get("uuid", str(uuid.uuid4())),
        date=kwargs.get("date", datetime.now()),
        detail=kwargs.get("detail", "ingestion detail"),
        outcome=kwargs.get("outcome", "success"),
        outcome_detail=kwargs.get("outcome_detail", "outcome detail"),
        file_id=kwargs.get("file_id", 1),
    )
    _add_test_object_to_db(event)
    return event


def create_test_event_agent(**kwargs):
    """Create and return a test EventAgent relationship with overridable defaults."""
    event_relationship = EventAgent.insert().values(
        event_id=kwargs.get("event_id", 1), agent_id=kwargs.get("agent_id", 1)
    )
    db.session.execute(event_relationship)
    db.session.commit()
    return event_relationship


def create_test_index_tasks(fetch_job_id, task_id):
    index_task_obj = index_tasks(
        index_task_id=task_id, fetch_job_id=fetch_job_id, indexing_start=datetime.now()
    )
    db.session.add(index_task_obj)
    db.session.commit()


def set_timezone(new_tz):
    os.environ["TZ"] = new_tz
    time.tzset()


def set_timezone_and_return_current_timezone(new_tz):
    local_timezone = tzlocal.get_localzone_name()
    set_timezone(new_tz)

    return local_timezone


def add_logger_streamer(logger):
    """Add stream handler to logger and return it."""
    logger.setLevel(logging.DEBUG)

    log_streamer = StringIO()
    handler = logging.StreamHandler(log_streamer)
    logger.addHandler(handler)

    return log_streamer
