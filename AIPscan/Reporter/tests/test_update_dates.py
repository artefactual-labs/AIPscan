from flask import current_app


def test_update_dates(app_with_populated_format_versions):
    """Test that report template renders."""
    with current_app.test_client() as test_client:
        get_response = test_client.get("/reporter/update_dates/")
        assert get_response.status_code == 405

        post_response = test_client.post(
            "/reporter/update_dates/", json={"start_date": "2021-02-14"}
        )
        assert post_response.status_code == 200
        assert post_response.json.get("start_date") == "2021-02-14"

        post_response = test_client.post(
            "/reporter/update_dates/", json={"end_date": "2021-02-14"}
        )
        assert post_response.status_code == 200
        assert post_response.json.get("end_date") == "2021-02-14"
