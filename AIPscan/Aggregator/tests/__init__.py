import json

RESPONSE_DICT = {"key": "value"}
VALID_JSON = json.dumps(RESPONSE_DICT)
INVALID_JSON = "test"

REQUEST_URL_WITHOUT_API_KEY = "http://test-archivematica.example.com:8000"
REQUEST_URL = REQUEST_URL_WITHOUT_API_KEY + "?user=test&api_key=test"


class MockResponse:
    """Mock requests.Response class."""

    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

    def json(self):
        return json.loads(self.data)
