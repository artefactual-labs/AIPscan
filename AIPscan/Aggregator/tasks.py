# -*- coding: utf-8 -*-
import json
import os

import requests
from celery.utils.log import get_task_logger

from AIPscan import db
from AIPscan.Aggregator import database_helpers
from AIPscan.Aggregator.celery_helpers import write_celery_update
from AIPscan.Aggregator.mets_parse_helpers import (
    METSError,
    download_mets,
    get_aip_original_name,
    parse_mets_with_metsrw,
)
from AIPscan.Aggregator.task_helpers import (
    format_api_url_with_limit_offset,
    get_location_url,
    process_package_object,
)
from AIPscan.extensions import celery
from AIPscan.helpers import file_sha256_hash
from AIPscan.models import (  # Custom celery Models.
    AIP,
    FetchJob,
    StorageLocation,
    get_mets_tasks,
)

logger = get_task_logger(__name__)


class TaskError(Exception):
    """Exception to call when there is a problem downloading from the
    storage service. The exception is known and asks for user
    intervention.
    """


def _get_storage_location(current_location):
    """Return first StorageLocation."""
    return StorageLocation.query.filter_by(current_location=current_location).first()


def write_packages_json(count, packages, packages_directory):
    """Write package JSON to disk"""
    json_download_file = os.path.join(
        packages_directory, "packages{}.json".format(count)
    )
    logger.info("Packages file is downloaded to '%s'", json_download_file)
    try:
        with open(json_download_file, "w") as json_file:
            json.dump(packages, json_file, indent=4)
    except json.JSONDecodeError:
        logger.error("Cannot decode JSON from %s", json_download_file)


def start_mets_task(
    package_uuid,
    relative_path_to_mets,
    current_location,
    api_url,
    timestamp_str,
    package_list_no,
    storage_service_id,
    fetch_job_id,
):
    """Initiate a get_mets task worker and record the event in the
    celery database.
    """
    # Add Storage Location if it doesn't already exist.
    storage_location = StorageLocation.query.filter_by(
        current_location=current_location
    ).first()
    if not storage_location:
        request_url, request_url_without_api_key = get_location_url(
            api_url, current_location
        )
        response = make_request(request_url, request_url_without_api_key)
        description = response.get("description")
        storage_location = database_helpers.create_storage_location_object(
            current_location, description, storage_service_id
        )

    # Call worker to download and parse METS File.
    get_mets_task = get_mets.delay(
        package_uuid,
        relative_path_to_mets,
        current_location,
        api_url,
        timestamp_str,
        package_list_no,
        storage_service_id,
        storage_location.id,
        fetch_job_id,
    )
    mets_task = get_mets_tasks(
        get_mets_task_id=get_mets_task.id,
        workflow_coordinator_id=workflow_coordinator.request.id,
        package_uuid=package_uuid,
        status=None,
    )
    db.session.add(mets_task)
    db.session.commit()


def parse_packages_and_load_mets(
    json_file_path,
    api_url,
    timestamp,
    package_list_no,
    storage_service_id,
    fetch_job_id,
):
    """Parse packages documents from the storage service and initiate
    the load mets functions of AIPscan. Results are written to the
    database.
    """
    OBJECTS = "objects"
    packages = []
    with open(json_file_path, "r") as packagesJson:
        package_list = json.load(packagesJson)
    for package_obj in package_list.get(OBJECTS, []):
        package = process_package_object(package_obj)
        packages.append(package)
        if not package.is_aip():
            continue
        start_mets_task(
            package.uuid,
            package.get_relative_path(),
            package.current_location,
            api_url,
            timestamp,
            package_list_no,
            storage_service_id,
            fetch_job_id,
        )
    return packages


@celery.task(bind=True)
def workflow_coordinator(
    self, api_url, timestamp, storage_service_id, fetch_job_id, packages_directory
):

    logger.info("Packages directory is: %s", packages_directory)

    # Send package list request to a worker.
    package_lists_task = package_lists_request.delay(
        api_url, timestamp, packages_directory
    )

    write_celery_update(package_lists_task, workflow_coordinator)

    # Wait for package lists task to finish downloading all package
    # lists.
    task = package_lists_request.AsyncResult(package_lists_task.id, app=celery)
    while True:
        if (task.state == "SUCCESS") or (task.state == "FAILURE"):
            break

    if isinstance(package_lists_task.info, TaskError):
        # Re-raise.
        raise (package_lists_task.info)

    total_package_lists = package_lists_task.info["totalPackageLists"]

    all_packages = []
    for package_list_no in range(1, total_package_lists + 1):
        json_file_path = os.path.join(
            packages_directory, "packages{}.json".format(package_list_no)
        )
        # Process packages and create a new worker to download and parse
        # each METS separately.
        packages = parse_packages_and_load_mets(
            json_file_path,
            api_url,
            timestamp,
            package_list_no,
            storage_service_id,
            fetch_job_id,
        )
        all_packages = all_packages + packages

    total_packages = package_lists_task.info["totalPackages"]

    total_aips = len([package for package in all_packages if package.is_aip()])
    total_sips = len([package for package in all_packages if package.is_sip()])
    total_dips = len([package for package in all_packages if package.is_dip()])
    total_deleted_aips = len(
        [package for package in all_packages if package.is_deleted()]
    )
    total_replicas = len([package for package in all_packages if package.is_replica()])

    summary = "aips: '{}'; sips: '{}'; dips: '{}'; deleted: '{}'; replicated: '{}'".format(
        total_aips, total_sips, total_dips, total_deleted_aips, total_replicas
    )
    logger.info("%s", summary)

    obj = FetchJob.query.filter_by(id=fetch_job_id).first()
    obj.total_packages = total_packages
    obj.total_aips = total_aips
    obj.total_dips = total_dips
    obj.total_sips = total_sips
    obj.total_replicas = total_replicas
    obj.total_deleted_aips = total_deleted_aips
    db.session.commit()


def make_request(request_url, request_url_without_api_key):
    """Make our request to the storage service and return a valid
    response to our caller or raise a TaskError for celery.
    """
    response = requests.get(request_url)
    if response.status_code != requests.codes.ok:
        err = "Check the URL and API details, cannot connect to: `{}`".format(
            request_url_without_api_key
        )
        logger.error(err)
        raise TaskError("Bad response from server: {}".format(err))
    try:
        packages = response.json()
    except json.JSONDecodeError:
        err = "Response is OK, but cannot decode JSON from server"
        logger.error(err)
        raise TaskError(err)
    return packages


@celery.task(bind=True)
def package_lists_request(self, apiUrl, timestamp, packages_directory):
    """Request package lists from the storage service. Package lists
    will contain details of the AIPs that we want to download.
    """
    META = "meta"
    NEXT = "next"
    LIMIT = "limit"
    COUNT = "total_count"
    IN_PROGRESS = "IN PROGRESS"
    (
        base_url,
        request_url_without_api_key,
        request_url,
    ) = format_api_url_with_limit_offset(apiUrl)
    # First packages request.
    packages = make_request(request_url, request_url_without_api_key)
    packages_count = 1
    # Calculate how many package list files will be downloaded based on
    # total number of packages and the download limit
    total_packages = int(packages.get(META, {}).get(COUNT, 0))
    total_package_lists = int(total_packages / int(apiUrl.get(LIMIT))) + (
        total_packages % int(apiUrl.get(LIMIT)) > 0
    )
    # There may be more packages to download to let's access those here.
    # TODO: `request_url_without_api_key` at this point will not be as
    # accurate. If we have more time, modify `format_api_url_with_limit_offset(...)`
    # to work with raw offset and limit data to make up for the fact
    # that an API key is plain-encoded in next_url.
    next_url = packages.get(META, {}).get(NEXT, None)
    write_packages_json(packages_count, packages, packages_directory)
    while next_url is not None:
        next_request = "{}{}".format(base_url, next_url)
        next_packages = make_request(next_request, request_url_without_api_key)
        packages_count += 1
        write_packages_json(packages_count, next_packages, packages_directory)
        next_url = next_packages.get(META, {}).get(NEXT, None)
        self.update_state(
            state=IN_PROGRESS,
            meta={
                "message": "Total packages: {} Total package lists: {}".format(
                    total_packages, total_package_lists
                )
            },
        )
    return {
        "totalPackageLists": total_package_lists,
        "totalPackages": total_packages,
        "timestampStr": timestamp,
    }


@celery.task()
def get_mets(
    package_uuid,
    relative_path_to_mets,
    current_location,
    api_url,
    timestamp_str,
    package_list_no,
    storage_service_id,
    storage_location_id,
    fetch_job_id,
):
    """Request METS XML file from the storage service and parse.

    Download a METS file from an AIP that is stored in the storage
    service and then parse the results into the AIPscan database.

    This function relies on being able to use mets-reader-writer which
    is the primary object we will be passing about.

    TODO: Log METS errors.
    """
    download_file = download_mets(
        api_url, package_uuid, relative_path_to_mets, timestamp_str, package_list_no
    )
    mets_name = os.path.basename(download_file)
    mets_hash = file_sha256_hash(download_file)

    # If METS file's hash matches an existing value, this is a duplicate of an
    # existing AIP and we can safely ignore it.
    matching_aip = AIP.query.filter_by(mets_sha256=mets_hash).first()
    if matching_aip is not None:
        logger.info(
            "Skipping METS file {} - identical to existing record".format(mets_name)
        )
        return

    logger.info("Processing METS file {}".format(mets_name))

    try:
        mets = parse_mets_with_metsrw(download_file)
    except METSError:
        # An error we need to log and report back to the user.
        return

    try:
        original_name = get_aip_original_name(mets)
    except METSError:
        # Some other error with the METS file that we might want to
        # log and act upon.
        original_name = package_uuid

    # Delete records of any previous versions of this AIP, which will shortly
    # be replaced by new records from the updated METS.
    previous_aips = AIP.query.filter_by(uuid=package_uuid).all()
    for previous_aip in previous_aips:
        logger.info(
            "Deleting record for AIP {} to replace from newer METS".format(package_uuid)
        )
        database_helpers.delete_aip_object(previous_aip)

    aip = database_helpers.create_aip_object(
        package_uuid=package_uuid,
        transfer_name=original_name,
        create_date=mets.createdate,
        mets_sha256=mets_hash,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job_id,
    )

    database_helpers.process_aip_data(aip, mets)
