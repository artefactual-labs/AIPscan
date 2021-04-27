# -*- coding: utf-8 -*-
import os
import uuid

import metsrw
import pytest

from AIPscan.Aggregator import database_helpers
from AIPscan.models import AIP, Agent

FIXTURES_DIR = "fixtures"

TEST_SHA_256 = "79c16fa9573ec46c5f60fd54b34f314159e0623ca53d8d2f00c5875dbb4e0dfd"


def test_create_aip(app_instance):
    """Test AIP creation."""
    PACKAGE_UUID = str(uuid.uuid4())
    TRANSFER_NAME = "some name"
    STORAGE_SERVICE_ID = 1
    FETCH_JOB_ID = 1

    database_helpers.create_aip_object(
        package_uuid=PACKAGE_UUID,
        transfer_name=TRANSFER_NAME,
        create_date="2020-11-02",
        mets_sha256=TEST_SHA_256,
        storage_service_id=STORAGE_SERVICE_ID,
        fetch_job_id=FETCH_JOB_ID,
    )

    aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert aip is not None
    assert aip.transfer_name == TRANSFER_NAME
    assert aip.storage_service_id == STORAGE_SERVICE_ID
    assert aip.fetch_job_id == FETCH_JOB_ID


def test_delete_aip(app_instance):
    """Test AIP deletion."""
    PACKAGE_UUID = str(uuid.uuid4())

    database_helpers.create_aip_object(
        package_uuid=PACKAGE_UUID,
        transfer_name="some name",
        create_date="2020-11-02",
        mets_sha256=TEST_SHA_256,
        storage_service_id=1,
        fetch_job_id=1,
    )

    aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert aip is not None

    database_helpers.delete_aip_object(aip)
    aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert aip is None


@pytest.mark.parametrize(
    "fixture_path, event_count, agent_link_multiplier",
    [
        (os.path.join("features_mets", "features-mets.xml"), 0, 0),
        (os.path.join("iso_mets", "iso_mets.xml"), 17, 3),
        (os.path.join("images_mets", "images.xml"), 76, 3),
    ],
)
def test_event_creation(
    app_instance, mocker, fixture_path, event_count, agent_link_multiplier
):
    """Make sure that we're seeing all of the events associated with
    an AIP and that they are potentially written to the database okay.
    Make sure too that the event_agent_relationship is established.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    mets_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    mets = metsrw.METSDocument.fromfile(mets_file)
    mocker.patch("AIPscan.models.Event")
    agent_find_match = mocker.patch(
        "AIPscan.Aggregator.database_helpers._create_agent_type_id"
    )
    mocker.patch(
        "sqlalchemy.orm.query.Query.first",
        return_value=Agent(
            linking_type_value="some_type_value",
            agent_type="an_agent_type",
            agent_value="an_agent_value",
        ),
    )
    mocked_events = mocker.patch("AIPscan.db.session.add")
    mocker.patch("AIPscan.db.session.commit")
    for fsentry in mets.all_files():
        database_helpers.create_event_objects(fsentry, "some_id")
    assert mocked_events.call_count == event_count
    assert agent_find_match.call_count == event_count * agent_link_multiplier


@pytest.mark.parametrize(
    "fixture_path, number_of_unique_agents",
    [
        (os.path.join("features_mets", "features-mets.xml"), 0),
        (os.path.join("features_mets", "features-mets-added-agents.xml"), 5),
        (os.path.join("iso_mets", "iso_mets.xml"), 3),
        (os.path.join("images_mets", "images.xml"), 3),
    ],
)
def test_collect_agents(app_instance, fixture_path, number_of_unique_agents):
    """Make sure that we retrieve only unique Agents from the METS to
    then add to the database. Agents are "repeated" per PREMIS:OBJECT
    in METS.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    mets_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    mets = metsrw.METSDocument.fromfile(mets_file)
    agents = database_helpers.collect_mets_agents(mets)
    assert len(agents) == number_of_unique_agents
