"""Functions to help us tease apart a METS file and write to the
database.
"""

from datetime import datetime

from celery.utils.log import get_task_logger
from lxml import etree

from AIPscan import db
from AIPscan.Aggregator import tasks
from AIPscan.Aggregator.task_helpers import _tz_neutral_date
from AIPscan.Aggregator.task_helpers import get_storage_service_api_url
from AIPscan.models import AIP
from AIPscan.models import Agent
from AIPscan.models import Event
from AIPscan.models import EventAgent
from AIPscan.models import FetchJob
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.models import Pipeline
from AIPscan.models import StorageLocation

logger = get_task_logger(__name__)


ORIGINAL_OBJECT = "original"
PRESERVATION_OBJECT = "preservation"


def _extract_event_detail(premis_event, file_id):
    """Extract the detail from the event and write a new event object
    to the database"""
    event_type = premis_event.event_type
    event_uuid = premis_event.event_identifier_value
    event_date = _tz_neutral_date(premis_event.event_date_time)
    # We have a strange issue with this logged: https://github.com/archivematica/Issues/issues/743
    event_detail, event_outcome, event_outcome_detail = None, None, None
    if not isinstance(premis_event.event_detail, tuple):
        event_detail = premis_event.event_detail
    if not isinstance(premis_event.event_outcome, tuple):
        event_outcome = premis_event.event_outcome
    if not isinstance(premis_event.event_outcome_detail_note, tuple):
        event_outcome_detail = premis_event.event_outcome_detail_note
    event = Event(
        event_type=event_type,
        uuid=event_uuid,
        date=event_date,
        detail=event_detail,
        outcome=event_outcome,
        outcome_detail=event_outcome_detail,
        file_id=file_id,
    )
    return event


def _create_agent_type_id(identifier_type, identifier_value):
    """Create a key-pair string for the linking_type_value in the db."""
    return f"{identifier_type}-{identifier_value}"


def _create_event_agent_relationship(event_id, agent_identifier):
    """Generator object helper for looping through an event's agents and
    returning the event-agent IDs.
    """
    for agent_ in agent_identifier:
        id_ = _create_agent_type_id(
            agent_.linking_agent_identifier_type, agent_.linking_agent_identifier_value
        )
        existing_agent = Agent.query.filter_by(linking_type_value=id_).first()
        event_relationship = EventAgent.insert().values(
            event_id=event_id, agent_id=existing_agent.id
        )
        yield event_relationship


def create_event_objects(fs_entry, file_id):
    """Add information about PREMIS Events associated with file to database

    :param fs_entry: mets-reader-writer FSEntry object
    :param file_id: File ID
    """
    for premis_event in fs_entry.get_premis_events():
        event = _extract_event_detail(premis_event, file_id)
        db.session.add(event)
        db.session.commit()

        for event_relationship in _create_event_agent_relationship(
            event.id, premis_event.linking_agent_identifier
        ):
            db.session.execute(event_relationship)
        db.session.commit()


def _extract_agent_detail(agent, storage_service_id):
    """Pull the agent information from the agent record and return an
    agent object ready to insert into the database.
    """
    linking_type_value = agent[0]
    agent_type = agent[1]
    agent_value = agent[2]
    return Agent(
        linking_type_value=linking_type_value,
        agent_type=agent_type,
        agent_value=agent_value,
        storage_service_id=storage_service_id,
    )


def create_agent_objects(unique_agents, storage_service_id):
    """Add our agents to the database. The list is already the
    equivalent of a set by the time it reaches here and so we don't
    need to perform any de-duplication.
    """
    for agent in unique_agents:
        agent_obj = _extract_agent_detail(agent, storage_service_id)
        exists = Agent.query.filter_by(
            linking_type_value=agent_obj.linking_type_value,
            agent_type=agent_obj.agent_type,
            agent_value=agent_obj.agent_value,
            storage_service_id=storage_service_id,
        ).count()
        if exists:
            continue
        logger.info("Adding: %s", agent_obj)
        db.session.add(agent_obj)
    db.session.commit()


def _get_unique_agents(all_agents, agents_list):
    """Return unique agents associated with a file in the AIP. Returns
    a list of tuples organized by (linking_type_value, type,
    value), e.g. (Archivematica user pk 4, Archivematica User, Eric).
    Linking type and value become one because only together are these
    two considered useful, they just happen to exist as two elements
    in the PREMIS dictionary.
    """
    agents = []
    linking_type_value = ""
    for agent in all_agents:
        linking_type_value = _create_agent_type_id(
            agent.agent_identifier[0].agent_identifier_type,
            agent.agent_identifier[0].agent_identifier_value,
        )
        agent_tuple = (linking_type_value, agent.type, agent.name)
        if agent_tuple not in agents_list:
            agents.append(agent_tuple)
    return agents


def create_aip_object(
    package_uuid,
    transfer_name,
    create_date,
    mets_sha256,
    size=0,
    storage_service_id=1,
    storage_location_id=1,
    fetch_job_id=1,
    origin_pipeline_id=1,
):
    """Create an AIP object and save it to the database."""
    aip = AIP(
        uuid=package_uuid,
        transfer_name=transfer_name,
        create_date=_tz_neutral_date(create_date),
        mets_sha256=mets_sha256,
        size=size,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job_id,
        origin_pipeline_id=origin_pipeline_id,
    )
    db.session.add(aip)
    db.session.commit()
    return aip


def delete_aip_object(aip):
    """Delete AIP object from database.

    :param aip: AIP model instance
    """
    db.session.delete(aip)
    db.session.commit()


def create_storage_location_object(current_location, description, storage_service_id):
    """Create a StorageLocation and save it to the database."""
    storage_location = StorageLocation(
        current_location=current_location,
        description=description,
        storage_service_id=storage_service_id,
    )
    db.session.add(storage_location)
    db.session.commit()
    return storage_location


def create_or_update_storage_location(current_location, storage_service):
    """Create or update Storage Location and return it."""
    storage_location = StorageLocation.query.filter_by(
        current_location=current_location
    ).first()

    request_url, request_url_without_api_key = get_storage_service_api_url(
        storage_service, current_location
    )
    response = tasks.make_request(request_url, request_url_without_api_key)
    description = response.get("description")
    if not storage_location:
        return create_storage_location_object(
            current_location, description, storage_service.id
        )

    if storage_location.description != description:
        storage_location.description = description
        db.session.commit()

    return storage_location


def create_pipeline_object(origin_pipeline, dashboard_url):
    """Create a Pipeline and save it to the database."""
    pipeline = Pipeline(origin_pipeline=origin_pipeline, dashboard_url=dashboard_url)
    db.session.add(pipeline)
    db.session.commit()
    return pipeline


def create_or_update_pipeline(origin_pipeline, storage_service):
    """Create or update Storage Location and return it."""
    pipeline = Pipeline.query.filter_by(origin_pipeline=origin_pipeline).first()

    request_url, request_url_without_api_key = get_storage_service_api_url(
        storage_service, origin_pipeline
    )
    response = tasks.make_request(request_url, request_url_without_api_key)
    dashboard_url = response.get("remote_name")
    if not pipeline:
        return create_pipeline_object(origin_pipeline, dashboard_url)

    if pipeline.dashboard_url != dashboard_url:
        pipeline.dashboard_url = dashboard_url
        db.session.commit()

    return pipeline


def _get_file_properties(fs_entry):
    """Retrieve file properties from FSEntry

    :param fs_entry: mets-reader-writer FSEntry object

    :returns: Dict of file properties
    """
    file_info = {
        "uuid": fs_entry.file_uuid,
        "name": fs_entry.label,
        "filepath": fs_entry.path,
        "size": None,
        "date_created": None,
        "puid": None,
        "file_format": None,
        "format_version": None,
        "checksum_type": None,
        "checksum_value": None,
        "related_uuid": None,
    }

    try:
        for premis_object in fs_entry.get_premis_objects():
            file_info["size"] = premis_object.size
            key_alias = premis_object.format_registry_key
            file_info["date_created"] = _tz_neutral_date(
                premis_object.date_created_by_application
            )
            if not isinstance(key_alias, tuple):
                file_info["puid"] = key_alias
            file_info["file_format"] = premis_object.format_name
            version_alias = premis_object.format_version
            if not isinstance(version_alias, tuple):
                file_info["format_version"] = version_alias
            file_info["checksum_type"] = premis_object.message_digest_algorithm
            file_info["checksum_value"] = premis_object.message_digest
            related_uuid_alias = premis_object.related_object_identifier_value
            if not isinstance(related_uuid_alias, tuple):
                file_info["related_uuid"] = related_uuid_alias
    except AttributeError:
        # File error/warning to log. Obviously this format may
        # be incorrect so it is our best guess.
        file_info["file_format"] = "ISO Disk Image File"
        file_info["puid"] = "fmt/468"

    return file_info


def _add_normalization_date(file_id):
    """Add normalization date from PREMIS creation Event to preservation file

    :param file_id: File ID
    """
    file_ = db.session.get(File, file_id)
    creation_event = Event.query.filter_by(file_id=file_.id, type="creation").first()
    if creation_event is not None:
        file_.date_created = creation_event.date
        db.session.commit()


def _add_premis_object_xml(fs_entry, file_id):
    """Add string representation of PREMIS Object to File object."""
    file_ = db.session.get(File, file_id)

    if hasattr(fs_entry, "amdsecs"):
        for ss in fs_entry.amdsecs[0].subsections:
            if ss.contents.mdtype == fs_entry.PREMIS_OBJECT:
                file_.premis_object = etree.tostring(
                    ss.contents.serialize(), encoding="unicode", pretty_print=True
                )
        db.session.commit()


def _get_original_file(related_uuid):
    """Get original file related to preservation derivative."""
    return File.query.filter_by(uuid=related_uuid, file_type=FileType.original).first()


def create_file_object(file_type, fs_entry, aip_id):
    """Add file to database

    :param file_type: models.FileType enum
    :param fs_entry: mets-reader-writer FSEntry object
    :param aip_id: AIP ID
    """
    file_info = _get_file_properties(fs_entry)

    original_file_id = None
    if file_type is FileType.preservation:
        original_file = _get_original_file(file_info["related_uuid"])
        if original_file:
            original_file_id = original_file.id

    new_file = File(
        name=file_info.get("name"),
        filepath=file_info.get("filepath"),
        uuid=file_info.get("uuid"),
        file_type=file_type,
        size=file_info.get("size"),
        date_created=file_info.get("date_created"),
        puid=file_info.get("puid"),
        file_format=file_info.get("file_format"),
        format_version=file_info.get("format_version"),
        checksum_type=file_info.get("checksum_type"),
        checksum_value=file_info.get("checksum_value"),
        original_file_id=original_file_id,
        aip_id=aip_id,
    )

    logger.debug("Adding file %s %s", new_file.name, aip_id)

    db.session.add(new_file)
    db.session.commit()

    create_event_objects(fs_entry, new_file.id)

    if file_type == FileType.preservation:
        _add_normalization_date(new_file.id)

    _add_premis_object_xml(fs_entry, new_file.id)


def collect_mets_agents(mets):
    """Collect all of the unique agents in the METS file to write to the
    database.
    """
    agents = []
    for aip_file in mets.all_files():
        if aip_file.use != ORIGINAL_OBJECT and aip_file.use != PRESERVATION_OBJECT:
            continue
        agents = agents + _get_unique_agents(aip_file.get_premis_agents(), agents)
    logger.info("Total agents: %d", len(agents))
    return agents


def process_aip_data(aip, mets):
    """Populate database with information needed for reporting from METS file

    :param aip: AIP object
    :param mets: mets-reader-writer METSDocument object
    """
    tasks.get_mets.update_state(state="IN PROGRESS")

    create_agent_objects(collect_mets_agents(mets), aip.storage_service_id)

    all_files = mets.all_files()

    # Parse the original files first so that they are available as foreign keys
    # when we parse preservation and derivative files.
    original_files = [file_ for file_ in all_files if file_.use == "original"]
    for file_ in original_files:
        create_file_object(FileType.original, file_, aip.id)

    preservation_files = [file_ for file_ in all_files if file_.use == "preservation"]
    for file_ in preservation_files:
        create_file_object(FileType.preservation, file_, aip.id)


def create_fetch_job(datetime_obj_start, timestamp_str, storage_server_id):
    fetch_job = FetchJob(
        total_packages=None,
        total_deleted_aips=None,
        total_aips=None,
        download_start=datetime_obj_start,
        download_end=None,
        download_directory=f"AIPscan/Aggregator/downloads/{timestamp_str}/",
        storage_service_id=storage_server_id,
    )
    db.session.add(fetch_job)
    db.session.commit()

    return fetch_job


def update_fetch_job(fetch_job_id, processed_packages, total_packages_count):
    # Count different types of packages
    total_aips = 0
    total_sips = 0
    total_dips = 0
    total_deleted_aips = 0
    total_replicas = 0

    for package in processed_packages:
        if package.is_aip():
            total_aips += 1

        if package.is_sip():
            total_sips += 1

        if package.is_dip():
            total_dips += 1

        if package.is_deleted():
            total_deleted_aips += 1

        if package.is_replica():
            total_replicas += 1

    # Store counts of different types of packages
    obj = FetchJob.query.filter_by(id=fetch_job_id).first()
    obj.total_packages = total_packages_count
    obj.total_aips = total_aips
    obj.total_dips = total_dips
    obj.total_sips = total_sips
    obj.total_replicas = total_replicas
    obj.total_deleted_aips = total_deleted_aips
    obj.download_end = datetime.now().replace(microsecond=0)
    db.session.commit()

    return obj
