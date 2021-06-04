# -*- coding: utf-8 -*-
import os
import uuid
from datetime import datetime

import metsrw
import pytest

from AIPscan.Aggregator import database_helpers
from AIPscan.models import AIP, Agent, File, FileType

FIXTURES_DIR = "fixtures"

TEST_SHA_256 = "79c16fa9573ec46c5f60fd54b34f314159e0623ca53d8d2f00c5875dbb4e0dfd"

BASE_FILE_DICT = {
    "name": "newfile.ext",
    "filepath": "/path/to/newfile.ext",
    "uuid": str(uuid.uuid4()),
    "date_created": datetime.now(),
    "puid": "fmt/1",
    "file_format": "Test Format",
    "size": "12345",
    "format_version": "1",
    "checksum_type": "sha-256",
    "checksum_value": "123456",
}

ORIGINAL_FILE_DICT = BASE_FILE_DICT.copy()
ORIGINAL_FILE_DICT["file_type"] = FileType.original

PRESERVATION_FILE_DICT = BASE_FILE_DICT.copy()
PRESERVATION_FILE_DICT["file_type"] = FileType.preservation
PRESERVATION_FILE_DICT["related_uuid"] = str(uuid.uuid4())


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


@pytest.mark.parametrize(
    "file_type, file_dict, is_original, connected_to_original",
    [
        # Test original file.
        (FileType.original, ORIGINAL_FILE_DICT, True, False),
        # Test preservation file tied to original.
        (FileType.preservation, PRESERVATION_FILE_DICT, False, True),
        # Test preservation file not tied to original.
        (FileType.preservation, PRESERVATION_FILE_DICT, False, False),
    ],
)
def test_create_file_object(
    app_with_populated_files,
    mocker,
    file_type,
    file_dict,
    is_original,
    connected_to_original,
):
    """Test adding files to database."""
    aip = AIP.query.first()
    first_original_file = File.query.filter_by(
        aip_id=aip.id, file_type=FileType.original.value
    ).first()

    get_file_props = mocker.patch(
        "AIPscan.Aggregator.database_helpers._get_file_properties"
    )
    get_file_props.return_value = file_dict

    get_original_file = mocker.patch(
        "AIPscan.Aggregator.database_helpers._get_original_file"
    )
    if not is_original:
        get_original_file.return_value = first_original_file

    mocker.patch("AIPscan.Aggregator.database_helpers.create_event_objects")
    add_normalization_date = mocker.patch(
        "AIPscan.Aggregator.database_helpers._add_normalization_date"
    )

    files_in_db = File.query.filter_by(aip_id=aip.id).all()
    assert len(files_in_db) == 2
    original_files = File.query.filter_by(
        aip_id=aip.id, file_type=FileType.original
    ).all()
    assert len(original_files) == 1
    preservation_files = File.query.filter_by(
        aip_id=aip.id, file_type=FileType.preservation
    ).all()
    assert len(preservation_files) == 1

    database_helpers.create_file_object(file_type, None, aip.id)

    files_in_db = File.query.filter_by(aip_id=aip.id).all()
    assert len(files_in_db) == 3
    if is_original:
        original_files = File.query.filter_by(
            aip_id=aip.id, file_type=FileType.original
        ).all()
        assert len(original_files) == 2
        preservation_files = File.query.filter_by(
            aip_id=aip.id, file_type=FileType.preservation
        ).all()
        assert len(preservation_files) == 1
        add_normalization_date.assert_not_called()
    else:
        original_files = File.query.filter_by(
            aip_id=aip.id, file_type=FileType.original
        ).all()
        assert len(original_files) == 1
        preservation_files = File.query.filter_by(
            aip_id=aip.id, file_type=FileType.preservation
        ).all()
        assert len(preservation_files) == 2
        add_normalization_date.assert_called_once()
