import pytest
from flask import current_app
from werkzeug.datastructures import Headers

from AIPscan import test_helpers
from AIPscan.Reporter import views


def test_download_mets(app_with_populated_files, mocker):
    # Mock storage server API request response
    request = mocker.patch("requests.get")

    class MockResponse:
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


@pytest.mark.parametrize(
    "query,page,pages,total,prev_num,next_num,set_location",
    [
        (None, 1, 2, 3, None, 2, False),  # No search query
        ("Another Test AIP", 1, 1, 1, None, None, False),  # Search matches one AIP
        (None, 1, 1, 1, None, None, True),  # Use non-default storage location
        ("Does Not Exist", 1, 0, 0, None, None, False),  # Search doesn't match any AIP
        ("Test AIP", 1, 2, 3, None, 2, False),  # Search matches all AIPs, page 1
        ("Test AIP", 2, 2, 3, 1, None, False),  # Search matches all AIPs, page 2
    ],
)
def test_get_aip_pager(
    app_instance,
    mocker,
    query,
    page,
    pages,
    total,
    prev_num,
    next_num,
    set_location,
):
    storage_service = test_helpers.create_test_storage_service()
    default_storage_location = test_helpers.create_test_storage_location(
        default_storage_service_id=storage_service.id
    )
    other_storage_location = test_helpers.create_test_storage_location(
        storage_service_id=storage_service.id,
        current_location="/other/location",
    )

    test_helpers.create_test_aip(
        transfer_name="Test AIP",
        storage_service_id=storage_service.id,
        storage_location_id=default_storage_location.id,
    )
    test_helpers.create_test_aip(
        transfer_name="Another Test AIP",
        storage_service_id=storage_service.id,
        storage_location_id=default_storage_location.id,
    )
    test_helpers.create_test_aip(
        transfer_name="This Is Also A Test AIP",
        storage_service_id=storage_service.id,
        storage_location_id=other_storage_location.id,
    )

    location = None
    if set_location:
        location = other_storage_location

    pager = views.get_aip_pager(
        page, 2, storage_service, storage_location=location, query=query
    )

    assert pager.pages == pages
    assert pager.total == total

    if prev_num is None:
        assert pager.prev_num is None
    else:
        assert pager.prev_num == prev_num

    if next_num is None:
        assert pager.next_num is None
    else:
        assert pager.next_num == next_num


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


def test_view_aip(app_with_populated_files):
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/aip/1")
        assert response.status_code == 200

        response = test_client.get("/reporter/aip/0")
        assert response.status_code == 404


def test_view_file(app_with_populated_files):
    with current_app.test_client() as test_client:
        response = test_client.get("/reporter/file/1")
        assert response.status_code == 200

        response = test_client.get("/reporter/file/0")
        assert response.status_code == 404
