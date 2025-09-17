"""Code shared across reporting modules but not outside of reporting."""

import csv
from datetime import timedelta
from io import StringIO

from flask import make_response
from natsort import natsorted

from AIPscan.Data import fields
from AIPscan.helpers import filesizeformat


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


def translate_headers(headers, add_bytes_column=False):
    """Translate headers from something machine readable to something
    more user friendly and translatable.
    """
    field_lookup = {
        fields.FIELD_AIP_NAME: "AIP Name",
        fields.FIELD_AIPS: "AIPs",
        fields.FIELD_AIP_SIZE: "AIP Size",
        fields.FIELD_AIP_UUID: "AIP UUID",
        fields.FIELD_ALL_AIPS: "All AIPs",
        fields.FIELD_COUNT: "Count",
        fields.FIELD_CREATED_DATE: "Created Date",
        fields.FIELD_DATE_START: "Start Date",
        fields.FIELD_DATE_END: "End Date",
        fields.FIELD_DURATION: "Duration",
        fields.FIELD_DERIVATIVE_COUNT: "Derivative Count",
        fields.FIELD_DERIVATIVE_FILE: "Derivative File",
        fields.FIELD_DERIVATIVE_FORMAT: "Derivative Format",
        fields.FIELD_DERIVATIVE_UUID: "Derivative UUID",
        fields.FIELD_FILE_COUNT: "File Count",
        fields.FIELD_FILE_TYPE: "Type",
        fields.FIELD_FILENAME: "Filename",
        fields.FIELD_FORMAT: "Format",
        fields.FIELD_FORMATS: "Formats",
        fields.FIELD_ID: "ID",
        fields.FIELD_NAME: "Name",
        fields.FIELD_ORIGINAL_FILE: "Original File",
        fields.FIELD_ORIGINAL_FORMAT: "Original Format",
        fields.FIELD_ORIGINAL_NAME: "Original Name",
        fields.FIELD_ORIGINAL_PUID: "Original PUID",
        fields.FIELD_ORIGINAL_UUID: "Original UUID",
        fields.FIELD_ORIGINAL_VERSION: "Original Version",
        fields.FIELD_PUID: "PUID",
        fields.FIELD_RELATED_PAIRING: "Related Pairing",
        fields.FIELD_SIZE: "Size",
        fields.FIELD_STORAGE_LOCATION: "Location",
        fields.FIELD_STORAGE_NAME: "Storage Service Name",
        fields.FIELD_TRANSFER_NAME: "Transfer Name",
        fields.FIELD_USER: "User",
        fields.FIELD_VERSION: "Version",
    }

    # Attempt to add an additional header representing a column containing size
    # expressed as a number of bytes, rather than in human-readable form, so
    # rows can more easily be sorted by size
    if add_bytes_column:
        headers = (
            headers.copy()
        )  # So we don't change the list object passed to this function

        # Handle the two standard size columns
        for header in [fields.FIELD_AIP_SIZE, fields.FIELD_SIZE]:
            # If size header is found then insert another for the size in bytes afer it
            if header in headers:
                bytes_header = field_lookup[header] + " (bytes)"
                headers.insert(headers.index(header) + 1, bytes_header)

    return [field_lookup.get(header, header) for header in headers]


def _remove_primary_keys(dictionary):
    """Remove AIPscan primary keys from dictionary."""
    PK_FIELDS = (fields.FIELD_ID, fields.FIELD_AIP_ID)
    for field in PK_FIELDS:
        try:
            dictionary.pop(field, None)
        except AttributeError:
            pass


def format_size_for_csv(rows):
    """Return data prepared for CSV file.

    :param rows: Data assembled for tabular report (list of dicts)

    :returns: rows with formatted size field (list of dicts)
    """
    edited_rows = []

    for row in rows:
        # Add size in bytes after original size column
        row_key_list = list(row.keys())

        if fields.FIELD_SIZE in row_key_list:
            size_position = row_key_list.index(fields.FIELD_SIZE) + 1
            row_items = list(row.items())

            row_items.insert(
                size_position, (fields.FIELD_SIZE_BYTES, row[fields.FIELD_SIZE])
            )
            row = dict(row_items)

            # Format original size column
            row[fields.FIELD_SIZE] = filesizeformat(row[fields.FIELD_SIZE])

        edited_rows.append(row)

    return edited_rows


def download_csv(headers, rows, filename="report.csv"):
    """Write CSV from string and send it as an attachment.

    :param headers: Row headers (list of str)
    :param rows: Data to write to CSV, returned from Data endpoint (list of dicts)
    :param filename: CSV filename (str)
    """
    string_io = StringIO()
    writer = csv.writer(string_io)
    writer.writerow(headers)
    for row in rows:
        _remove_primary_keys(row)
        writer.writerow(row.values())
    response = make_response(string_io.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.mimetype = "text/csv"
    return response


def get_display_end_date(end_date):
    """Format end date to display.

    A day is added to end_date by parse_datetime_bound to facilitate date
    comparison in SQL queries. Here we remove that extra day before displaying
    the date in a report.

    :param end_date: End date (datetime.datetime object)

    :return: End date minus one day (datetime.datetime object)
    """
    return end_date - timedelta(days=1)


def calculate_paging_window(pagination):
    first_item = ((pagination.page - 1) * pagination.per_page) + 1
    last_item = pagination.page * pagination.per_page

    return first_item, min(last_item, pagination.total)


def remove_dict_none_values(values):
    return {index: "" if value is None else value for (index, value) in values.items()}
