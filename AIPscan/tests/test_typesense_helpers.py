import os
import time
from datetime import datetime

import typesense
import tzlocal
from pytz import timezone

from AIPscan import typesense_helpers as ts_helpers
from AIPscan.models import File, Pipeline


def test_client(app_with_populated_files):
    client = ts_helpers.client()

    assert type(client) is typesense.Client
    assert client.config.nodes[0].host == "localhost"
    assert client.config.nodes[0].port == "8108"
    assert client.config.nodes[0].protocol == "http"
    assert client.config.api_key == "x0x0x0x0x0"


def test_collection_prefix():
    fake_table_name = "test"

    prefixed = ts_helpers.collection_prefix(fake_table_name)

    assert prefixed == ts_helpers.COLLECTION_PREFIX + fake_table_name


def test_date_string_to_timestamp_int():
    # Get local time zone then set time zone for testing
    local_timezone = tzlocal.get_localzone_name()
    os.environ["TZ"] = "Europe/London"
    time.tzset()

    # Test that date string gets converted to correct timestamp integer
    date_text = "2019-01-30"
    assert ts_helpers.date_string_to_timestamp_int(date_text) == 1548806400

    # Test that date string gets rounded to nearest date then converted to timestamp
    date_text = "2019-01-30 02:30:50"
    assert ts_helpers.date_string_to_timestamp_int(date_text) == 1548806400

    # Reset time zone
    os.environ["TZ"] = local_timezone
    time.tzset()


def test_datetime_to_timestamp_int():
    # Get local time zone then set time zone for testing
    local_timezone = tzlocal.get_localzone_name()
    os.environ["TZ"] = "America/Vancouver"
    time.tzset()

    # Create time zone object to create datetime objects from
    pst_tz = timezone("US/Pacific")

    # Test that datetime object gets converted to correct timestamp integer
    datetime_object = pst_tz.localize(datetime(2019, 1, 30))
    assert ts_helpers.datetime_to_timestamp_int(datetime_object) == 1548835200

    # Test that datetime object gets rounded to neartest date then converted to timestamp
    datetime_object = datetime(2019, 1, 30, 2, 30, 50).astimezone(pst_tz)
    assert ts_helpers.datetime_to_timestamp_int(datetime_object) == 1548835200

    # Reset time zone
    os.environ["TZ"] = local_timezone
    time.tzset()


def test_assemble_filter_by():
    filters = [("storage_service_id", "=", 1), ("file_type", "=", "'original'")]
    filter_string = "storage_service_id:=1 && file_type:='original'"

    assert ts_helpers.assemble_filter_by(filters) == filter_string


def test_file_filters(app_with_populated_files):
    # Get local time zone then set time zone for testing
    local_timezone = tzlocal.get_localzone_name()
    os.environ["TZ"] = "America/Vancouver"
    time.tzset()

    file_filters = ts_helpers.file_filters(1, 1, "2019-01-01", "2019-01-31")

    desired_filters = [
        ("date_created", ">", 1546329600),
        ("date_created", "<", 1548921599),
        ("storage_service_id", "=", 1),
        ("file_type", "=", "'original'"),
        ("storage_location_id", "=", 1),
    ]

    assert file_filters == desired_filters

    # Reset time zone
    os.environ["TZ"] = local_timezone
    time.tzset()


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
