# -*- coding: utf-8 -*-

"""Collects a number of reusable components of tasks.py. Also ensures
the module remains clean and easy to refactor over time.
"""
from datetime import datetime
import os

from dateutil.parser import parse, ParserError

from AIPscan.Aggregator.types import StorageServicePackage


def format_api_url_with_limit_offset(api_url):
    """Format the API URL here to make sure it is as correct as
    possible.
    """
    base_url = api_url.get("baseUrl", "").rstrip("/")
    limit = int(api_url.get("limit", ""))
    offset = api_url.get("offset", "")
    user_name = api_url.get("userName")
    api_key = api_url.get("apiKey", "")
    request_url_without_api_key = "{}/api/v2/file/?limit={}&offset={}".format(
        base_url, limit, offset
    )
    request_url = "{}&username={}&api_key={}".format(
        request_url_without_api_key, user_name, api_key
    )
    return base_url, request_url_without_api_key, request_url


def get_packages_directory(timestamp):
    """Create a path which we will use to store packages downloaded from
    the storage service plus other metadata.
    """
    return os.path.join("AIPscan", "Aggregator", "downloads", timestamp, "packages")


def process_package_object(package_obj):
    """Process a package object as retrieve from the storage service
    and return a StorageServicePackage type to the caller for further
    analysis.
    """
    package = StorageServicePackage()

    STATUS = "status"
    TYPE = "package_type"
    REPL = "replicated_package"
    CURRENT_PATH = "current_path"
    UUID = "uuid"

    PKG_AIP = "AIP"
    PKG_SIP = "transfer"
    PKG_DIP = "DIP"
    PKG_DEL = "DELETED"

    # Accumulate state. The package object should be able to evaluate
    # itself accordingly.
    if package_obj[TYPE] == PKG_AIP:
        package.aip = True
    if package_obj.get(TYPE) == PKG_DIP:
        package.dip = True
    if package_obj.get(TYPE) == PKG_SIP:
        package.sip = True
    if package_obj.get(STATUS) == PKG_DEL:
        package.deleted = True
    if package_obj.get(REPL) is not None:
        package.replica = True

    package.uuid = package_obj.get(UUID)
    package.current_path = package_obj.get(CURRENT_PATH)

    return package


def _tz_neutral_date(date):
    """Convert inconsistent dates consistently. Dates are round-tripped
    back to a Python datetime object as anticipated by the database.
    Where a date is unknown or can't be parsed, we return the UNIX EPOCH
    in lieu of another sensible value.
    """
    date_time_pattern = "%Y-%m-%dT%H:%M:%S"
    EPOCH = datetime.strptime("1970-01-01T00:00:01", date_time_pattern)
    try:
        date = parse(date)
        date = date.strftime(date_time_pattern)
        date = datetime.strptime(date, date_time_pattern)
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
        api_url[am_url].rstrip("/"),
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
