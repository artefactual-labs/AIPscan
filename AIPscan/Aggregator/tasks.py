# -*- coding: utf-8 -*-

from celery import Celery

from celery.result import AsyncResult

from AIPscan import celery
import os
import requests
import json
from datetime import datetime
import lxml
import metsrw
import xml.etree.ElementTree as ET
from AIPscan import db
from AIPscan.models import (
    fetch_jobs,
    aips,
    originals,
    copies,
    events,
    agents,
    event_agents,
    # Custom celery Models.
    package_tasks,
    get_mets_tasks,
)

from AIPscan.Aggregator.task_helpers import (
    get_mets_url,
)

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
    """
    request METS XML file from Archivematica AIP package and parse it
    """

    # request METS file
    mets_response = requests.get(get_mets_url(apiUrl, packageUUID, relativePathToMETS))

    # save METS files to disk
    # create package list numbered subdirectory if it doesn't exist
    if not os.path.exists(
        "AIPscan/Aggregator/downloads/" + timestampStr + "/mets/" + str(packageListNo)
    ):
        os.makedirs(
            "AIPscan/Aggregator/downloads/"
            + timestampStr
            + "/mets/"
            + str(packageListNo)
        )

    downloadFile = (
        "AIPscan/Aggregator/downloads/"
        + timestampStr
        + "/mets/"
        + str(packageListNo)
        + "/METS."
        + packageUUID
        + ".xml"
    )
    # cache a local copy of the METS file
    with open(downloadFile, "wb") as file:
        file.write(mets_response.content)

    # Load and Parse the METS. Because this function parses the whole
    # METS into memory it has  the potential to fail, so we need to
    # catch certain failures.
    #
    # NB. Any failures at this point are critical and so let's hope that
    # the source data is good.
    try:
        mets = metsrw.METSDocument.fromfile(downloadFile)
    except AttributeError as err:
        # We have an attribute error associated with archivematica/issues#1129.
        #
        # https://github.com/archivematica/Issues/issues/1129
        #
        # PICTURAE TODO: We need a pretty log output.
        #
        err = "{}: {}".format(err, downloadFile)
        print(err)
        return
    except lxml.etree.Error as err:
        # We have another undetermined storage service error, e.g. the
        # package no longer exists. We might also want to check the
        # response code in this instance. I didn't grab the exact error
        # code, so to recreate, delete an AIP on the server and don't
        # tell the storage service about it. Then try to download it.
        err = "{}: {}".format(err, downloadFile)
        print(err)
        return

    # metsrw library does not give access to original Transfer Name
    # which is often more useful to end-users than the AIP uuid
    # so we'll take the extra processing hit here to retrieve it
    metsTree = ET.parse(downloadFile)
    dmdSec1 = metsTree.find("{http://www.loc.gov/METS/}dmdSec[@ID='dmdSec_1']")
    for element in dmdSec1.getiterator():
        if element.tag == "{http://www.loc.gov/premis/v3}originalName":
            originalName = element.text[:-37]
            break

    # add AIP record to database
    aip = aips(
        packageUUID,
        transfer_name=originalName,
        create_date=datetime.strptime(mets.createdate, "%Y-%m-%dT%H:%M:%S"),
        originals_count=None,
        copies_count=None,
        storage_service_id=storageServiceId,
        fetch_job_id=fetchJobId,
    )
    db.session.add(aip)
    db.session.commit()

    for aipFile in mets.all_files():
        if (aipFile.use == "original") or (aipFile.use == "preservation"):
            name = aipFile.label
            uuid = aipFile.file_uuid
            size = None
            puid = None
            formatVersion = None
            relatedUuid = None

            # TODO: Fix-up mets-reader-writer:
            # https://github.com/archivematica/Issues/issues/1277
            try:
                for premis_object in aipFile.get_premis_objects():
                    size = premis_object.size
                    if (
                        str(premis_object.format_registry_key)
                    ) != "(('format_registry_key',),)":
                        if (str(premis_object.format_registry_key)) != "()":
                            puid = premis_object.format_registry_key
                    format = premis_object.format_name
                    if (str(premis_object.format_version)) != "(('format_version',),)":
                        if (str(premis_object.format_version)) != "()":
                            formatVersion = premis_object.format_version
                    checksumType = premis_object.message_digest_algorithm
                    checksumValue = premis_object.message_digest
                    if str(premis_object.related_object_identifier_value) != "()":
                        relatedUuid = premis_object.related_object_identifier_value

            except:
                format = "ISO Disk Image File"
                puid = "fmt/468"
                pass

            if aipFile.use == "original":
                file = originals(
                    name=name,
                    uuid=uuid,
                    size=size,
                    puid=puid,
                    format=format,
                    format_version=formatVersion,
                    checksum_type=checksumType,
                    checksum_value=checksumValue,
                    related_uuid=relatedUuid,
                    aip_id=aip.id,
                )
                db.session.add(file)
                db.session.commit()

                for premis_event in aipFile.get_premis_events():
                    type = premis_event.event_type
                    uuid = premis_event.event_identifier_value
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
                    originalId = file.id

                    event = events(
                        type=type,
                        uuid=uuid,
                        date=date,
                        detail=detail,
                        outcome=outcome,
                        outcome_detail=outcomeDetail,
                        original_id=originalId,
                    )

                    db.session.add(event)
                    db.session.commit()

                """
                for linking_agent in premis_event.linking_agent_identifier:
                print("Agent: " + linking_agent.linking_agent_identifier_value
                + " (" + linking_agent.linking_agent_identifier_type + ")")
                """

            if aipFile.use == "preservation":
                for premis_event in aipFile.get_premis_events():
                    if (premis_event.event_type) == "creation":
                        eventDate = (premis_event.event_date_time)[0:19]
                        normalizationDate = datetime.strptime(
                            eventDate, "%Y-%m-%dT%H:%M:%S"
                        )
                        eventDate = _tz_neutral_date(premis_event.event_date_time)
                file = copies(
                    name=name,
                    uuid=uuid,
                    size=size,
                    format=format,
                    checksum_type=checksumType,
                    checksum_value=checksumValue,
                    related_uuid=relatedUuid,
                    normalization_date=eventDate,
                    aip_id=aip.id,
                )
                db.session.add(file)
                db.session.commit()

            get_mets.update_state(state="IN PROGRESS")

    aip.originals_count = originals.query.filter_by(aip_id=aip.id).count()
    aip.copies_count = copies.query.filter_by(aip_id=aip.id).count()
    db.session.commit()

    return
