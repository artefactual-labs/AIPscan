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


def _retrieve_uuid_and_path_from_package_object(package_obj):
    """Given a JSON dictionary describing a package in the storage
    service parse out the details into something that can be added to
    the database and then acted upon by AIPscan.
    """
    packageUUID = package_obj["uuid"]

    # build relative path to METS file
    if package_obj["current_path"].endswith(".7z"):
        relativePath = package_obj["current_path"][40:-3]
    else:
        relativePath = package_obj["current_path"][40:]
    relativePathToMETS = relativePath + "/data/METS." + package_obj["uuid"] + ".xml"

    return packageUUID, relativePathToMETS


def parse_packages_and_load_mets(
    json_file_path, apiUrl, timestampStr, packageListNo, storageServiceId, fetchJobId
):
    """Parse packages documents from the storage service and initiate
    the load mets functions of AIPscan. Results are written to the
    database.
    """
    totalDeletedAIPs, total_dips, total_replicated, totalAIPs = 0, 0, 0, 0
    with open(json_file_path, "r") as packagesJson:
        package_list = json.load(packagesJson)
    for package_obj in package_list.get("objects", []):
        if package_obj["status"] == "DELETED":
            totalDeletedAIPs += 1
            continue
        if package_obj["package_type"] == "DIP":
            total_dips += 1
            continue
        if package_obj["replicated_package"] is not None:
            total_replicated += 1
        if (
            package_obj["package_type"] == "AIP"
            and package_obj["replicated_package"] is None
            and package_obj["status"] != "DELETED"
        ):
            totalAIPs += 1
            packageUUID, relativePathToMETS = _retrieve_uuid_and_path_from_package_object(
                package_obj
            )
            start_mets_task(
                packageUUID,
                relativePathToMETS,
                apiUrl,
                timestampStr,
                packageListNo,
                storageServiceId,
                fetchJobId,
            )
    return totalDeletedAIPs, total_dips, total_replicated, totalAIPs


@celery.task(bind=True)
def workflow_coordinator(
    self, apiUrl, timestampStr, storageServiceId, fetchJobId, packages_directory
):

    logger.info("Packages directory is: %s", packages_directory)

    # send package list request to a worker
    package_lists_task = package_lists_request.delay(
        apiUrl, timestampStr, packages_directory
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

    totalPackageLists = package_lists_task.info["totalPackageLists"]
    totalPackages = package_lists_task.info["totalPackages"]

    totalDeletedAIPs = 0
    totalAIPs = 0

    # Create a new worker to download and parse each METS separately.
    for packageListNo in range(1, totalPackageLists + 1):
        json_file_path = os.path.join(
            packages_directory, "packages{}.json".format(packageListNo)
        )
        parse_packages_and_load_mets(
            json_file_path,
            apiUrl,
            timestampStr,
            packageListNo,
            storageServiceId,
            fetchJobId,
        )

    # PICTURAE TODO: Do we need a try catch here in case the value
    # returns None.
    obj = fetch_jobs.query.filter_by(id=fetchJobId).first()
    obj.total_packages = totalPackages
    obj.total_aips = totalAIPs
    obj.total_deleted_aips = totalDeletedAIPs
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

    request_url_without_api_key = "{}/api/v2/file/?limit={}&offset={}".format(
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
