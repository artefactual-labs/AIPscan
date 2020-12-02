# -*- coding: utf-8 -*-

"""Tests for the agents transfer log."""

import pytest

from AIPscan.Reporter.report_ingest_log import get_table_data, get_figure_html

ZERO_TRANSFERS = {"StorageName": None, "Ingests": []}

ONE_TRANSFER = {
    "StorageName": "S1",
    "Ingests": [
        {
            "AIP": "2905e275-90df-4f07-8203-bc54d5588d32",
            "AIPName": "12345",
            "Event": "ingestion",
            "IngestStartDate": "2020-11-30 18:30:00",
            "IngestFinishDate": "2020-11-30 18:35:00",
            "User": "test",
        }
    ],
}

THREE_TRANSFERS = {
    "StorageName": "S2",
    "Ingests": [
        {
            "AIP": "2905e275-90df-4f07-8203-bc54d5588d32",
            "AIPName": "12345",
            "Event": "ingestion",
            "IngestStartDate": "2020-11-30 18:30:00",
            "IngestFinishDate": "2020-11-30 18:30:42",
            "User": "test",
        },
        {
            "AIP": "c8111c6f-d74b-44b6-87dd-668b0fdc59e4",
            "AIPName": "images_two",
            "Event": "ingestion",
            "IngestStartDate": "2020-11-30 18:30:00",
            "IngestFinishDate": "2020-11-30 18:30:42",
            "User": "miller",
        },
        {
            "AIP": "24a5a997-83b6-49bc-b4fb-29ec7a561ce6",
            "AIPName": "longer_transfer",
            "Event": "ingestion",
            "IngestStartDate": "2020-11-30 18:30:00",
            "IngestFinishDate": "2020-11-30 18:30:42",
            "User": "ross",
        },
    ],
}


@pytest.mark.parametrize(
    "agents_transfers, transfer_count, storage_name, duration",
    [
        # There is no data, e.g. the request could be for an invalid
        # storage service. Count should be zero, a valid div is still
        # returned with the data.
        (ZERO_TRANSFERS, 0, None, None),
        # One transfer with valid data. Duration for the first ingest is
        # configured to 5 mins.
        (ONE_TRANSFER, 1, "S1", "0:05:00"),
        # Three transfers with valid data. Duration for the first ingest
        # is configured to 42 seconds.
        (THREE_TRANSFERS, 3, "S2", "0:00:42"),
    ],
)
def test_get_table_data(agents_transfers, transfer_count, storage_name, duration):
    """Test that we get valid data for the transfers log table, e.g.
    including our calculation of duration.
    """
    response = get_table_data(agents_transfers)
    assert response["transfer_count"] == transfer_count
    assert response["StorageName"] == storage_name
    if not duration:
        with pytest.raises(IndexError):
            _ = response["Ingests"][0]["duration"]
        return
    assert str(response["Ingests"][0]["duration"]) == duration


@pytest.mark.parametrize(
    "agents_transfers, transfer_count, storage_name",
    [
        # There is no data, e.g. the request could be for an invalid
        # storage service. Count should be zero, a valid div is still
        # returned with the data.
        (ZERO_TRANSFERS, 0, None),
        # One transfer with valid data.
        (ONE_TRANSFER, 1, "S1"),
        # Three transfers with valid data.
        (THREE_TRANSFERS, 3, "S2"),
    ],
)
def test_get_figure_html(agents_transfers, transfer_count, storage_name):
    """Test that we get valid data required for the Gantt chart to be
    rendered.
    """
    response = get_figure_html(agents_transfers)
    assert response["transfer_count"] == transfer_count
    assert response["StorageName"] == storage_name
    assert response["figure"].startswith("<div>")
    assert response["figure"].endswith("</div>")
