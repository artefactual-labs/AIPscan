import os

from AIPscan.Aggregator import tasks, task_helpers

# Storage service URLs, usernames and API keys are sensitive information.
# To run this test, create yours as local ENV variables using the following
# names: 'AIPSCAN_SS_URL', 'AIPSCAN_SS_USER', and 'AIPSCAN_SS_KEY'
SS_URL = os.getenv('AIPSCAN_SS_URL')
SS_USER = os.getenv('AIPSCAN_SS_USER')
SS_KEY = os.getenv('AIPSCAN_SS_KEY')


def test_ss_connection():
    """Test that a connection to the Storage Service server can be made
    successfully and that there are no incorrect values for the Storage Service URL, username or API Key"""

    if SS_URL is None or SS_USER is None or SS_KEY is None:
        assert False, "Missing Storage Service URL, username, or API Key in ENV variables."
    else:
        api_url = {
            "baseUrl": SS_URL,
            "userName": SS_USER,
            "apiKey": SS_KEY,
            "offset": 0,
            "limit": 20,
        }

        base_url, request_url_without_api_key, request_url = task_helpers.format_api_url_with_limit_offset(api_url)

        assert tasks._make_request(request_url, request_url_without_api_key)
