"""Collects a number of functions that aid in the retrieval of
information from an AIP METS file.
"""

import os

import lxml
import metsrw
import requests

from AIPscan.Aggregator.task_helpers import create_numbered_subdirs
from AIPscan.Aggregator.task_helpers import get_mets_url
from AIPscan.helpers import stream_write_and_hash


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
        raise METSError("Error parsing METS: Cannot return a METSDocument") from err
    except lxml.etree.Error as err:
        # We have another undetermined storage service error, e.g. the
        # package no longer exists on the server, or another download
        # error.
        msg = f"Error parsing METS: {err}: {mets_file}"
        raise METSError(msg) from err
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
    """Download METS from the storage service.

    The METS document is streamed directly to disk while its SHA256 digest is
    computed so that the caller can avoid re-reading the file.
    """

    numbered_subdir = create_numbered_subdirs(timestamp, package_list_no)
    download_file = os.path.join(numbered_subdir, f"METS.{package_uuid}.xml")

    mets_response = requests.get(
        get_mets_url(storage_service, package_uuid, relative_path_to_mets),
        stream=True,
    )

    try:
        mets_hash = stream_write_and_hash(mets_response, download_file)
    finally:
        mets_response.close()

    return download_file, mets_hash
