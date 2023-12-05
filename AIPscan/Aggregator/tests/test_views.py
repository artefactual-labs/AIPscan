import pytest
from flask import current_app

from AIPscan.Aggregator.tasks import TaskError
from AIPscan.Aggregator.views import _test_storage_service_connection
from AIPscan.models import StorageService


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
