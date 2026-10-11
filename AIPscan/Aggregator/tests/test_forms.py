"""Validate Storage Service pagination through its public edit form."""

import pytest
from lxml import html

from AIPscan import db
from AIPscan import test_helpers


@pytest.mark.parametrize(
    "limit,offset,error",
    [
        ("0", "0", "Number must be at least 1"),
        ("one", "0", "Not a valid integer value"),
        ("1", "-1", "Number must be at least 0"),
        ("1", "0", None),
    ],
)
def test_storage_service_pagination_form(app_instance, limit, offset, error):
    storage = test_helpers.create_test_storage_service(
        download_limit=20, download_offset=0
    )
    client = app_instance.test_client()
    url = f"/aggregator/edit_storage_service/{storage.id}"
    form = html.fromstring(client.get(url).text).forms[0]
    data = dict(form.form_values()) | {
        "download_limit": limit,
        "download_offset": offset,
    }

    response = client.post(url, data=data)

    db.session.expire_all()
    if error:
        assert response.status_code == 200
        assert error in response.text
        assert storage.download_limit == 20
        assert storage.download_offset == 0
    else:
        assert response.status_code == 302
        assert storage.download_limit == 1
        assert storage.download_offset == 0
