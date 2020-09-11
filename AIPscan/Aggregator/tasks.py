# -*- coding: utf-8 -*-

from datetime import datetime
import json
import os
import requests

from celery.utils.log import get_task_logger

from AIPscan import celery
from AIPscan import db
from AIPscan.models import (
    fetch_jobs,
    # Custom celery Models.
    get_mets_tasks,
)

from AIPscan.Aggregator.celery_helpers import write_celery_update
from AIPscan.Aggregator.database_helpers import create_aip_object, process_aip_data

from AIPscan.Aggregator.mets_parse_helpers import (
    _download_mets,
    METSError,
    get_aip_original_name,
    parse_mets_with_metsrw,
)

from AIPscan.Aggregator.task_helpers import (
    process_package_object,
    format_api_url_with_limit_offset,
)

logger = get_task_logger(__name__)


class TaskError(Exception):
    """Exception to call when there is a problem downloading from the
    storage service. The exception is known and asks for user
    intervention.
    """


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
    packageUUID,
    relativePathToMETS,
    apiUrl,
    timestampStr,
    packageListNo,
    storageServiceId,
    fetchJobId,
):
    """Initiate a get_mets task worker and record the event in the
    celery database.
    """
    # call worker to download and parse METS File
    get_mets_task = get_mets.delay(
        packageUUID,
        relativePathToMETS,
        apiUrl,
        timestampStr,
        packageListNo,
        storageServiceId,
        fetchJobId,
    )
    mets_task = get_mets_tasks(
        get_mets_task_id=get_mets_task.id,
        workflow_coordinator_id=workflow_coordinator.request.id,
        package_uuid=packageUUID,
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

    obj = fetch_jobs.query.filter_by(id=fetch_job_id).first()
    obj.total_packages = total_packages
    obj.total_aips = total_aips
    obj.total_dips = total_dips
    obj.total_sips = total_sips
    obj.total_replicas = total_replicas
    obj.total_deleted_aips = total_deleted_aips
    db.session.commit()


@celery.task(bind=True)
def package_lists_request(self, apiUrl, timestamp, packages_directory):
    """Request package lists from the storage service. Package lists
    will contain details of the AIPs that we want to download.
    """

    packagesCount = 1
    dateTimeObjStart = datetime.now().replace(microsecond=0)

    base_url = apiUrl.get("baseUrl", "")
    limit = apiUrl.get("limit", "")
    offset = apiUrl.get("offset", "")
    user_name = apiUrl.get("userName")
    api_key = apiUrl.get("apiKey", "")

    request_url_without_api_key = format_api_url_with_limit_offset(
        base_url, limit, offset
    )

    request_url = "{}&username={}&api_key={}".format(
        request_url_without_api_key, user_name, api_key
    )

    # initial packages request
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

    nextUrl = packages["meta"]["next"]
    # calculate how many package list files will be downloaded based on total
    # number of packages and the download limit
    totalPackages = int(packages["meta"]["total_count"])
    limit = int(apiUrl["limit"])
    totalPackageLists = int(totalPackages / limit) + (totalPackages % limit > 0)

    write_packages_json(packagesCount, packages, packages_directory)

    while nextUrl is not None:
        next = requests.get(apiUrl["baseUrl"] + nextUrl)
        nextPackages = next.json()
        packagesCount += 1
        write_packages_json(packagesCount, nextPackages, packages_directory)
        nextUrl = nextPackages["meta"]["next"]
        self.update_state(
            state="IN PROGRESS",
            meta={
                "message": "Total packages: "
                + str(totalPackages)
                + " Total package lists: "
                + str(totalPackageLists)
            },
        )
    return {
        "totalPackageLists": totalPackageLists,
        "totalPackages": totalPackages,
        "timestampStr": timestamp,
    }


@celery.task()
def get_mets(
    packageUUID,
    relativePathToMETS,
    apiUrl,
    timestampStr,
    packageListNo,
    storageServiceId,
    fetchJobId,
):
    """Request METS XML file from the storage service and parse.

    Download a METS file from an AIP that is stored in the storage
    service and then parse the results into the AIPscan database.

    This function relies on being able to use mets-reader-writer which
    is the primary object we will be passing about.

    TODO:
        * Make variable names snake_case.
        * Log METS errors.
    """

    download_file = _download_mets(
        apiUrl, packageUUID, relativePathToMETS, timestampStr, packageListNo
    )

    try:
        mets = parse_mets_with_metsrw(download_file)
    except METSError:
        # An error we need to log and report back to the user.
        return

    try:
        originalName = get_aip_original_name(mets)
    except METSError:
        # Some other error with the METS file that we might want to
        # log and act upon.
        originalName = ""

    aip = create_aip_object(
        package_uuid=packageUUID,
        transfer_name=originalName,
        create_date=mets.createdate,
        storage_service_id=storageServiceId,
        fetch_job_id=fetchJobId,
    )

    process_aip_data(aip, packageUUID, mets)
