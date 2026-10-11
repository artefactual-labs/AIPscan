"""Indexed exports retain counts when optional file metadata is absent."""

import csv
import io
import json

import pytest

from AIPscan import test_helpers


@pytest.mark.parametrize(
    "route, facet, value",
    [
        ("report_formats_count", "format_name", "Plain Text"),
        (
            "report_format_versions_count",
            "format_group",
            json.dumps(["x-fmt/111", "Plain Text", None]),
        ),
    ],
)
def test_indexed_csv_with_missing_sizes(
    app_instance, enable_typesense, mocker, route, facet, value
):
    aip = test_helpers.create_test_aip()
    test_helpers.create_test_file(aip_id=aip.id, size=None)
    mocker.patch(
        "typesense.sync.collection.Collection.retrieve",
        return_value={"fields": [{"name": facet, "facet": True}]},
    )
    mocker.patch(
        "typesense.sync.documents.Documents.search",
        return_value={
            "facet_counts": [
                {"field_name": facet, "counts": [{"value": value, "count": 1}]}
            ]
        },
    )
    mocker.patch(
        "typesense.sync.multi_search.MultiSearch.perform",
        return_value={
            "results": [
                {
                    "hits": [{"document": {"format_name": "Plain Text"}}],
                    "facet_counts": [
                        {
                            "field_name": "size",
                            "counts": [],
                            "stats": {"total_values": 0},
                        }
                    ],
                }
            ]
        },
    )

    response = app_instance.test_client().get(
        f"/reporter/{route}/",
        query_string={"amss_id": aip.storage_service_id, "csv": "True"},
    )

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.data.decode())))
    assert len(rows) == 1
    assert rows[0]["Count"] == "1"
    assert rows[0]["Size (bytes)"] == "0"


@pytest.mark.parametrize(
    "route", ["report_formats_count", "report_format_versions_count"]
)
def test_format_exports_use_sql_for_an_older_index(
    app_instance, enable_typesense, mocker, monkeypatch, route
):
    aip = test_helpers.create_test_aip()
    test_helpers.create_test_file(aip_id=aip.id, size=25, file_format="Plain Text")
    client = app_instance.test_client()
    url = f"/reporter/{route}/"
    params = {"amss_id": aip.storage_service_id, "csv": "True"}
    key = app_instance.config["TYPESENSE_API_KEY"]
    monkeypatch.setitem(app_instance.config, "TYPESENSE_API_KEY", None)
    expected = client.get(url, query_string=params)
    monkeypatch.setitem(app_instance.config, "TYPESENSE_API_KEY", key)
    mocker.patch(
        "typesense.sync.collection.Collection.retrieve",
        return_value={"fields": [{"name": "file_format", "facet": True}]},
    )
    mocker.patch(
        "typesense.sync.documents.Documents.search",
        side_effect=AssertionError("The old index cannot provide the new facets"),
    )

    response = client.get(url, query_string=params)

    assert response.status_code == 200
    assert response.data == expected.data
    assert b"Plain Text" in response.data
