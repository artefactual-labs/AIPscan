from celery import Celery
import requests
from AIPscan import celery
import json
from datetime import datetime
import sqlite3
from celery.result import AsyncResult


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
def workflow_coordinator(self, apiUrl, timestampStr):

    # send package list request to a worker
    package_lists_task = package_lists_request.delay(apiUrl, timestampStr)

    """
    # Sending state updates back to Flask only works once, then the server needs
    # a restart for it to work again. The compromise is to write task ID to dbase

    self.update_state(meta={"package_lists_taskId": package_lists_task.id},)
    """

    db = sqlite3.connect("celerytasks.db")
    cursor = db.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS package_tasks(package_task_id TEXT PRIMARY KEY, workflow_coordinator_id TEXT)"
    )
    cursor.execute(
        "INSERT INTO package_tasks VALUES (?,?)",
        (package_lists_task.id, workflow_coordinator.request.id),
    )
    db.commit()

    # wait for package lists to download
    task = package_lists_request.AsyncResult(package_lists_task.id, app=celery)
    while True:
        if (task.state == "SUCCESS") or (task.state == "FAILURE"):
            break

    packagesDirectory = (
        "AIPscan/Aggregator/downloads/"
        + package_lists_task.info["timestampStr"]
        + "/packages/packages"
    )
    packagesCount = package_lists_task.info["packageCount"]
    totalDeletedAIPs = 0

    for packageListNo in range(1, packagesCount):
        with open(packagesDirectory + str(packageListNo) + ".json", "r") as packageList:
            list = packageList.read()
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
                    # build relative path to METS file
                    if package["current_path"].endswith(".7z"):
                        relative_path = package["current_path"][40:-3]
                    else:
                        relative_path = package["current_path"][40:]
                relative_path_to_mets = (
                    relative_path + "/data/METS." + package["uuid"] + ".xml"
                )

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
    return {"packageCount": packagesCount, "timestampStr": timestampStr}


@celery.task()
def get_mets(ssPackages, apiUrl, timestampStr, totalAIPs, totalDeletedAIPs):
    """
    request METS files from Archivematica AIP packages
    """
