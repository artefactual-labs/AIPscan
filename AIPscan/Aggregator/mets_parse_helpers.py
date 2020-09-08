# -*- coding: utf-8 -*-

"""Collects a number of functions that aid in the retrieval of
information from an AIP METS file.
"""


class METSError(Exception):
    """Exception to signal that we have encountered an error parsing
    the METS document.
    """


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
