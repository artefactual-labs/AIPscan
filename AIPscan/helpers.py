# -*- coding: utf-8 -*-

from datetime import datetime

from distutils.util import strtobool


def parse_bool(val, default=True):
    try:
        return bool(strtobool(val))
    except (ValueError, AttributeError):
        return default


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
