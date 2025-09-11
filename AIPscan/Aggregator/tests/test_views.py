import pytest
from flask import current_app

from AIPscan import test_helpers
from AIPscan.Aggregator.tasks import TaskError
from AIPscan.Aggregator.views import _test_storage_service_connection
from AIPscan.models import StorageService


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
        assert set(["timestamp", "taskId", "fetchJobId"]).issubset(data.keys())
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
