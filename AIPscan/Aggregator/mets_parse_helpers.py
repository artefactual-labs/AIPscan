# -*- coding: utf-8 -*-

"""Collects a number of functions that aid in the retrieval of
information from an AIP METS file.
"""
import lxml
import requests

import metsrw

from AIPscan.Aggregator.task_helpers import (
    create_numbered_subdirs,
    download_mets,
    get_mets_url,
)


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
    """Retrieve PREMIS original name from a METSDocument object."""

    # Negated as we're going to want to remove this length of values.
    NAMESUFFIX = -len("-00000000-0000-0000-0000-000000000000")

    NAMESPACES = {u"premis": u"http://www.loc.gov/premis/v3"}
    ELEM_ORIGINAL_NAME_PATTERN = ".//premis:originalName"

    FIRST_DMDSEC = "dmdSec_1"

    original_name = ""
    for fsentry in mets.all_files():
        try:
            dmdsec = fsentry.dmdsecs[0]
            if dmdsec.id_string != FIRST_DMDSEC:
                continue
            dmd_element = dmdsec.serialize()
            full_name = dmd_element.find(
                ELEM_ORIGINAL_NAME_PATTERN, namespaces=NAMESPACES
            )
            try:
                original_name = full_name.text[:NAMESUFFIX]
            except AttributeError:
                pass
            break
        except IndexError:
            pass

    if original_name == "":
        raise METSError()

    return original_name


def _download_mets(
    api_url, package_uuid, relative_path_to_mets, timestamp, package_list_no
):
    """Download METS from the storage service."""

    # Request the METS file.
    mets_response = requests.get(
        get_mets_url(api_url, package_uuid, relative_path_to_mets)
    )

    # Create a directory to download the METS to.
    numbered_subdir = create_numbered_subdirs(timestamp, package_list_no)

    # Output METS to a convenient location to later be parsed.
    download_file = download_mets(mets_response, package_uuid, numbered_subdir)

    return download_file
