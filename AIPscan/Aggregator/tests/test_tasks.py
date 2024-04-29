import json
import logging
import os
import uuid
from datetime import datetime
from io import StringIO

import celery
import pytest

from AIPscan import test_helpers
from AIPscan.Aggregator.tasks import (
    TaskError,
    delete_aip,
    delete_fetch_job,
    delete_storage_service,
    get_mets,
    index_task,
    make_request,
    parse_package_list_file,
    parse_packages_and_load_mets,
    start_index_task,
)
from AIPscan.Aggregator.tests import (
    INVALID_JSON,
    REQUEST_URL,
    REQUEST_URL_WITHOUT_API_KEY,
    RESPONSE_DICT,
    VALID_JSON,
    MockResponse,
)
from AIPscan.models import AIP, Agent, FetchJob, StorageService, index_tasks

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
        return mets_file

    mocker.patch("AIPscan.Aggregator.tasks.download_mets", mock_download_mets)
    delete_mets_file = mocker.patch("AIPscan.Aggregator.tasks.os.remove")

    storage_service = test_helpers.create_test_storage_service()
    storage_location = test_helpers.create_test_storage_location(
        storage_service_id=storage_service.id
    )
    pipeline = test_helpers.create_test_pipeline(storage_service_id=storage_service.id)

    get_storage_location = mocker.patch(
        "AIPscan.Aggregator.database_helpers.create_or_update_storage_location"
    )
    get_storage_location.return_value = storage_location

    # No AIPs should exist at this point.
    aips = _get_aips(storage_service.id)
    assert not aips

    # Set up custom logger and add handler to capture output
    customlogger = logging.getLogger(__name__)
    customlogger.setLevel(logging.DEBUG)

    log_string = StringIO()
    handler = logging.StreamHandler(log_string)
    customlogger.addHandler(handler)

    # Create AIP and verify record.
    fetch_job1 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service.id
    )
    get_mets(
        package_uuid=package_uuid,
        aip_size=1000,
        relative_path_to_mets="test",
        timestamp_str=datetime.now()
        .replace(microsecond=0)
        .strftime("%Y-%m-%d-%H-%M-%S"),
        package_list_no=1,
        storage_service_id=storage_service.id,
        storage_location_id=storage_location.id,
        fetch_job_id=fetch_job1.id,
        origin_pipeline_id=pipeline.id,
        customlogger=customlogger,
    )
    aips = _get_aips(storage_service.id)
    assert len(aips) == 1
    assert len(fetch_job1.aips) == 1

    original_mets_sha256 = aips[0].mets_sha256

    # Try to create AIP again and verify no duplicate is created.
    fetch_job2 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service.id
    )
    get_mets(
        package_uuid=package_uuid,
        aip_size=1000,
        relative_path_to_mets="test",
        timestamp_str=datetime.now()
        .replace(microsecond=0)
        .strftime("%Y-%m-%d-%H-%M-%S"),
        package_list_no=1,
        storage_service_id=storage_service.id,
        storage_location_id=storage_location.id,
        fetch_job_id=fetch_job2.id,
        origin_pipeline_id=pipeline.id,
    )
    aips = _get_aips(storage_service.id)
    assert len(aips) == 1
    assert aips[0].mets_sha256 == original_mets_sha256
    assert len(fetch_job1.aips) == 1
    assert len(fetch_job2.aips) == 0

    # Replace METS with a new METS file and run again. The old AIP record
    # should be deleted and replaced with one from the new METS.
    mets_file = os.path.join(FIXTURES_DIR, "iso_mets", "iso_mets.xml")
    fetch_job3 = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service.id
    )
    get_mets(
        package_uuid=package_uuid,
        aip_size=1000,
        relative_path_to_mets="test",
        timestamp_str=datetime.now()
        .replace(microsecond=0)
        .strftime("%Y-%m-%d-%H-%M-%S"),
        package_list_no=1,
        storage_service_id=storage_service.id,
        storage_location_id=storage_location.id,
        fetch_job_id=fetch_job3.id,
        origin_pipeline_id=pipeline.id,
    )
    aips = _get_aips(storage_service.id)
    assert len(aips) == 1
    assert aips[0].mets_sha256 != original_mets_sha256
    assert len(fetch_job1.aips) == 0
    assert len(fetch_job2.aips) == 0
    assert len(fetch_job3.aips) == 1

    delete_calls = [
        mocker.call(os.path.join(FIXTURES_DIR, fixture_path)),
        mocker.call(mets_file),
    ]
    delete_mets_file.assert_has_calls(delete_calls, any_order=True)
    delete_mets_file.call_count == 3

    # Test that custom logger was used
    assert (
        log_string.getvalue()
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


def test_parse_packages_and_load_mets(app_instance, tmpdir, mocker):
    """Test that JSON package lists are deleted after being parsed."""
    json_file_path = tmpdir.join("packages.json")
    json_file_path.write(json.dumps({"objects": []}))

    delete_package_json = mocker.patch("AIPscan.Aggregator.tasks.os.remove")

    package_list = parse_package_list_file(json_file_path, None, True)

    parse_packages_and_load_mets(package_list, str(datetime.now()), 1, 1, 1)

    delete_package_json.assert_called_with(json_file_path)


def test_delete_aip(app_instance):
    """Test that SS deleted AIPs gets deleted in aipscan.db."""
    PACKAGE_UUID = str(uuid.uuid4())

    test_helpers.create_test_aip(uuid=PACKAGE_UUID)

    deleted_aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert deleted_aip is not None

    delete_aip(PACKAGE_UUID)

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

    fetch_job = test_helpers.create_test_fetch_job(
        storage_service_id=storage_service.id
    )

    # At this point no index_tasks should exist for the fetch job
    index_task_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job.id).first()
    assert index_task_obj is None

    # Start mock index task, making sure it got started with the right value
    start_index_task(fetch_job.id)

    mock_index_task.assert_called_with(fetch_job.id)

    # At this point an index_tasks should exist for the fetch job
    index_task_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job.id).first()
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
