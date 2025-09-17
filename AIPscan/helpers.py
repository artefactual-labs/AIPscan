import hashlib
from datetime import datetime
from datetime import timedelta


def parse_bool(value, default=True):
    if value is not None:
        value = value.lower()

        if value in ("y", "yes", "on", "1", "true", "t"):
            return True

    return False


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


def filesizeformat(value, binary=False):
    """Format the value like a 'human-readable' file size (i.e. 13 kB,
    4.1 MB, 102 Bytes, etc).  Per default decimal prefixes are used (Mega,
    Giga, etc.), if the second parameter is set to `True` the binary
    prefixes are used (Mebi, Gibi).

    Copied from jinja2 source code to ensure consistency of human-readable
    dates regardless of whether conversion happens in a view or a template.
    Source code: https://github.com/pallets/jinja/blob/
    9d4689b04d53f233b8b9ab664edb2f7430d2bbde/src/jinja2/filters.py

    Copyright 2007 Pallets
    BSD 3 license
    """
    byte_size = float(value)
    base = 1024 if binary else 1000
    prefixes = [
        ("KiB" if binary else "kB"),
        ("MiB" if binary else "MB"),
        ("GiB" if binary else "GB"),
        ("TiB" if binary else "TB"),
        ("PiB" if binary else "PB"),
        ("EiB" if binary else "EB"),
        ("ZiB" if binary else "ZB"),
        ("YiB" if binary else "YB"),
    ]

    if byte_size == 1:
        return "1 Byte"
    elif byte_size < base:
        return f"{int(byte_size)} Bytes"
    else:
        for i, prefix in enumerate(prefixes):
            unit = base ** (i + 2)

            if byte_size < unit:
                return f"{base * byte_size / unit:.1f} {prefix}"

        return f"{base * byte_size / unit:.1f} {prefix}"


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


def file_sha256_hash(filepath):
    """Return SHA256 hash for contents of file."""
    with open(filepath, "rb") as f:
        expected_bytes = f.read()
        return hashlib.sha256(expected_bytes).hexdigest()
