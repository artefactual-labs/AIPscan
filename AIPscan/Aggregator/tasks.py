from celery import Celery
import requests
from AIPscan import celery
import json
from datetime import datetime


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
def storage_service_request(self, apiUrl, timestampStr):
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
    write_packages_json(packagesCount, timestampStr, packages)
    self.update_state(
        state="STARTED DOWNLOADING PACKAGE LISTS",
        meta={
            "started": dateTimeObjStart,
            "total packages": packages["meta"]["total_count"],
        },
    )

    while nextUrl is not None:
        next = requests.get(apiUrl["baseUrl"] + nextUrl)
        nextPackages = next.json()
        packagesCount += 1
        write_packages_json(packagesCount, timestampStr, nextPackages)
        nextUrl = nextPackages["meta"]["next"]

        self.update_state(
            state="IN PROGRESS", meta={"current package list": packagesCount}
        )


@celery.task()
def get_mets(ssPackages, apiUrl, timestampStr, totalAIPs, totalDeletedAIPs):
    """
    request METS files from Archivematica AIP packages
    """
