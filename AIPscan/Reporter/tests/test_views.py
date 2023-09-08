from flask import current_app
from werkzeug.datastructures import Headers


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
