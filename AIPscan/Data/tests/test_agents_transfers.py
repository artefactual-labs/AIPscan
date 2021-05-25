# -*- coding: utf-8 -*-

"""Test the efficacy of the agents_transfers function which supplies
the ingest log report and agents-transfers API endpoint.
"""

import pytest

from AIPscan.conftest import AIP_CREATION_TIME, INGEST_EVENT_CREATION_TIME
from AIPscan.Data import fields, report_data


@pytest.mark.parametrize(
    "storage_id, storage_name, location_id, location_name, number_of_ingests, aip_uuid, aip_name, user_name, ingest_date, aip_creation_date",
    [
        # Simple transfer with limited amount of data from the DB.
        (
            1,
            "test storage service",
            1,
            "test storage location",
            1,
            "111111111111-1111-1111-11111111",
            "test aip",
            "user one",
            INGEST_EVENT_CREATION_TIME,
            AIP_CREATION_TIME,
        ),
        # Request for a non-existent storage service.
        (30, None, 35, None, 0, "", "", "", "", ""),
    ],
)
def test_agents_transfers(
    app_with_populated_files,
    storage_id,
    storage_name,
    location_id,
    location_name,
    number_of_ingests,
    aip_uuid,
    aip_name,
    user_name,
    ingest_date,
    aip_creation_date,
):
    """Test that structure of agents-transfers matches expectations."""
    report = report_data.agents_transfers(
        storage_service_id=storage_id, storage_location_id=location_id
    )

    assert report[fields.FIELD_STORAGE_NAME] == storage_name
    assert report[fields.FIELD_STORAGE_LOCATION] == location_name
    assert len(report[fields.FIELD_INGESTS]) == number_of_ingests

    if number_of_ingests < 1:
        return

    ingests = report["Ingests"]
    assert ingests[0]["AIPUUID"] == aip_uuid
    assert ingests[0]["User"] == "user one"
    assert ingests[0]["IngestStartDate"] == str(ingest_date)
    assert ingests[0]["IngestFinishDate"] == str(aip_creation_date)


@pytest.mark.parametrize(
    "storage_id, storage_name, location_id, location_name, number_of_ingests",
    [
        # Simple transfer with limited amount of data from the DB.
        (1, "test storage service", 1, "test storage location", 0)
    ],
)
def test_agents_transfers_no_ingestion_event(
    app_with_populated_files_no_ingestion_event,
    storage_id,
    storage_name,
    location_id,
    location_name,
    number_of_ingests,
):
    """Test that lack of ingestion event doesn't throw error."""
    report = report_data.agents_transfers(
        storage_service_id=storage_id, storage_location_id=location_id
    )

    assert report[fields.FIELD_STORAGE_NAME] == storage_name
    assert report[fields.FIELD_STORAGE_LOCATION] == location_name
    assert len(report[fields.FIELD_INGESTS]) == number_of_ingests
