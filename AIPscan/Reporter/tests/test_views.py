import pytest
from flask import current_app
from werkzeug.datastructures import Headers

from AIPscan import test_helpers
from AIPscan.Reporter import views


def test_download_mets(app_with_populated_files, mocker):
    # Mock storage server API request response
    request = mocker.patch("requests.get")

    class MockResponse(object):
        pass

    return_response = MockResponse()
    return_response.content = bytes("METS content", "utf-8")
    return_response.status_code = 200

    request.return_value = return_response

    # Test view logic
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/download_mets/1")

        assert response.headers == Headers(
            [
                (
                    "Content-Disposition",
                    'attachment; filename="METS-111111111111-1111-1111-11111111.xml"',
                ),
                ("Content-Length", "12"),
                ("Content-Type", "text/html; charset=utf-8"),
            ]
        )

        assert response.data == return_response.content
        assert response.status_code == return_response.status_code


@pytest.mark.parametrize("page,pager_page", [(1, 1), ("bad", 1)])
def test_get_aip_pager(app_instance, mocker, page, pager_page):
    paginate_mock = mocker.Mock()
    filter_by_mock = mocker.Mock()
    filter_by_mock.paginate.return_value = paginate_mock

    query_mock = mocker.Mock()
    query_mock.filter_by.return_value = filter_by_mock

    storage_service = test_helpers.create_test_storage_service()
    storage_location = test_helpers.create_test_storage_location(
        storage_service_id=storage_service.id
    )
    pager = views.get_aip_pager(page, 2, storage_service, storage_location)

    assert pager.page == pager_page
    assert pager.pages == 0
    assert pager.per_page == 2
    assert pager.prev_num is None
    assert pager.next_num is None


@pytest.mark.parametrize("page,pager_page", [(1, 1), ("bad", 1)])
def test_get_file_pager(app_instance, mocker, page, pager_page):
    paginate_mock = mocker.Mock()
    filter_by_mock = mocker.Mock()
    filter_by_mock.paginate.return_value = paginate_mock

    query_mock = mocker.Mock()
    query_mock.filter_by.return_value = filter_by_mock

    aip = test_helpers.create_test_aip()
    pager = views.get_file_pager(page, 2, aip)

    assert pager.page == pager_page
    assert pager.pages == 0
    assert pager.per_page == 2
    assert pager.prev_num is None
    assert pager.next_num is None
