# -*- coding: utf-8 -*-

"""Collects a number of reusable components of tasks.py. Also ensures
the module remains clean and easy to refactor over time.
"""
from datetime import datetime
import os

from dateutil.parser import parse, ParserError


def _tz_neutral_date(date):
    """Convert inconsistent dates consistently. Dates are round-tripped
    back to a Python datetime object as anticipated by the database.
    Where a date is unknown or can't be parsed, we return the UNIX EPOCH
    in lieu of another sensible value.
    """
    EPOCH = datetime.strptime("1970-01-01T00:00:01", "%Y-%m-%dT%H:%M:%S")
    try:
        date = parse(date)
        date = date.strftime("%Y-%m-%dT%H:%M:%S")
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    except ParserError:
        date = EPOCH
    return date


def get_mets_url(api_url, package_uuid, path_to_mets):
    """Construct a URL from which we can download the METS files that
    we are interested in.
    """
    am_url = "baseUrl"
    user_name = "userName"
    api_key = "apiKey"

    mets_url = "{}/api/v2/file/{}/extract_file/?relative_path_to_file={}&username={}&api_key={}".format(
        api_url[am_url],
        package_uuid,
        path_to_mets,
        api_url[user_name],
        api_url[api_key],
    )
    return mets_url


def create_numbered_subdirs(timestamp, package_list_number):
    """Check for the existence and create a container folder for our
    METS files as required.
    """
    AGGREGATOR_DOWNLOADS = os.path.join("AIPscan", "Aggregator", "downloads")
    METS_FOLDER = "mets"

    # Create a package list numbered subdirectory if it doesn't exist.
    numbered_subdir = os.path.join(
        AGGREGATOR_DOWNLOADS, timestamp, METS_FOLDER, str(package_list_number)
    )
    if not os.path.exists(numbered_subdir):
        os.makedirs(numbered_subdir)

    return numbered_subdir


def download_mets(http_response, package_uuid, subdir):
    """Given a http response containing our METS data, create the path
    we want to store our METS at, and then stream the response into a
    file.
    """
    mets_file = "METS.{}.xml".format(package_uuid)
    download_file = os.path.join(subdir, mets_file)
    with open(download_file, "wb") as file:
        file.write(http_response.content)
    return download_file
