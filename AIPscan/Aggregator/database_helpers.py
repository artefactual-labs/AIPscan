# -*- coding: utf-8 -*-

"""Functions to help us tease apart a METS file and write to the
database.
"""

from celery.utils.log import get_task_logger

from AIPscan import db
from AIPscan.models import Agents, EventAgents, aips, originals, copies, events

from AIPscan.Aggregator.task_helpers import _tz_neutral_date
from AIPscan.Aggregator import tasks

logger = get_task_logger(__name__)


ORIGINAL_OBJECT = "original"
PRESERVATION_OBJECT = "preservation"


def _extract_event_detail(premis_event, file_obj_id):
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
    original_id = file_obj_id
    event = events(
        type=event_type,
        uuid=event_uuid,
        date=event_date,
        detail=event_detail,
        outcome=event_outcome,
        outcome_detail=event_outcome_detail,
        original_id=original_id,
    )
    return event


def _create_agent_type_id(identifier_type, identifier_value):
    """Create a key-pair string for the linking_type_value in the db.
    """
    return "{}-{}".format(identifier_type, identifier_value)


def _create_event_agent_relationship(event_id, agent_identifier):
    """Generator object helper for looping through an event's agents and
    returning the event-agent IDs.
    """
    for agent_ in agent_identifier:
        id_ = _create_agent_type_id(
            agent_.linking_agent_identifier_type, agent_.linking_agent_identifier_value
        )
        existing_agent = Agents.query.filter_by(linking_type_value=id_).first()
        event_relationship = EventAgents.insert().values(
            event_id=event_id, agent_id=existing_agent.id
        )
        yield event_relationship


def create_event_objects(aip_file, file_obj_id):
    """Retrieve information about events associated with a file and
    add that information to the database.
    """
    for premis_event in aip_file.get_premis_events():
        event = _extract_event_detail(premis_event, file_obj_id)
        db.session.add(event)
        for event_relationship in _create_event_agent_relationship(
            event.id, premis_event.linking_agent_identifier
        ):
            db.session.execute(event_relationship)
        db.session.commit()


def _extract_agent_detail(agent):
    """Pull the agent information from the agent record and return an
    agent object ready to insert into the database.
    """
    linking_type_value = agent[0]
    agent_type = agent[1]
    agent_value = agent[2]
    return Agents(
        linking_type_value=linking_type_value,
        agent_type=agent_type,
        agent_value=agent_value,
    )


def create_agent_objects(unique_agents):
    """Add our agents to the database. The list is already the
    equivalent of a set by the time it reaches here and so we don't
    need to perform any de-duplication.
    """
    for agent in unique_agents:
        agent_obj = _extract_agent_detail(agent)
        exists = Agents.query.filter_by(
            linking_type_value=agent_obj.linking_type_value,
            agent_type=agent_obj.agent_type,
            agent_value=agent_obj.agent_value,
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
    package_uuid, transfer_name, create_date, storage_service_id, fetch_job_id
):
    """Create an AIP object and save it to the database."""
    aip = aips(
        uuid=package_uuid,
        transfer_name=transfer_name,
        create_date=_tz_neutral_date(create_date),
        originals_count=None,
        copies_count=None,
        storage_service_id=storage_service_id,
        fetch_job_id=fetch_job_id,
    )
    db.session.add(aip)
    db.session.commit()
    return aip


def _add_file_original(
    aip_id,
    aip_file,
    file_name,
    file_uuid,
    file_size,
    last_modified_date,
    puid,
    file_format,
    format_version,
    checksum_type,
    checksum_value,
    related_uuid,
):
    """Add a new original file to the database."""
    file_obj = originals(
        aip_id=aip_id,
        name=file_name,
        uuid=file_uuid,
        size=file_size,
        last_modified_date=last_modified_date,
        puid=puid,
        file_format=file_format,
        format_version=format_version,
        checksum_type=checksum_type,
        checksum_value=checksum_value,
        related_uuid=related_uuid,
    )

    logger.debug("Adding original %s %s", file_obj, aip_id)

    db.session.add(file_obj)
    db.session.commit()

    create_event_objects(aip_file, file_obj.id)


def _add_file_preservation(
    aip_id,
    aip_file,
    file_name,
    file_uuid,
    file_size,
    file_format,
    checksum_type,
    checksum_value,
    related_uuid,
):
    """Add a preservation copy of a file to the database."""
    event_date = None
    for premis_event in aip_file.get_premis_events():
        if (premis_event.event_type) == "creation":
            event_date = (premis_event.event_date_time)[0:19]
            event_date = _tz_neutral_date(premis_event.event_date_time)

    file_obj = copies(
        aip_id=aip_id,
        name=file_name,
        uuid=file_uuid,
        size=file_size,
        file_format=file_format,
        checksum_type=checksum_type,
        checksum_value=checksum_value,
        related_uuid=related_uuid,
        normalization_date=event_date,
    )

    logger.debug("Adding preservation %s", file_obj)

    db.session.add(file_obj)
    db.session.commit()


def collect_mets_agents(mets):
    """Collect all of the unique agents in the METS file to write to the
    database.
    """
    agents = []
    for aip_file in mets.all_files():
        if aip_file.use != ORIGINAL_OBJECT and aip_file.use != PRESERVATION_OBJECT:
            continue
        agents = agents + _get_unique_agents(aip_file.get_premis_agents(), agents)
    logger.info("Total  agents: %d", len(agents))
    return agents


def process_mets(aip, aip_uuid, mets):
    """Process the mets file into the database."""
    for aip_file in mets.all_files():
        if aip_file.use != ORIGINAL_OBJECT and aip_file.use != PRESERVATION_OBJECT:
            # Move onto the next file quickly.
            continue

        tasks.get_mets.update_state(state="IN PROGRESS")

        # Setup initial values that we're going to commit to the
        # database. If we don't find them in the AIP data then with the
        # current architecture we require placeholders to avoid
        # attribute errors.
        file_uuid = aip_file.file_uuid
        file_name = aip_file.label
        file_size = None
        puid = None
        file_format = None
        format_version = None
        related_uuid = None
        checksum_type = None
        checksum_value = None
        last_modified_date = None

        try:
            for premis_object in aip_file.get_premis_objects():
                file_size = premis_object.size
                key_alias = premis_object.format_registry_key
                last_modified_date = _tz_neutral_date(
                    premis_object.date_created_by_application
                )
                if not isinstance(key_alias, tuple):
                    puid = key_alias
                file_format = premis_object.format_name
                version_alias = premis_object.format_version
                if not isinstance(version_alias, tuple):
                    format_version = version_alias
                checksum_type = premis_object.message_digest_algorithm
                checksum_value = premis_object.message_digest
                related_uuid_alias = premis_object.related_object_identifier_value
                if not isinstance(related_uuid_alias, tuple):
                    related_uuid = related_uuid_alias
        except AttributeError:
            # File error/warning to log. Obviously this format may
            # be incorrect so it is our best guess.
            file_format = "ISO Disk Image File"
            puid = "fmt/468"

        if aip_file.use == ORIGINAL_OBJECT:
            _add_file_original(
                aip_id=aip.id,
                aip_file=aip_file,
                file_name=file_name,
                file_uuid=file_uuid,
                file_size=file_size,
                last_modified_date=last_modified_date,
                puid=puid,
                file_format=file_format,
                format_version=format_version,
                checksum_type=checksum_type,
                checksum_value=checksum_value,
                related_uuid=related_uuid,
            )

        if aip_file.use == PRESERVATION_OBJECT:
            _add_file_preservation(
                aip_id=aip.id,
                aip_file=aip_file,
                file_name=file_name,
                file_uuid=file_uuid,
                file_size=file_size,
                file_format=file_format,
                checksum_type=checksum_type,
                checksum_value=checksum_value,
                related_uuid=related_uuid,
            )

    aip.originals_count = originals.query.filter_by(aip_id=aip.id).count()
    aip.copies_count = copies.query.filter_by(aip_id=aip.id).count()
    db.session.commit()


def process_aip_data(aip, aip_uuid, mets):
    """Process the METS for as much information about the AIP as we
    need for reporting.
    """
    create_agent_objects(collect_mets_agents(mets))
    process_mets(aip, aip_uuid, mets)
