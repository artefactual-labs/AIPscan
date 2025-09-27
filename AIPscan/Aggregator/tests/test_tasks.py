import json
import logging
import os
import uuid
from datetime import datetime

import celery
import pytest

from AIPscan import db
from AIPscan import test_helpers
from AIPscan.Aggregator.tasks import TaskError
from AIPscan.Aggregator.tasks import delete_aip
from AIPscan.Aggregator.tasks import delete_fetch_job
from AIPscan.Aggregator.tasks import delete_storage_service
from AIPscan.Aggregator.tasks import get_mets
from AIPscan.Aggregator.tasks import handle_deletion
from AIPscan.Aggregator.tasks import index_task
from AIPscan.Aggregator.tasks import make_request
from AIPscan.Aggregator.tasks import parse_package_list_file
from AIPscan.Aggregator.tasks import process_packages
from AIPscan.Aggregator.tasks import start_index_task
from AIPscan.Aggregator.tests import INVALID_JSON
from AIPscan.Aggregator.tests import REQUEST_URL
from AIPscan.Aggregator.tests import REQUEST_URL_WITHOUT_API_KEY
from AIPscan.Aggregator.tests import RESPONSE_DICT
from AIPscan.Aggregator.tests import VALID_JSON
from AIPscan.Aggregator.tests import MockResponse
from AIPscan.Aggregator.types import StorageServicePackage
from AIPscan.models import AIP
from AIPscan.models import Agent
from AIPscan.models import FetchJob
from AIPscan.models import StorageService
from AIPscan.models import index_tasks

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")


def _get_aips(storage_service_id):
    """Return queryset of AIPs associated with Storage Service ID."""
    return AIP.query.filter_by(storage_service_id=storage_service_id).all()


@pytest.mark.parametrize(
    "fixture_path, package_uuid",
    [
        # First METS file.
        (
            os.path.join("features_mets", "features-mets.xml"),
            "ab793f82-27b0-4c2e-ac3e-621bab5af8f1",
        ),
        # Another METS file.
        (
            os.path.join("images_mets", "images.xml"),
            "2d718ecf-828a-4487-83ce-873cf9edca1a",
        ),
    ],
)
def test_get_mets_task(app_instance, tmpdir, mocker, fixture_path, package_uuid):
    """Test that fetch jobs after the first don't duplicate content."""
    mets_file = os.path.join(FIXTURES_DIR, fixture_path)

    def mock_download_mets(
        storage_service,
        package_uuid,
        relative_path_to_mets,
        timestamp_str,
        package_list_no,
    ):
        return mets_file, test_helpers.file_sha256_hash(mets_file)

    mocker.patch("AIPscan.Aggregator.tasks.download_mets", mock_download_mets)
    delete_mets_file = mocker.patch("AIPscan.Aggregator.tasks.os.remove")

    storage_service = test_helpers.create_test_storage_service()
    storage_service_id = storage_service.id

    storage_location = test_helpers.create_test_storage_location(
        storage_service_id=storage_service_id
    )
    storage_location_id = storage_location.id

    pipeline = test_helpers.create_test_pipeline(storage_service_id=storage_service_id)
    pipeline_id = pipeline.id

    get_storage_location = mocker.patch(
        "AIPscan.Aggregator.database_helpers.create_or_update_storage_location"
    )
    get_storage_location.return_value = storage_location

    # No AIPs should exist at this point.
    aips = _get_aips(storage_service_id)
    assert not aips

    # Set up custom logger and add handler to capture output
    customlogger = logging.getLogger(__name__)
    log_stream = test_helpers.add_logger_streamer(customlogger)

    # Create AIP and verify record.
    fetch_job1 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service_id
    )
    fetch_job1_id = fetch_job1.id
    get_mets(
        package_uuid=package_uuid,
        aip_size=1000,
        relative_path_to_mets="test",
        timestamp_str=datetime.now()
        .replace(microsecond=0)
        .strftime("%Y-%m-%d-%H-%M-%S"),
        package_list_no=1,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job1_id,
        origin_pipeline_id=pipeline_id,
        customlogger=customlogger,
    )
    aips = _get_aips(storage_service_id)
    assert len(aips) == 1
    fetch_job1_refreshed = db.session.get(FetchJob, fetch_job1_id)
    assert len(fetch_job1_refreshed.aips) == 1

    original_mets_sha256 = aips[0].mets_sha256

    # Try to create AIP again and verify no duplicate is created.
    fetch_job2 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service_id
    )
    fetch_job2_id = fetch_job2.id
    get_mets(
        package_uuid=package_uuid,
        aip_size=1000,
        relative_path_to_mets="test",
        timestamp_str=datetime.now()
        .replace(microsecond=0)
        .strftime("%Y-%m-%d-%H-%M-%S"),
        package_list_no=1,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job2_id,
        origin_pipeline_id=pipeline_id,
    )
    aips = _get_aips(storage_service_id)
    assert len(aips) == 1
    assert aips[0].mets_sha256 == original_mets_sha256
    fetch_job1_refreshed = db.session.get(FetchJob, fetch_job1_id)
    fetch_job2_refreshed = db.session.get(FetchJob, fetch_job2_id)
    assert len(fetch_job1_refreshed.aips) == 1
    assert len(fetch_job2_refreshed.aips) == 0

    # Replace METS with a new METS file and run again. The old AIP record
    # should be deleted and replaced with one from the new METS.
    mets_file = os.path.join(FIXTURES_DIR, "iso_mets", "iso_mets.xml")
    fetch_job3 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service_id
    )
    fetch_job3_id = fetch_job3.id
    get_mets(
        package_uuid=package_uuid,
        aip_size=1000,
        relative_path_to_mets="test",
        timestamp_str=datetime.now()
        .replace(microsecond=0)
        .strftime("%Y-%m-%d-%H-%M-%S"),
        package_list_no=1,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job3_id,
        origin_pipeline_id=pipeline_id,
    )
    aips = _get_aips(storage_service_id)
    assert len(aips) == 1
    assert aips[0].mets_sha256 != original_mets_sha256
    fetch_job1_refreshed = db.session.get(FetchJob, fetch_job1_id)
    fetch_job2_refreshed = db.session.get(FetchJob, fetch_job2_id)
    fetch_job3_refreshed = db.session.get(FetchJob, fetch_job3_id)
    assert len(fetch_job1_refreshed.aips) == 0
    assert len(fetch_job2_refreshed.aips) == 0
    assert len(fetch_job3_refreshed.aips) == 1

    delete_calls = [
        mocker.call(os.path.join(FIXTURES_DIR, fixture_path)),
        mocker.call(mets_file),
    ]
    delete_mets_file.assert_has_calls(delete_calls, any_order=True)
    assert delete_mets_file.call_count == 3

    # Test that custom logger was used
    assert (
        log_stream.getvalue()
        == f"Processing METS file {os.path.basename(fixture_path)}\n"
    )


def test_delete_fetch_job_task(app_instance, tmpdir, mocker):
    """Test that fetch job gets deleted by delete fetch job task logic."""
    storage_service = test_helpers.create_test_storage_service()

    # Create fetch job and confirm expected ID
    fetch_job1 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service.id
    )
    assert fetch_job1.id == 1

    # Create index_tasks instance and confirm expected ID
    task_id = celery.uuid()
    test_helpers.create_test_index_tasks(fetch_job1.id, task_id)

    index_tasks_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job1.id).first()
    assert index_tasks_obj.index_task_id == task_id

    # Delete fetch job and confirm it no longer exists
    delete_fetch_job(fetch_job1.id)

    assert FetchJob.query.filter_by(id=fetch_job1.id).first() is None

    index_tasks_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job1.id).first()
    assert index_tasks_obj is None


def test_delete_storage_service_task(app_instance, tmpdir, mocker):
    """Test that storage service gets deleted by delete storage service job task logic."""
    storage_service = test_helpers.create_test_storage_service()
    test_helpers.create_test_agent()

    assert Agent.query.filter_by(storage_service_id=storage_service.id).count() == 1

    deleted_ss = StorageService.query.filter_by(id=storage_service.id).first()
    assert deleted_ss is not None

    delete_storage_service(storage_service.id)

    deleted_ss = StorageService.query.filter_by(id=storage_service.id).first()
    assert deleted_ss is None
    assert Agent.query.filter_by(storage_service_id=storage_service.id).count() == 0


@pytest.mark.parametrize(
    "response, raises_task_error",
    [
        # Test 200 response with valid JSON.
        (MockResponse(200, VALID_JSON), False),
        # Test 500 response raises TaskError.
        (MockResponse(500, VALID_JSON), True),
        # Test 200 response with invalid JSON raises TaskError.
        (MockResponse(200, INVALID_JSON), True),
    ],
)
def test_make_request(mocker, response, raises_task_error):
    """Test handling of Storage Service response."""
    request = mocker.patch("AIPscan.Aggregator.tasks.requests.get")
    request.return_value = response

    if raises_task_error:
        with pytest.raises(TaskError):
            _ = make_request(REQUEST_URL, REQUEST_URL_WITHOUT_API_KEY)
    else:
        return_dict = make_request(REQUEST_URL, REQUEST_URL_WITHOUT_API_KEY)
        assert return_dict["key"] == RESPONSE_DICT["key"]


def test_parse_package_list_file(tmpdir):
    """Test that JSON package list files are being parsed."""
    json_file_path = tmpdir.join("packages.json")
    json_file_path.write(json.dumps({"objects": []}))

    package = parse_package_list_file(json_file_path, None, True)
    assert "objects" in package

    package_list = package["objects"]
    assert len(package_list) == 0


def test_process_packages_json_file_deletion(app_instance, tmpdir, mocker):
    """Test that JSON package lists are deleted after being parsed."""
    json_file_path = tmpdir.join("packages.json")
    json_file_path.write(json.dumps({"objects": []}))

    delete_package_json = mocker.patch("AIPscan.Aggregator.tasks.os.remove")

    package_list = parse_package_list_file(json_file_path, None, True)

    process_packages(package_list, 1, str(datetime.now()), 1, 1, True)

    delete_package_json.assert_called_with(json_file_path)


def test_process_packages(app_instance, tmpdir, mocker):
    """Test that JSON package lists are deleted after being parsed."""
    aip_package_uuid = str(uuid.uuid4())
    aip_package_data = {
        "uuid": aip_package_uuid,
        "package_type": "AIP",
        "current_path": str(tmpdir),
    }

    deleted_sip_package_uuid = str(uuid.uuid4())
    deleted_sip_package_data = {
        "uuid": deleted_sip_package_uuid,
        "package_type": "SIP",
        "current_path": str(tmpdir),
        "deleted": True,
    }

    # Write test AIP to JSON file (from which to general a list of packages)
    json_file_path = tmpdir.join("packages.json")
    json_file_path.write(
        json.dumps({"objects": [aip_package_data, deleted_sip_package_data]})
    )

    # Get test package list
    package_list = parse_package_list_file(json_file_path, None, True)

    # Process test package list
    mocker.patch(
        "AIPscan.Aggregator.database_helpers.create_or_update_storage_location"
    )
    mocker.patch("AIPscan.Aggregator.database_helpers.create_or_update_pipeline")

    # Set up custom logger and add handler to capture output
    customlogger = logging.getLogger(__name__)
    log_stream = test_helpers.add_logger_streamer(customlogger)

    processed_packages = process_packages(
        package_list, 1, str(datetime.now()), 1, 1, False, customlogger, 1, 1
    )

    # Test that custom logger was used
    assert log_stream.getvalue() == f"Processing {aip_package_uuid} (1 of 1)\n"

    # Make sure only one package was processed and that is was the non-deleted AIP
    assert len(processed_packages) == 1
    assert processed_packages[0].aip is True


def test_handle_deletion(app_instance, mocker):
    """Test that delete handler handles deletion correctly."""
    PACKAGE_UUID = str(uuid.uuid4())

    # Make sure package deleted on storage service gets deleted locally
    package = StorageServicePackage(uuid=PACKAGE_UUID, deleted=True)
    mock_delete_aip = mocker.patch("AIPscan.Aggregator.tasks.delete_aip")

    handle_deletion(package)

    mock_delete_aip.assert_called_with(PACKAGE_UUID)

    # Make sure package not deleted on storage service doesn't get deleted
    package = StorageServicePackage(uuid=PACKAGE_UUID, deleted=False)
    mock_delete_aip = mocker.patch("AIPscan.Aggregator.tasks.delete_aip")

    handle_deletion(package)

    mock_delete_aip.assert_not_called()


def test_delete_aip(app_instance):
    """Test that SS deleted AIPs gets deleted in aipscan.db."""
    PACKAGE_UUID = str(uuid.uuid4())

    test_helpers.create_test_aip(uuid=PACKAGE_UUID)

    # Make sure test AIP exists before deletion
    deleted_aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert deleted_aip is not None

    delete_aip(PACKAGE_UUID)

    # Make sure test AIP doesn't exist after deletion
    deleted_aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert deleted_aip is None


def test_start_index_task(app_instance, mocker):
    """Test that index_tasks record gets create by start index job function logic."""
    # Mock creation of index task
    mock_index_task = mocker.patch("AIPscan.Aggregator.tasks.index_task.delay")

    class MockTask:
        id = 1

    mock_index_task.return_value = MockTask()

    # Create test fetch job
    storage_service = test_helpers.create_test_storage_service()
    storage_service_id = storage_service.id

    fetch_job = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service_id
    )
    fetch_job_id = fetch_job.id

    # At this point no index_tasks should exist for the fetch job
    index_task_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job_id).first()
    assert index_task_obj is None

    # Start mock index task, making sure it got started with the right value
    start_index_task(fetch_job_id)

    mock_index_task.assert_called_with(fetch_job_id)

    # At this point an index_tasks should exist for the fetch job
    index_task_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job_id).first()
    assert type(index_task_obj) is index_tasks


def test_index_task(app_instance, enable_typesense, mocker):
    """Test index task."""
    # Create test fetch job
    storage_service = test_helpers.create_test_storage_service()

    fetch_job = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service.id
    )

    # Mock call to index initialize function
    mocker.patch("AIPscan.typesense_helpers.initialize_index")

    # Create test index tasks object and test index task with fake Celery task ID
    task_id = celery.uuid()
    test_helpers.create_test_index_tasks(fetch_job.id, task_id)

    # Mock call to finish bulk document creation function
    mock_finish_bulk_doc = mocker.patch(
        "AIPscan.typesense_helpers.finish_bulk_document_creation"
    )

    # Start index task
    index_task.apply((fetch_job.id,), task_id=task_id)

    # Make sure finish bulk document creation function got called
    mock_finish_bulk_doc.assert_called()
