# -*- coding: utf-8 -*-

"""Functions to help us tease apart a METS file and write to the
database.
"""

from celery.utils.log import get_task_logger

from AIPscan import db
from AIPscan.models import aips, originals, copies, events

from AIPscan.Aggregator.task_helpers import _tz_neutral_date

from AIPscan.Aggregator import tasks

logger = get_task_logger(__name__)


def create_aip_object(
    package_uuid, transfer_name, create_date, storage_service_id, fetch_job_id
):
    """Create an AIP object and save it to the database."""
    aip = aips(
        package_uuid,
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


def _create_event_objs(aip_file, file_obj_id):
    """Retrieve information about events associated with a file and
    add that information to the database.
    """
    for premis_event in aip_file.get_premis_events():
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
        db.session.add(event)
        db.session.commit()


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

    _create_event_objs(aip_file, file_obj.id)


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


def process_aip_data(aip, aip_uuid, mets):
    """Process the METS for as much information about the AIP as we
    need for reporting.
    """

    ORIGINAL_OBJECT = "original"
    PRESERVATION_OBJECT = "preservation"

    for aip_file in mets.all_files():
        if aip_file.use != ORIGINAL_OBJECT and aip_file.use != PRESERVATION_OBJECT:
            # Move onto the next file quickly.
            continue

        tasks.get_mets.update_state(state="IN PROGRESS")

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
