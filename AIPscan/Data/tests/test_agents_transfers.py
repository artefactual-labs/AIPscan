"""Test the efficacy of the agents_transfers function which supplies
the ingest log report and agents-transfers API endpoint.
"""

import pytest

from AIPscan.conftest import AIP_CREATION_TIME
from AIPscan.conftest import INGEST_EVENT_CREATION_TIME
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_datetime_bound

DAY_BEFORE_AIP_CREATION = parse_datetime_bound("2020-12-01")
DAY_OF_AIP_CREATION = parse_datetime_bound("2020-12-03", upper=True)
DAY_WELL_PAST_AIP_CREATION = parse_datetime_bound("2022-04-12")


@pytest.mark.parametrize(
    "storage_id, storage_name, location_id, location_name, number_of_ingests, aip_uuid, aip_name, user_name, ingest_date, aip_creation_date, start_date, end_date",
    [
        # Simple transfer with limited amount of data from the DB.
        (
            1,
            "test storage service",
            1,
            "test storage location",
            1,
            "111111111111-1111-1111-11111111",
            "Test AIP",
            "user one",
            INGEST_EVENT_CREATION_TIME,
            AIP_CREATION_TIME,
            DAY_BEFORE_AIP_CREATION,
            DAY_OF_AIP_CREATION,
        ),
        # Request for a non-existent storage service.
        (30, None, 35, None, 0, "", "", "", "", "", "", ""),
        # Transfer that occured outside of specified date range.
        (
            1,
            "test storage service",
            1,
            "test storage location",
            0,
            "",
            "",
            "",
            "",
            "",
            DAY_WELL_PAST_AIP_CREATION,
            DAY_WELL_PAST_AIP_CREATION,
        ),
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
    start_date,
    end_date,
):
    """Test that structure of agents-transfers matches expectations."""
    report = report_data.agents_transfers(
        storage_service_id=storage_id,
        start_date=start_date,
        end_date=end_date,
        storage_location_id=location_id,
    )

    assert report[fields.FIELD_STORAGE_NAME] == storage_name
    assert report[fields.FIELD_STORAGE_LOCATION] == location_name
    assert len(report[fields.FIELD_INGESTS]) == number_of_ingests

    if number_of_ingests < 1:
        return

    ingests = report["Ingests"]
    assert ingests[0]["AIPUUID"] == aip_uuid
    assert ingests[0]["AIPName"] == aip_name
    assert ingests[0]["User"] == "user one"
    assert ingests[0]["IngestStartDate"] == str(ingest_date)
    assert ingests[0]["IngestFinishDate"] == str(aip_creation_date)


@pytest.mark.parametrize(
    "storage_id, storage_name, location_id, location_name, number_of_ingests, start_date, end_date",
    [
        # Simple transfer with limited amount of data from the DB.
        (
            1,
            "test storage service",
            1,
            "test storage location",
            0,
            DAY_BEFORE_AIP_CREATION,
            DAY_OF_AIP_CREATION,
        )
    ],
)
def test_agents_transfers_no_ingestion_event(
    app_with_populated_files_no_ingestion_event,
    storage_id,
    storage_name,
    location_id,
    location_name,
    number_of_ingests,
    start_date,
    end_date,
):
    """Test that lack of ingestion event doesn't throw error."""
    report = report_data.agents_transfers(
        storage_service_id=storage_id,
        start_date=start_date,
        end_date=end_date,
        storage_location_id=location_id,
    )

    assert report[fields.FIELD_STORAGE_NAME] == storage_name
    assert report[fields.FIELD_STORAGE_LOCATION] == location_name
    assert len(report[fields.FIELD_INGESTS]) == number_of_ingests
