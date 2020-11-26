# -*- coding: utf-8 -*-

"""Code shared across reporting modules but not outside of reporting.
"""
from natsort import natsorted

from AIPscan.Data import fields


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
        fields.FIELD_AIP_NAME: "AIP Name",
        fields.FIELD_AIPS: "AIPs",
        fields.FIELD_AIP_SIZE: "AIP Size",
        fields.FIELD_ALL_AIPS: "All AIPs",
        fields.FIELD_COUNT: "Count",
        fields.FIELD_CREATED_DATE: "Created Date",
        fields.FIELD_DERIVATIVE_COUNT: "Derivative Count",
        fields.FIELD_DERIVATIVE_FORMAT: "Derivative Format",
        fields.FIELD_DERIVATIVE_UUID: "Derivative UUID",
        fields.FIELD_FILE_COUNT: "File Count",
        fields.FIELD_FILE_TYPE: "Type",
        fields.FIELD_FILENAME: "Filename",
        fields.FIELD_FORMAT: "Format",
        fields.FIELD_FORMATS: "Formats",
        fields.FIELD_NAME: "Name",
        fields.FIELD_ORIGINAL_UUID: "Original UUID",
        fields.FIELD_ORIGINAL_FORMAT: "Original Format",
        fields.FIELD_PUID: "PUID",
        fields.FIELD_RELATED_PAIRING: "Related Pairing",
        fields.FIELD_SIZE: "Size",
        fields.FIELD_STORAGE_NAME: "Storage Service Name",
        fields.FIELD_TRANSFER_NAME: "Transfer Name",
        fields.FIELD_VERSION: "Version",
    }
    return [field_lookup.get(header, header) for header in headers]
