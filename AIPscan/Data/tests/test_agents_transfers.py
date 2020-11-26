# -*- coding: utf-8 -*-

"""Test the efficacy of the agents_transfers function which supplies
the ingest log report and agents-transfers API endpoint.
"""

import pytest

from AIPscan.Data import report_data
from AIPscan.Data.tests.conftest import INGEST_EVENT_CREATION_TIME, AIP_CREATION_TIME


@pytest.mark.parametrize(
    "storage_id, storage_name, number_of_ingests, aip_uuid, aip_name, user_name, ingest_date, aip_creation_date",
    [
        # Simple transfer with limited amount of data from the DB.
        (
            1,
            "test storage service",
            1,
            "111111111111-1111-1111-11111111",
            "test aip",
            "user one",
            INGEST_EVENT_CREATION_TIME,
            AIP_CREATION_TIME,
        ),
        # Request for a non-existent storage service.
        (30, None, 0, "", "", "", "", ""),
    ],
)
def test_agents_transfers(
    app_with_populated_files,
    storage_id,
    storage_name,
    number_of_ingests,
    aip_uuid,
    aip_name,
    user_name,
    ingest_date,
    aip_creation_date,
):
    """Test that structure of agents-transfers matches expectations."""

    report = report_data.agents_transfers(storage_service_id=storage_id)

    assert report["StorageName"] == storage_name
    assert len(report["Ingests"]) == number_of_ingests

    if number_of_ingests < 1:
        return

    ingests = report["Ingests"]
    assert ingests[0]["AIPUUID"] == aip_uuid
    assert ingests[0]["User"] == "user one"
    assert ingests[0]["IngestStartDate"] == str(ingest_date)
    assert ingests[0]["IngestFinishDate"] == str(aip_creation_date)
