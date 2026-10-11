from datetime import datetime

import pytest
from flask import current_app

from AIPscan import db
from AIPscan import test_helpers
from AIPscan.Aggregator.tasks import TaskError
from AIPscan.Aggregator.views import _test_storage_service_connection
from AIPscan.models import StorageService
from AIPscan.models import get_mets_tasks
from AIPscan.models import index_tasks


@pytest.mark.parametrize("state", ["SUCCESS", "FAILURE", "PENDING", "STARTED"])
def test_fetch_job_reports_terminal_import_states(app_instance, mocker, state):
    """Polling records finished imports and leaves running imports pending."""
    job = test_helpers.create_test_fetch_job(download_end=None)
    task = get_mets_tasks(
        get_mets_task_id="import-task",
        workflow_coordinator_id="coordinator",
        package_uuid="package",
    )
    db.session.add(task)
    db.session.commit()
    result = mocker.patch("AIPscan.Aggregator.views.AsyncResult").return_value
    result.state = state
    result.info = TaskError("Cannot parse METS")
    mocker.patch(
        "AIPscan.Aggregator.views.tasks.workflow_coordinator.AsyncResult"
    ).return_value.state = "SUCCESS"
    client = app_instance.test_client()
    url = "/aggregator/get_mets_task_status/coordinator"
    params = {"totalAIPs": 0, "fetchJobId": job.id}

    response = client.get(url, query_string=params)

    assert response.status_code == 200
    terminal = state in {"SUCCESS", "FAILURE"}
    assert response.json == (
        [
            {"state": state, "package": "METS.package.xml", "totalAIPs": 1}
            | ({"message": "Cannot parse METS"} if state == "FAILURE" else {})
        ]
        if terminal
        else []
    )
    db.session.expire_all()
    assert task.status == (state if terminal else None)
    assert job.download_end is None

    response = client.get(url, query_string=params | {"totalAIPs": int(terminal)})
    assert response.json == (
        {"state": "COMPLETED", "failedImports": 1}
        if state == "FAILURE"
        else {"state": "COMPLETED"}
        if terminal
        else []
    )
    db.session.expire_all()
    assert (job.download_end is not None) == terminal


@pytest.mark.parametrize("state", ["PENDING", "STARTED", "FAILURE", "SUCCESS"])
def test_fetch_job_waits_for_coordinator(app_instance, mocker, state):
    job = test_helpers.create_test_fetch_job(download_end=None)
    result = mocker.patch(
        "AIPscan.Aggregator.views.tasks.workflow_coordinator.AsyncResult"
    ).return_value
    result.state = state
    result.info = TaskError("Cannot read package list")

    response = app_instance.test_client().get(
        "/aggregator/get_mets_task_status/coordinator",
        query_string={"totalAIPs": 0, "fetchJobId": job.id},
    )

    assert response.status_code == 200
    assert response.json["state"] == (
        "COMPLETED"
        if state == "SUCCESS"
        else "FAILURE"
        if state == "FAILURE"
        else "PENDING"
    )
    if state == "FAILURE":
        assert response.json["message"] == "Cannot read package list"
    db.session.expire_all()
    assert (job.download_end is not None) == (state == "SUCCESS")


def test_completed_poll_preserves_end_time(app_instance, mocker):
    original_end = datetime(2020, 1, 2, 3, 4, 5)
    job = test_helpers.create_test_fetch_job(download_end=original_end)
    mocker.patch(
        "AIPscan.Aggregator.views.tasks.workflow_coordinator.AsyncResult"
    ).return_value.state = "SUCCESS"

    response = app_instance.test_client().get(
        "/aggregator/get_mets_task_status/completed-coordinator",
        query_string={"totalAIPs": 1, "fetchJobId": job.id},
    )

    assert response.json == {"state": "COMPLETED"}
    db.session.expire_all()
    assert job.download_end == original_end


def test_failed_coordinator_with_pending_import(app_instance, mocker):
    job = test_helpers.create_test_fetch_job(download_end=None)
    db.session.add(
        get_mets_tasks(
            get_mets_task_id="pending-import",
            workflow_coordinator_id="failed-coordinator",
            package_uuid="package",
        )
    )
    db.session.commit()
    mocker.patch("AIPscan.Aggregator.views.AsyncResult").return_value.state = "PENDING"
    coordinator = mocker.patch(
        "AIPscan.Aggregator.views.tasks.workflow_coordinator.AsyncResult"
    ).return_value
    coordinator.state = "FAILURE"
    coordinator.info = TaskError("Cannot finish scheduling imports")

    response = app_instance.test_client().get(
        "/aggregator/get_mets_task_status/failed-coordinator",
        query_string={"totalAIPs": 0, "fetchJobId": job.id},
    )

    assert response.json == {
        "state": "FAILURE",
        "message": "Cannot finish scheduling imports",
    }
    db.session.expire_all()
    assert job.download_end is None


def test_indexing_status_reports_failed_worker(app_instance, enable_typesense, mocker):
    job = test_helpers.create_test_fetch_job()
    test_helpers.create_test_index_tasks(job.id, "failed-index")
    result = mocker.patch(
        "AIPscan.Aggregator.views.tasks.index_task.AsyncResult"
    ).return_value
    result.state = "FAILURE"
    result.info = RuntimeError("Typesense did not accept every file document")

    response = app_instance.test_client().get(f"/aggregator/indexing_status/{job.id}")

    assert response.json == {
        "state": "FAILURE",
        "message": "Typesense did not accept every file document",
    }
    db.session.expire_all()
    assert index_tasks.query.filter_by(fetch_job_id=job.id).one().indexing_end is None


def test_new_fetch_job_success_returns_task_id(app_instance, mocker):
    ss = test_helpers.create_test_storage_service()

    mocker.patch("AIPscan.Aggregator.views._test_storage_service_connection")
    mocker.patch("AIPscan.Aggregator.views.os.makedirs")

    class _FakeTask:
        id = "coordinator-123"

    mocker.patch(
        "AIPscan.Aggregator.views.tasks.workflow_coordinator.delay",
        return_value=_FakeTask(),
    )

    mocker.patch(
        "AIPscan.Aggregator.views._wait_for_package_list_task_id",
        return_value="child-456",
    )

    with current_app.test_client() as test_client:
        response = test_client.post(f"/aggregator/new_fetch_job/{ss.id}")
        assert response.status_code == 200

        data = response.get_json()
        assert {"timestamp", "taskId", "fetchJobId"}.issubset(data.keys())
        assert data["taskId"] == "child-456"
        assert isinstance(data["fetchJobId"], int)


def test_new_fetch_job_timeout_returns_500(app_instance, mocker):
    """If no child id appears, the view responds with 500 JSON error."""
    ss = test_helpers.create_test_storage_service()

    mocker.patch("AIPscan.Aggregator.views._test_storage_service_connection")
    mocker.patch("AIPscan.Aggregator.views.os.makedirs")

    class _FakeTask:
        id = "coordinator-xyz"

    mocker.patch(
        "AIPscan.Aggregator.views.tasks.workflow_coordinator.delay",
        return_value=_FakeTask(),
    )

    # Simulate helper timing out.
    mocker.patch(
        "AIPscan.Aggregator.views._wait_for_package_list_task_id",
        return_value=None,
    )

    with current_app.test_client() as test_client:
        response = test_client.post(f"/aggregator/new_fetch_job/{ss.id}")
        assert response.status_code == 500

        data = response.get_json()
        assert "message" in data
        assert "failed to start" in data["message"].lower()


def test__test_storage_service_connection(mocker):
    """Test that invalid SS connection raises ConnectionError."""
    make_request = mocker.patch("AIPscan.Aggregator.views.tasks.make_request")
    make_request.side_effect = TaskError("Bad response from server")

    with pytest.raises(ConnectionError):
        storage_service = StorageService(
            "Test", "http://test-url", "test", "test", "0", "10", ""
        )
        _test_storage_service_connection(storage_service)


def test_new_fetch_job_bad_connection(app_with_populated_files, mocker):
    """Verify Celery tasks don't run wihtout a Storage Service connection."""
    task = mocker.patch("AIPscan.Aggregator.views.tasks.workflow_coordinator.delay")
    test_storage_service_conn = mocker.patch(
        "AIPscan.Aggregator.views._test_storage_service_connection"
    )
    test_storage_service_conn.side_effect = ConnectionError("Bad response from server")
    with current_app.test_client() as test_client:
        response = test_client.post("/aggregator/new_fetch_job/1")
        task.assert_not_called()
        assert response.status_code == 400


def test_view_storage_service(app_with_populated_files):
    with current_app.test_client() as test_client:
        response = test_client.get("/aggregator/storage_service/1")
        assert response.status_code == 200

        response = test_client.get("/aggregator/storage_service/0")
        assert response.status_code == 404


def test_edit_storage_service(app_with_populated_files):
    with current_app.test_client() as test_client:
        response = test_client.post("/aggregator/edit_storage_service/1")
        assert response.status_code == 200

        response = test_client.post("/aggregator/edit_storage_service/0")
        assert response.status_code == 404


def test_delete_storage_service(app_with_populated_files, mocker):
    with current_app.test_client() as test_client:
        # The delete confirmation page should not show up for a non-existent storage service
        response = test_client.get("/aggregator/delete_storage_service/0")
        assert response.status_code == 404

        # Deletion should not be attempted for a non-existent storage service
        response = test_client.get("/aggregator/delete_storage_service/0?confirm=1")
        assert response.status_code == 404

        # Don't actually instantiate Celery job
        mocker.patch("AIPscan.Aggregator.tasks.delete_storage_service.delay")

        # The delete confirmation page should show up for an existing storage service
        response = test_client.get("/aggregator/delete_storage_service/1")
        assert response.status_code == 200

        # Deletion should be attempted if the storage service exists
        response = test_client.get("/aggregator/delete_storage_service/1?confirm=1")
        assert response.status_code == 200


def test_delete_fetch_job(app_with_populated_files, mocker):
    with current_app.test_client() as test_client:
        response = test_client.get("/aggregator/delete_fetch_job/0?confirm=1")
        assert response.status_code == 404

        mocker.patch("AIPscan.Aggregator.tasks.delete_fetch_job.delay")

        response = test_client.get("/aggregator/delete_fetch_job/1?confirm=1")
        assert response.status_code == 302
