# -*- coding: utf-8 -*-

"""Code shared across reporting modules but not outside of reporting.
"""
from natsort import natsorted

from AIPscan.Data import data


def sort_puids(puids):
    """Return PUIDs sorted in natural sorting order.

    Python sorts strings containining integers in ASCII order - i.e.
    ["fmt/1", "fmt/10", "fmt/2"]. Since this is different than what end
    users expect, this helper uses the natsort library to reorder PUIDs
    into natural sort order - i.e. ["fmt/1", "fmt/2", "fmt/10"].

    :param puids: List of PUIDs

    :returns: Sorted list of PUIDs
    """
    return natsorted(puids)


def translate_headers(headers):
    """Translate headers from something machine readable to something
    more user friendly and translatable.
    """
    field_lookup = {
        data.FIELD_AIP_NAME: "AIP Name",
        data.FIELD_AIPS: "AIPs",
        data.FIELD_AIP_SIZE: "AIP Size",
        data.FIELD_ALL_AIPS: "All AIPs",
        data.FIELD_COUNT: "Count",
        data.FIELD_CREATED_DATE: "Created Date",
        data.FIELD_DERIVATIVE_COUNT: "Derivative Count",
        data.FIELD_DERIVATIVE_FORMAT: "Derivative Format",
        data.FIELD_DERIVATIVE_UUID: "Derivative UUID",
        data.FIELD_FILE_COUNT: "File Count",
        data.FIELD_FILE_TYPE: "Type",
        data.FIELD_FILENAME: "Filename",
        data.FIELD_FORMAT: "Format",
        data.FIELD_FORMATS: "Formats",
        data.FIELD_NAME: "Name",
        data.FIELD_ORIGINAL_UUID: "Original UUID",
        data.FIELD_ORIGINAL_FORMAT: "Original Format",
        data.FIELD_PUID: "PUID",
        data.FIELD_RELATED_PAIRING: "Related Pairing",
        data.FIELD_SIZE: "Size",
        data.FIELD_STORAGE_NAME: "Storage Service Name",
        data.FIELD_TRANSFER_NAME: "Transfer Name",
        data.FIELD_VERSION: "Version",
    }
    return [field_lookup.get(header, header) for header in headers]
