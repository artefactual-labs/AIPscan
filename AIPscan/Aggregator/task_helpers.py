"""Collects a number of reusable components of tasks.py. Also ensures
the module remains clean and easy to refactor over time.
"""

import json
import os
from datetime import datetime

from dateutil.parser import ParserError
from dateutil.parser import parse

from AIPscan.Aggregator.types import StorageServicePackage


def format_api_url_with_limit_offset(storage_service):
    """Format the API URL here to make sure it is as correct as
    possible.
    """
    base_url = storage_service.url.rstrip("/")

    request_url_without_api_key = f"{base_url}/api/v2/file/?limit={storage_service.download_limit}&offset={storage_service.download_offset}"
    request_url = f"{request_url_without_api_key}&username={storage_service.user_name}&api_key={storage_service.api_key}"
    return base_url, request_url_without_api_key, request_url


def get_packages_directory(timestamp):
    """Create a path which we will use to store packages downloaded from
    the storage service plus other metadata.
    """
    return os.path.join("AIPscan", "Aggregator", "downloads", timestamp, "packages")


def parse_package_list_file(filepath, logger=None, remove_after_parsing=False):
    with open(filepath) as packages_json:
        package_list = json.load(packages_json)
    try:
        if remove_after_parsing:
            os.remove(filepath)
    except OSError as err:
        if logger:
            logger.warning(f"Unable to delete package JSON file: {err}")

    return package_list


def process_package_object(package_obj):
    """Process a package object as retrieve from the storage service
    and return a StorageServicePackage type to the caller for further
    analysis.
    """
    package = StorageServicePackage()

    STATUS = "status"
    TYPE = "package_type"
    REPL = "replicated_package"
    CURRENT_LOCATION = "current_location"
    CURRENT_PATH = "current_path"
    ORIGIN_PIPELINE = "origin_pipeline"
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
    package.current_location = package_obj.get(CURRENT_LOCATION)
    package.current_path = package_obj.get(CURRENT_PATH)
    package.origin_pipeline = package_obj.get(ORIGIN_PIPELINE)
    package.size = package_obj.get("size")

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


def get_mets_url(storage_service, package_uuid, path_to_mets):
    """Construct a URL from which we can download the METS files that
    we are interested in.
    """
    mets_url = "{}/api/v2/file/{}/extract_file/?relative_path_to_file={}&username={}&api_key={}".format(
        storage_service.url.rstrip("/"),
        package_uuid,
        path_to_mets,
        storage_service.user_name,
        storage_service.api_key,
    )
    return mets_url


def get_storage_service_api_url(storage_service, api_path):
    """Return URL to fetch location infofrom Storage Service."""
    base_url = storage_service.url.rstrip("/")
    request_url_without_api_key = f"{base_url}{api_path}".rstrip("/")

    request_url = f"{request_url_without_api_key}?username={storage_service.user_name}&api_key={storage_service.api_key}"
    return request_url, request_url_without_api_key


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


def summarize_fetch_job_results(fetch_job):
    return f"aips: '{fetch_job.total_aips}'; sips: '{fetch_job.total_sips}'; dips: '{fetch_job.total_dips}'; deleted: '{fetch_job.total_deleted_aips}'; replicated: '{fetch_job.total_replicas}'"
