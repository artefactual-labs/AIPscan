from datetime import datetime

import pytest
import typesense
from pytz import timezone

from AIPscan import test_helpers
from AIPscan import typesense_helpers as ts_helpers
from AIPscan import typesense_test_helpers
from AIPscan.models import File
from AIPscan.models import Pipeline


def test_typesense_enabled(app_instance, enable_typesense):
    assert ts_helpers.typesense_enabled() is True


def test_client(app_instance, enable_typesense):
    client = ts_helpers.client()

    assert type(client) is typesense.Client
    assert client.config.nodes[0].host == "localhost"
    assert client.config.nodes[0].port == "8108"
    assert client.config.nodes[0].protocol == "http"
    assert client.config.api_key == "x0x0x0x0x0"


def test_search(app_instance, enable_typesense, mocker):
    client = ts_helpers.client()

    search_parameters = {"q": "*"}

    fake_results = {
        "facet_counts": [],
        "found": 1,
        "hits": [{"document": {"aip_id": 1}, "highlight": {}, "highlights": []}],
        "out_of": 252246,
        "page": 1,
        "request_params": {"collection_name": "aipscan_file", "per_page": 10, "q": "*"},
        "search_cutoff": False,
        "search_time_ms": 0,
    }

    fake_collection = typesense_test_helpers.FakeCollection(fake_results)

    query = mocker.patch("typesense.collections.Collections.__getitem__")
    query.return_value = fake_collection

    results = ts_helpers.search("file", search_parameters, client)

    assert results == fake_results


def test_collection_prefix(app_instance):
    fake_table_name = "test"

    prefixed = ts_helpers.collection_prefix(fake_table_name)

    assert prefixed == f"aipscan_{fake_table_name}"


@pytest.mark.parametrize(
    "datetime_obj,expected",
    [
        # PST midnight localized: exactly at the local midnight in US/Pacific.
        # The function should treat this as the PST date boundary and return the
        # corresponding epoch seconds
        (
            timezone("US/Pacific").localize(datetime(2019, 1, 30, 0, 0, 0)),
            1548835200,
        ),
        # PST early-morning time: a time after midnight in PST should be
        # truncated to the same PST date boundary.
        (
            timezone("US/Pacific").localize(datetime(2019, 1, 30, 2, 30, 50)),
            1548835200,
        ),
        # Naive datetime (no tz): for these tests naive datetimes are treated as
        # system/UTC-local time, so midnight naive here corresponds to the UTC
        # date boundary.
        (datetime(2019, 1, 30, 0, 0, 0), 1548806400),
        # Explicit UTC timezone: should map directly to the UTC date boundary
        # timestamp.
        (
            timezone("UTC").localize(datetime(2019, 1, 30, 0, 0, 0)),
            1548806400,
        ),
        # Naive later time in the day: later-naive times should be truncated to
        # that day's UTC date boundary.
        (datetime(2019, 1, 30, 2, 30, 50), 1548806400),
    ],
)
def test_datetime_to_timestamp_int(datetime_obj, expected):
    # Ensure datetime_to_timestamp_int converts a datetime to the start-of-day
    # (midnight in its timezone) before turning it into epoch seconds.
    assert ts_helpers.datetime_to_timestamp_int(datetime_obj) == expected


def test_assemble_filter_by():
    filters = [("storage_service_id", "=", 1), ("file_type", "=", "'original'")]
    filter_string = "storage_service_id:=1 && file_type:='original'"

    assert ts_helpers.assemble_filter_by(filters) == filter_string


def test_file_filters(app_instance):
    # Get local time zone then set time zone for testing
    local_timezone = test_helpers.set_timezone_and_return_current_timezone(
        "America/Vancouver"
    )

    file_filters = ts_helpers.file_filters(
        1, 1, datetime(2019, 1, 1), datetime(2019, 1, 31)
    )

    desired_filters = [
        ("aip_create_date", ">=", 1546300800),
        ("aip_create_date", "<", 1548892800),
        ("storage_service_id", "=", 1),
        ("file_type", "=", "'original'"),
        ("storage_location_id", "=", 1),
    ]

    assert file_filters == desired_filters

    # Reset time zone
    test_helpers.set_timezone(local_timezone)


def test_facet_value_counts():
    results = {
        "facet_counts": [
            {
                "field_name": "color",
                "counts": [{"value": "blue", "count": 9}, {"value": "red", "count": 7}],
            }
        ]
    }

    counts = ts_helpers.facet_value_counts(results)

    assert counts == {"color": {"blue": 9, "red": 7}}


def test_get_model_table():
    assert ts_helpers.get_model_table(File) == "file"


def test_collection_fields_from_model():
    pipeline_fields = [
        {"name": "id", "type": "int32"},
        {"name": "origin_pipeline", "type": "string", "optional": True},
        {"name": "dashboard_url", "type": "string", "optional": True},
    ]

    assert ts_helpers.collection_fields_from_model(Pipeline) == pipeline_fields


def test_initialize_index(app_instance, enable_typesense, mocker):
    class FakeCollections:
        def create(self):
            return True

    fake_collections = FakeCollections()
    fake_collection = typesense_test_helpers.FakeCollection()

    query = mocker.patch("typesense.collections.Collections.__getitem__")
    query.return_value = fake_collection

    query2 = mocker.patch("typesense.collections.Collections.create")
    query2.return_value = fake_collections

    ts_helpers.initialize_index()


def test_populate_index(app_instance, enable_typesense, mocker):
    fake_collection = typesense_test_helpers.FakeCollection()

    query = mocker.patch("typesense.collections.Collections.__getitem__")
    query.return_value = fake_collection

    ts_helpers.populate_index()


def test_augment_file_document_with_aip_data(app_instance):
    document = {}

    aip_cache = {
        "original_file_count": {3: 23},
        "storage_service_id": {3: 1},
        "storage_location_id": {3: [2]},
        "create_date": {3: datetime(2024, 3, 2, 5, 35)},
        "uuid": {3: "111111111111-1111-1111-11111111"},
        "transfer_name": {3: "Test AIP"},
    }

    class MockFileResult:
        id = 4
        aip_id = 3

    file_result = MockFileResult()

    # Get local time zone then set time zone for testing
    local_timezone = test_helpers.set_timezone_and_return_current_timezone(
        "America/Vancouver"
    )

    ts_helpers.augment_file_document_with_aip_data(
        "file", document, aip_cache, file_result
    )

    assert document["storage_service_id"] == 1
    assert document["storage_location_id"] == [2]
    assert document["aip_create_date"] == 1709366400
    assert document["aip_uuid"] == "111111111111-1111-1111-11111111"
    assert document["transfer_name"] == "Test AIP"

    # Reset time zone
    test_helpers.set_timezone(local_timezone)
