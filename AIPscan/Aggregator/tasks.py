from celery import Celery
from celery.result import AsyncResult
from AIPscan import celery
import os
import requests
import json
from datetime import datetime
import sqlite3
import metsrw
import xml.etree.ElementTree as ET
from AIPscan import db
from AIPscan.models import fetch_jobs, aips, files


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
def workflow_coordinator(self, apiUrl, timestampStr, fetchJobId):

    # send package list request to a worker
    package_lists_task = package_lists_request.delay(apiUrl, timestampStr)

    """
    # Sending state updates back to Flask only works once, then the server needs
    # a restart for it to work again. The compromise is to write task ID to dbase

    self.update_state(meta={"package_lists_taskId": package_lists_task.id},)
    """

    celerydb = sqlite3.connect("celerytasks.db")
    cursor = celerydb.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS package_tasks(package_task_id TEXT PRIMARY KEY, workflow_coordinator_id TEXT)"
    )
    cursor.execute(
        "INSERT INTO package_tasks VALUES (?,?)",
        (package_lists_task.id, workflow_coordinator.request.id),
    )
    celerydb.commit()

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
                        fetchJobId,
                    )

    # fix me to match time when last get_mets task finishes
    downloadEnd = datetime.now().replace(microsecond=0)

    """
    fetch_jobs.query.filter_by(id=fetchJobId).update(
        {
            "total_packages": packagesCount,
            "total_aips": totalAIPs,
            "total_deleted_aips": totalDeletedAIPs,
            "download_end": downloadEnd,
        }
    )

    # The SQLalchemy insert above is not working so the raw insert below is used
    """

    aipscandb = sqlite3.connect("aipscan.db")
    cursor = aipscandb.cursor()
    cursor.execute(
        "UPDATE fetch_jobs SET total_packages = ?, total_aips = ?, total_deleted_aips = ?, download_end = ?  WHERE id = ?",
        (totalPackages, totalAIPs, totalDeletedAIPs, downloadEnd, fetchJobId),
    )
    aipscandb.commit()

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
    packageUUID, relativePathToMETS, apiUrl, timestampStr, packageListNo, fetchJobId
):
    """
    request METS XML file from Archivematica AIP package and parse it
    """

    # request METS file
    mets_response = requests.get(
        apiUrl["baseUrl"]
        + "/api/v2/file/"
        + packageUUID
        + "/extract_file/?relative_path_to_file="
        + relativePathToMETS
        + "&username="
        + apiUrl["userName"]
        + "&api_key="
        + apiUrl["apiKey"]
    )

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
        + "/"
        + packageUUID
        + ".xml"
    )
    # cache a local copy of the METS file
    with open(downloadFile, "wb") as file:
        file.write(mets_response.content)

    mets = metsrw.METSDocument.fromfile(downloadFile)

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
        originals=None,
        preservation_copies=None,
        fetch_job_id=fetchJobId,
    )
    db.session.add(aip)
    db.session.commit()

    for aipFile in mets.all_files():
        originalsCount = 0
        preservationCopiesCount = 0
        if (aipFile.use == "original") or (aipFile.use == "preservation"):
            name = aipFile.label
            type = aipFile.use
            uuid = aipFile.file_uuid
            puid = None
            formatVersion = None
            relatedUuid = None
            creationDate = None
            ingestionDate = None
            normalizationDate = None

            # this exception handler had to be added because for .iso file types METSRW throws
            # the error: "metsrw/plugins/premisrw/premis.py", line 644, in _to_colon_ns
            # parts = [x.strip("{") for x in bracket_ns.split("}")]"
            # AttributeError: 'cython_function_or_method' object has no attribute 'split'
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
                    if str(premis_object.related_object_identifier_value) != "()":
                        relatedUuid = premis_object.related_object_identifier_value
                    if aipFile.use == "original":
                        eventDate = str(premis_object.date_created_by_application)
                        creationDate = datetime.strptime(eventDate, "%Y-%m-%d")
                        originalsCount += 1
                    else:
                        preservationCopiesCount += 1
            except:
                format = "ISO Disk Image File"
                puid = "fmt/468"
                originalsCount += 1
                pass

            for premis_event in aipFile.get_premis_events():
                if (premis_event.event_type) == "ingestion":
                    eventDate = (premis_event.event_date_time)[:-13]
                    ingestionDate = datetime.strptime(eventDate, "%Y-%m-%dT%H:%M:%S")
                if (premis_event.event_type) == "creation":
                    eventDate = (premis_event.event_date_time)[:-13]
                    normalizationDate = datetime.strptime(
                        eventDate, "%Y-%m-%dT%H:%M:%S"
                    )
            file = files(
                name=name,
                type=type,
                uuid=uuid,
                size=size,
                puid=puid,
                format=format,
                format_version=formatVersion,
                related_uuid=relatedUuid,
                creation_date=creationDate,
                ingestion_date=ingestionDate,
                normalization_date=normalizationDate,
                aip_id=aip.id,
            )
            db.session.add(file)
            db.session.commit()

        aips.query.filter_by(id=aip.id).update(
            {
                "originals": originalsCount,
                "preservation_copies": preservationCopiesCount,
            }
        )

    return
