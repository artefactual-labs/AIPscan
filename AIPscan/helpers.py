# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from distutils.util import strtobool


def parse_bool(val, default=True):
    try:
        return bool(strtobool(val))
    except (ValueError, AttributeError):
        return default


def parse_datetime_bound(date_string, upper=False):
    """Parse date parameter string into datetime object.

    Date parameters come in from the UI or API as date strings. This
    helper converts these date strings to datetime objects for use in
    filtering by date range in Data endpoints.

    Date filtering in SQLAlchemy queries in the Data endpoint will be
    inclusive when the following rules are followed:
    - Use >= for start_date comparison
    - Use < for end_date comparison

    None or invalid start and end date values are set to datetime.min
    and datetime.max respectively.

    :param date_string: Date string. Valid format is YYYY-MM-DD (str).
    :param upper: Flag indicating if date string being parsed is
        the upper bound, with default of False (bool).

    :returns: datetime.datetime object
    """
    default_datetime = datetime.min
    if upper:
        default_datetime = datetime.max

    try:
        parsed_datetime = datetime.strptime(date_string, "%Y-%m-%d")
        if upper:
            parsed_datetime = parsed_datetime + timedelta(days=1)
        return parsed_datetime
    except (TypeError, ValueError):
        return default_datetime


def get_human_readable_file_size(size, precision=2):
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB"]
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1  # increment the index of the suffix
        size = size / 1024.0  # apply the division
    return "%.*f %s" % (precision, size, suffixes[suffixIndex])


def _split_ms(date_string):
    """Remove microseconds from the given date string."""
    return str(date_string).split(".")[0]


def _simplify_datetime(date_string, return_object=True):
    """Consistently return datetime string or object as required with
    microseconds striped.
    """
    DATE_FORMAT_FULL = "%Y-%m-%d %H:%M:%S"
    formatted_date = datetime.strptime(_split_ms(date_string), DATE_FORMAT_FULL)
    if return_object:
        return formatted_date
    return formatted_date.strftime(DATE_FORMAT_FULL)
