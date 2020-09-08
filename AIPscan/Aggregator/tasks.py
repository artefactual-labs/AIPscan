# -*- coding: utf-8 -*-

from datetime import datetime
import json
import requests

from celery.utils.log import get_task_logger

from AIPscan import celery
from AIPscan import db
from AIPscan.models import (
    fetch_jobs,
    aips,
    originals,
    copies,
    events,
    # Custom celery Models.
    package_tasks,
    get_mets_tasks,
)

from AIPscan.Aggregator.task_helpers import (
    create_numbered_subdirs,
    download_mets,
    get_mets_url,
    _tz_neutral_date,
)

from AIPscan.Aggregator.mets_parse_helpers import (
    METSError,
    get_aip_original_name,
    parse_mets_with_metsrw,
)


logger = get_task_logger(__name__)


def write_packages_json(count, timestampStr, packages):
    with open(
        "AIPscan/Aggregator/downloads/"
        + timestampStr
        + "/packages/packages"
        + str(count)
        + ".json",
        "w",
    ) as json_file:
        json.dump(packages, json_file, indent=4)
    return


@celery.task(bind=True)
def workflow_coordinator(self, apiUrl, timestampStr, storageServiceId, fetchJobId):

    # send package list request to a worker
    package_lists_task = package_lists_request.delay(apiUrl, timestampStr)

    """
    # Sending state updates back to Flask only works once, then the server needs
    # a restart for it to work again. The compromise is to write task ID to dbase

    self.update_state(meta={"package_lists_taskId": package_lists_task.id},)
    """

    package_task = package_tasks(
        package_task_id=package_lists_task.id,
        workflow_coordinator_id=workflow_coordinator.request.id,
    )
    db.session.add(package_task)
    db.session.commit()

    # wait for package lists task to finish downloading all package lists
    task = package_lists_request.AsyncResult(package_lists_task.id, app=celery)
    while True:
        if (task.state == "SUCCESS") or (task.state == "FAILURE"):
            break

    packagesDirectory = (
        "AIPscan/Aggregator/downloads/"
        + package_lists_task.info["timestampStr"]
        + "/packages/packages"
    )
    totalPackageLists = package_lists_task.info["totalPackageLists"]
    totalPackages = package_lists_task.info["totalPackages"]

    totalDeletedAIPs = 0
    totalAIPs = 0

    # get relative paths to METS file in the AIPs
    # create a new worker to download and parse each one separately
    # to take advantage of asynchronous tasks. The bottleneck will be SS api
    # response to multiple METS requests so get the same worker to do parsing
    # rather than synchronously download all METS first and then do parsing.
    for packageListNo in range(1, totalPackageLists + 1):
        with open(
            packagesDirectory + str(packageListNo) + ".json", "r"
        ) as packagesJson:
            list = json.load(packagesJson)
            for package in list["objects"]:
                # count number of deleted AIPs
                if package["status"] == "DELETED":
                    totalDeletedAIPs += 1

                # only scan AIP packages, ignore replicated and deleted packages
                if (
                    package["package_type"] == "AIP"
                    and package["replicated_package"] is None
                    and package["status"] != "DELETED"
                ):
                    totalAIPs += 1
                    packageUUID = package["uuid"]

                    # build relative path to METS file
                    if package["current_path"].endswith(".7z"):
                        relativePath = package["current_path"][40:-3]
                    else:
                        relativePath = package["current_path"][40:]
                    relativePathToMETS = (
                        relativePath + "/data/METS." + package["uuid"] + ".xml"
                    )

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

    # PICTURAE TODO: Do we need a try catch here in case the value
    # returns None.
    obj = fetch_jobs.query.filter_by(id=fetchJobId).first()
    obj.total_packages = totalPackages
    obj.total_aips = totalAIPs
    obj.total_deleted_aips = totalDeletedAIPs
    db.session.commit()
    return


@celery.task(bind=True)
def package_lists_request(self, apiUrl, timestampStr):
    """
    make requests for package information to Archivematica Storage Service
    """

    packagesCount = 1
    dateTimeObjStart = datetime.now().replace(microsecond=0)

    # initial packages request
    firstPackages = requests.get(
        apiUrl["baseUrl"]
        + "/api/v2/file/"
        + "?limit="
        + apiUrl["limit"]
        + "&offset="
        + apiUrl["offset"]
        + "&username="
        + apiUrl["userName"]
        + "&api_key="
        + apiUrl["apiKey"]
    )

    packages = firstPackages.json()
    nextUrl = packages["meta"]["next"]
    # calculate how many package list files will be downloaded based on total
    # number of packages and the download limit
    totalPackages = int(packages["meta"]["total_count"])
    limit = int(apiUrl["limit"])
    totalPackageLists = int(totalPackages / limit) + (totalPackages % limit > 0)

    write_packages_json(packagesCount, timestampStr, packages)

    while nextUrl is not None:
        next = requests.get(apiUrl["baseUrl"] + nextUrl)
        nextPackages = next.json()
        packagesCount += 1
        write_packages_json(packagesCount, timestampStr, nextPackages)
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
        "timestampStr": timestampStr,
    }


def _download_mets(
    api_url, package_uuid, relative_path_to_mets, timestamp, package_list_no
):
    """Download METS from the storage service."""

    # Request the METS file.
    mets_response = requests.get(
        get_mets_url(api_url, package_uuid, relative_path_to_mets)
    )

    # Create a directory to download the METS to.
    numbered_subdir = create_numbered_subdirs(timestamp, package_list_no)

    # Output METS to a convenient location to later be parsed.
    download_file = download_mets(mets_response, package_uuid, numbered_subdir)

    return download_file


def _create_aip_object(
    package_uuid, transfer_name, create_date, storage_service_id, fetch_job_id
):
    """Create an AIP object and save it to the database."""
    aip = aips(
        package_uuid,
        transfer_name=transfer_name,
        create_date=datetime.strptime(create_date, "%Y-%m-%dT%H:%M:%S"),
        originals_count=None,
        copies_count=None,
        storage_service_id=storage_service_id,
        fetch_job_id=fetch_job_id,
    )
    db.session.add(aip)
    db.session.commit()
    return aip


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

    aip = _create_aip_object(
        package_uuid=packageUUID,
        transfer_name=originalName,
        create_date=mets.createdate,
        storage_service_id=storageServiceId,
        fetch_job_id=fetchJobId,
    )

    process_aip_data(aip, packageUUID, mets)


def _add_file_original(
    aip_id,
    aip_file,
    file_name,
    file_uuid,
    file_size,
    puid,
    file_format,
    format_version,
    checksum_type,
    checksum_value,
    related_uuid,
):
    """Add a new original file to the database."""
    file_obj = originals(
        aip_id=aip_id,
        name=file_name,
        uuid=file_uuid,
        size=file_size,
        puid=puid,
        format=file_format,
        format_version=format_version,
        checksum_type=checksum_type,
        checksum_value=checksum_value,
        related_uuid=related_uuid,
    )

    logger.info("Adding original %s %s", file_obj, aip_id)

    db.session.add(file_obj)
    db.session.commit()

    for premis_event in aip_file.get_premis_events():
        type = premis_event.event_type
        event_uuid = premis_event.event_identifier_value
        date = _tz_neutral_date(premis_event.event_date_time)
        if str(premis_event.event_detail) != "(('event_detail',),)":
            detail = premis_event.event_detail
        else:
            detail = None
        if str(premis_event.event_outcome) != "(('event_outcome',),)":
            outcome = premis_event.event_outcome
        else:
            outcome = None
        if (
            str(premis_event.event_outcome_detail_note)
            != "(('event_outcome_detail_note',),)"
        ):
            outcomeDetail = premis_event.event_outcome_detail_note
        else:
            outcomeDetail = None
        originalId = file_obj.id

        event = events(
            type=type,
            uuid=event_uuid,
            date=date,
            detail=detail,
            outcome=outcome,
            outcome_detail=outcomeDetail,
            original_id=originalId,
        )

        db.session.add(event)
        db.session.commit()


def _add_file_preservation(
    aip_id,
    aip_file,
    file_name,
    file_uuid,
    file_size,
    file_format,
    checksum_type,
    checksum_value,
    related_uuid,
):
    """Add a preservation copy of a file to the database."""
    event_date = None
    for premis_event in aip_file.get_premis_events():
        if (premis_event.event_type) == "creation":
            event_date = (premis_event.event_date_time)[0:19]
            normalizationDate = datetime.strptime(event_date, "%Y-%m-%dT%H:%M:%S")
            event_date = _tz_neutral_date(premis_event.event_date_time)

    file_obj = copies(
        aip_id=aip_id,
        name=file_name,
        uuid=file_uuid,
        size=file_size,
        format=file_format,
        checksum_type=checksum_type,
        checksum_value=checksum_value,
        related_uuid=related_uuid,
        normalization_date=event_date,
    )

    logger.info("Adding preservation %s", file_obj)

    db.session.add(file_obj)
    db.session.commit()


def process_aip_data(aip, aip_uuid, mets):
    """Process the METS for as much information about the AIP as we
    need for reporting.
    """

    ORIGINAL_OBJECT = "original"
    PRESERVATION_OBJECT = "preservation"

    for aip_file in mets.all_files():
        if aip_file.use != ORIGINAL_OBJECT and aip_file.use != PRESERVATION_OBJECT:
            # Move onto the next file quickly.
            continue

        get_mets.update_state(state="IN PROGRESS")

        file_uuid = aip_file.file_uuid
        file_name = aip_file.label
        file_size = None
        puid = None
        file_format = None
        format_version = None
        related_uuid = None
        checksum_type = None
        checksum_value = None

        try:
            for premis_object in aip_file.get_premis_objects():
                file_size = premis_object.size
                if (
                    str(premis_object.format_registry_key)
                ) != "(('format_registry_key',),)":
                    if (str(premis_object.format_registry_key)) != "()":
                        puid = premis_object.format_registry_key
                file_format = premis_object.format_name
                if (str(premis_object.format_version)) != "(('format_version',),)":
                    if (str(premis_object.format_version)) != "()":
                        format_version = premis_object.format_version
                checksum_type = premis_object.message_digest_algorithm
                checksum_value = premis_object.message_digest
                if str(premis_object.related_object_identifier_value) != "()":
                    related_uuid = premis_object.related_object_identifier_value

        except AttributeError:
            # File error/warning to log. Obviously this format may
            # be incorrect so it is our best guess.
            file_format = "ISO Disk Image File"
            puid = "fmt/468"

        if aip_file.use == ORIGINAL_OBJECT:

            _add_file_original(
                aip_id=aip.id,
                aip_file=aip_file,
                file_name=file_name,
                file_uuid=file_uuid,
                file_size=file_size,
                puid=puid,
                file_format=file_format,
                format_version=format_version,
                checksum_type=checksum_type,
                checksum_value=checksum_value,
                related_uuid=related_uuid,
            )

        if aip_file.use == PRESERVATION_OBJECT:
            _add_file_preservation(
                aip_id=aip.id,
                aip_file=aip_file,
                file_name=file_name,
                file_uuid=file_uuid,
                file_size=file_size,
                file_format=file_format,
                checksum_type=checksum_type,
                checksum_value=checksum_value,
                related_uuid=related_uuid,
            )

    aip.originals_count = originals.query.filter_by(aip_id=aip.id).count()
    aip.copies_count = copies.query.filter_by(aip_id=aip.id).count()
    db.session.commit()
