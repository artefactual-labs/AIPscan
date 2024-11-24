# -*- coding: utf-8 -*-

"""Collects a number of functions that aid in the retrieval of
information from an AIP METS file.
"""
import os

import lxml
import metsrw
import requests

from AIPscan.Aggregator import database_helpers
from AIPscan.Aggregator.task_helpers import (
    create_numbered_subdirs,
    get_mets_url,
    write_mets,
)
from AIPscan.helpers import file_sha256_hash
from AIPscan.models import AIP


class METSError(Exception):
    """Exception to signal that we have encountered an error parsing
    the METS document.
    """


def parse_mets_with_metsrw(mets_file):
    """Load and Parse the METS.

    Errors which we encounter at this point will be critical to the
    caller and so an exception is returned when we can't do any better.
    """
    try:
        mets = metsrw.METSDocument.fromfile(mets_file)
    except AttributeError as err:
        # See archivematica/issues#1129 where METSRW expects a certain
        # METS structure but Archivematica has written it incorrectly.
        err = "{}: {}".format(err, mets_file)
        raise METSError("Error parsing METS: Cannot return a METSDocument")
    except lxml.etree.Error as err:
        # We have another undetermined storage service error, e.g. the
        # package no longer exists on the server, or another download
        # error.
        err = "Error parsing METS: {}: {}".format(err, mets_file)
        raise METSError(err)
    return mets


def get_aip_original_name(mets):
    """Retrieve PREMIS original name from a METSDocument object.

    If the original name cannot be reliably retrieved from the METS file
    a METSError exception is returned to be handled by the caller as
    desired.
    """

    # Negated as we're going to want to remove this length of values.
    NAMESUFFIX = -len("-00000000-0000-0000-0000-000000000000")

    # The transfer directory prefix is a directory prefix that can also
    # exist in a dmdSec intellectual entity and we want to identify and
    # ignore those.
    TRANSFER_DIR_PREFIX = "%transferDirectory%"

    NAMESPACES = {"premis": "http://www.loc.gov/premis/v3"}
    ELEM_ORIGINAL_NAME_PATTERN = ".//premis:originalName"

    original_name = ""
    for fsentry in mets.all_files():
        for dmdsec in fsentry.dmdsecs:
            dmd_element = dmdsec.serialize()
            full_name = dmd_element.find(
                ELEM_ORIGINAL_NAME_PATTERN, namespaces=NAMESPACES
            )
            if full_name is not None and full_name.text.startswith(TRANSFER_DIR_PREFIX):
                # We don't want this value, it will usually represent an
                # directory entity.
                continue
            try:
                original_name = full_name.text[:NAMESUFFIX]
            except AttributeError:
                continue

    # There should be a transfer name in every METS.
    if original_name == "":
        raise METSError("Cannot locate transfer name in METS")

    return original_name


def download_mets(
    storage_service, package_uuid, relative_path_to_mets, timestamp, package_list_no
):
    """Download METS from the storage service."""

    # Request the METS file.
    mets_response = requests.get(
        get_mets_url(storage_service, package_uuid, relative_path_to_mets)
    )

    # Create a directory to download the METS to.
    numbered_subdir = create_numbered_subdirs(timestamp, package_list_no)

    # Output METS to a convenient location to later be parsed.
    download_file = write_mets(mets_response, package_uuid, numbered_subdir)

    return download_file


def import_from_mets(
    filename,
    aip_size,
    package_uuid,
    storage_service_id,
    storage_location_id,
    fetch_job_id,
    origin_pipeline_id,
    logger,
    delete_file=False,
):
    mets_name = os.path.basename(filename)
    mets_hash = file_sha256_hash(filename)

    # If METS file's hash matches an existing value, this is a duplicate of an
    # existing AIP and we can safely ignore it.
    matching_aip = AIP.query.filter_by(mets_sha256=mets_hash).first()
    if matching_aip is not None:
        logger.info(
            "Skipping METS file {} - identical to existing record".format(mets_name)
        )
        try:
            if delete_file:
                os.remove(filename)
        except OSError as err:
            logger.warning("Unable to delete METS file: {}".format(err))
        return

    logger.info("Processing METS file {}".format(mets_name))

    try:
        mets = parse_mets_with_metsrw(filename)
    except METSError:
        # An error we need to log and report back to the user.
        return

    try:
        original_name = get_aip_original_name(mets)
    except METSError:
        # Some other error with the METS file that we might want to
        # log and act upon.
        original_name = package_uuid

    # Delete records of any previous versions of this AIP, which will shortly
    # be replaced by new records from the updated METS.
    previous_aips = AIP.query.filter_by(uuid=package_uuid).all()
    for previous_aip in previous_aips:
        logger.info(
            "Deleting record for AIP {} to replace from newer METS".format(package_uuid)
        )
        database_helpers.delete_aip_object(previous_aip)

    aip = database_helpers.create_aip_object(
        package_uuid=package_uuid,
        transfer_name=original_name,
        create_date=mets.createdate,
        mets_sha256=mets_hash,
        size=aip_size,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job_id,
        origin_pipeline_id=origin_pipeline_id,
    )

    database_helpers.process_aip_data(aip, mets)

    # Delete METS file.
    if delete_file:
        try:
            os.remove(filename)
        except OSError as err:
            logger.warning("Unable to delete METS file: {}".format(err))
