import os
import uuid
from datetime import datetime

import metsrw
import pytest

from AIPscan import db
from AIPscan.Aggregator import database_helpers
from AIPscan.Aggregator import types
from AIPscan.conftest import ORIGIN_PIPELINE
from AIPscan.conftest import STORAGE_LOCATION_1_CURRENT_LOCATION
from AIPscan.models import AIP
from AIPscan.models import Agent
from AIPscan.models import FetchJob
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.models import Pipeline
from AIPscan.models import StorageLocation
from AIPscan.models import StorageService

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


def test_create_storage_location_object(app_instance):
    LOCATION_UUID = str(uuid.uuid4())
    CURRENT_LOCATION = f"/api/v2/location/{LOCATION_UUID}"
    DESCRIPTION = "My test AIP Store location"
    STORAGE_SERVICE_ID = 1

    database_helpers.create_storage_location_object(
        current_location=CURRENT_LOCATION,
        description=DESCRIPTION,
        storage_service_id=STORAGE_SERVICE_ID,
    )

    storage_location = StorageLocation.query.filter_by(
        current_location=CURRENT_LOCATION
    ).first()
    assert storage_location is not None
    assert storage_location.current_location == CURRENT_LOCATION
    assert storage_location.uuid == LOCATION_UUID
    assert storage_location.description == DESCRIPTION
    assert storage_location.storage_service_id == STORAGE_SERVICE_ID


def test_create_pipeline_object(app_instance):
    LOCATION_UUID = str(uuid.uuid4())
    ORIGIN_PIPELINE = f"/api/v2/pipeline/{LOCATION_UUID}"
    DASHBOARD_URL = "http://tessas-am-dashboard.example.com"

    database_helpers.create_pipeline_object(
        origin_pipeline=ORIGIN_PIPELINE, dashboard_url=DASHBOARD_URL
    )

    pipeline = Pipeline.query.filter_by(origin_pipeline=ORIGIN_PIPELINE).first()
    assert pipeline is not None
    assert pipeline.origin_pipeline == ORIGIN_PIPELINE
    assert pipeline.dashboard_url == DASHBOARD_URL


def test_create_aip(app_instance):
    """Test AIP creation."""
    PACKAGE_UUID = str(uuid.uuid4())
    TRANSFER_NAME = "some name"
    STORAGE_SERVICE_ID = 1
    STORAGE_LOCATION_ID = 1
    FETCH_JOB_ID = 1
    ORIGIN_PIPELINE_ID = 1

    database_helpers.create_aip_object(
        package_uuid=PACKAGE_UUID,
        transfer_name=TRANSFER_NAME,
        create_date="2020-11-02",
        mets_sha256=TEST_SHA_256,
        storage_service_id=STORAGE_SERVICE_ID,
        storage_location_id=STORAGE_LOCATION_ID,
        fetch_job_id=FETCH_JOB_ID,
        origin_pipeline_id=ORIGIN_PIPELINE_ID,
    )

    aip = AIP.query.filter_by(uuid=PACKAGE_UUID).first()
    assert aip is not None
    assert aip.transfer_name == TRANSFER_NAME
    assert aip.storage_service_id == STORAGE_SERVICE_ID
    assert aip.fetch_job_id == FETCH_JOB_ID
    assert aip.origin_pipeline_id == ORIGIN_PIPELINE_ID


def test_delete_aip(app_instance):
    """Test AIP deletion."""
    PACKAGE_UUID = str(uuid.uuid4())

    database_helpers.create_aip_object(
        package_uuid=PACKAGE_UUID,
        transfer_name="some name",
        create_date="2020-11-02",
        mets_sha256=TEST_SHA_256,
        storage_service_id=1,
        storage_location_id=1,
        fetch_job_id=1,
        origin_pipeline_id=1,
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
            storage_service_id="1",
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


@pytest.mark.parametrize(
    "current_location, storage_service_id, new_description, location_created",
    [
        # Create Storage Location if matching one doesn't exist.
        ("/api/v2/location/new-location/", 1, "", True),
        # Update Storage Location description if already exists.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, 1, "updated description", False),
    ],
)
def test_create_or_update_storage_location(
    storage_locations,
    mocker,
    current_location,
    storage_service_id,
    new_description,
    location_created,
):
    """Test that Storage Locations are created or updated as expected."""
    make_request = mocker.patch("AIPscan.Aggregator.tasks.make_request")
    make_request.return_value = {"description": new_description}

    create_storage_location_object = mocker.patch(
        "AIPscan.Aggregator.database_helpers.create_storage_location_object"
    )

    storage_service = db.session.get(StorageService, 1)

    storage_location = database_helpers.create_or_update_storage_location(
        current_location=current_location, storage_service=storage_service
    )

    if location_created:
        create_storage_location_object.assert_called_once()
    else:
        assert storage_location.description == new_description


@pytest.mark.parametrize(
    "origin_pipeline, new_url, pipeline_created",
    [
        # Create Pipeline if matching one doesn't exist.
        ("/api/v2/pipeline/new-pipeline/", "", True),
        # Update Pipeline's dashboard URL if already exists.
        (ORIGIN_PIPELINE, "http://new-url.example.com", False),
    ],
)
def test_create_or_update_pipeline(
    storage_locations, mocker, origin_pipeline, new_url, pipeline_created
):
    """Test that Storage Locations are created or updated as expected."""
    make_request = mocker.patch("AIPscan.Aggregator.tasks.make_request")
    make_request.return_value = {"remote_name": new_url}

    create_pipeline_object = mocker.patch(
        "AIPscan.Aggregator.database_helpers.create_pipeline_object"
    )

    get_storage_service_api_url = mocker.patch(
        "AIPscan.Aggregator.database_helpers.get_storage_service_api_url"
    )
    get_storage_service_api_url.return_value = (None, None)

    storage_service = db.session.get(StorageService, 1)

    pipeline = database_helpers.create_or_update_pipeline(
        origin_pipeline=origin_pipeline, storage_service=storage_service
    )

    if pipeline_created:
        create_pipeline_object.assert_called_once()
    else:
        assert pipeline.dashboard_url == new_url


def test_create_fetch_job(app_instance, mocker):
    datetime_obj_start = datetime.now().replace(microsecond=0)
    timestamp_str = datetime_obj_start.strftime("%Y-%m-%d-%H-%M-%S")
    storage_service_id = 1

    mocker.patch("AIPscan.db.session.add")
    mocker.patch("AIPscan.db.session.commit")

    fetch_job = database_helpers.create_fetch_job(
        datetime_obj_start, timestamp_str, storage_service_id
    )
    assert fetch_job.total_packages is None
    assert fetch_job.total_deleted_aips is None
    assert fetch_job.total_aips is None
    assert fetch_job.download_start == datetime_obj_start
    assert fetch_job.download_end is None
    assert (
        fetch_job.download_directory == f"AIPscan/Aggregator/downloads/{timestamp_str}/"
    )
    assert fetch_job.storage_service_id == storage_service_id


def test_update_fetch_job(app_instance, mocker):
    fetch_job = FetchJob(
        total_packages=0,
        total_aips=0,
        total_deleted_aips=0,
        download_start=datetime.now(),
        download_end=datetime.now(),
        download_directory="/some/directory/",
        storage_service_id=1,
    )

    mocker.patch("sqlalchemy.orm.query.Query.first", return_value=fetch_job)
    mocker.patch("AIPscan.db.session.commit")

    # Define processed packages
    deleted = types.StorageServicePackage()
    deleted.deleted = True

    replica = types.StorageServicePackage()
    replica.replica = True
    replica.aip = True

    aip = types.StorageServicePackage()
    aip.aip = True

    dip = types.StorageServicePackage()
    dip.dip = True

    sip = types.StorageServicePackage()
    sip.sip = True

    processed_packages = [deleted, replica, aip, dip, sip]

    # Only some packags may have been processed
    total_packages_count = 10

    obj = database_helpers.update_fetch_job(1, processed_packages, total_packages_count)

    assert obj.total_packages == total_packages_count
    assert obj.total_deleted_aips == 1
    assert obj.total_replicas == 1
    assert obj.total_aips == 1
    assert obj.total_dips == 1
    assert obj.total_sips == 1
