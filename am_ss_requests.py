__author__ = "Peter Van Garderen"
__email__ = "peter@artefactual.com"

import requests
import os.path
from datetime import datetime

baseUrl = "http://am111bionic.qa.archivematica.net:8000"
apiCommand = "/api/v2/file/"
limit = "20"
offset = "0"
username = "test"
apiKey = "110xapikey"
totalAIPs = 0


def get_packages(nextUrl):
    """
    request package metadata from Archivematica Storage Service
    """

    if nextUrl is not None:
        packages_response = requests.get(baseUrl + nextUrl)
    else:
        packages_response = requests.get(
            baseUrl
            + apiCommand
            + "?limit="
            + limit
            + "&offset="
            + offset
            + "&username="
            + username
            + "&api_key="
            + apiKey
        )

    return packages_response.json()


def get_mets(ssPackages):
    """
    request METS files from Archivematica AIP packages
    """

    for package in ssPackages["objects"]:
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

            # request METS file
            mets_response = requests.get(
                baseUrl
                + apiCommand
                + package["uuid"]
                + "/extract_file/?relative_path_to_file="
                + relative_path_to_mets
                + "&username="
                + username
                + "&api_key="
                + apiKey
            )

            # save METS files to disk
            filename = package["uuid"] + ".xml"
            with open("downloads/" + timestampStr + "/" + filename, "wb") as file:
                file.write(mets_response.content)

            # count number of actual AIP METS files (versus packages) downloaded
            global totalAIPs
            totalAIPs += 1
    return totalAIPs


# create "downloads/" directory if it doesn't exist
if not os.path.exists("downloads/"):
    os.makedirs("downloads/")

# create a subdirectory for each download job using a timestamp as its name
dateTimeObj = datetime.now()
timestampStr = dateTimeObj.strftime("%Y-%m-%d--%H:%M:%S")
os.makedirs("downloads/" + timestampStr + "/")

# initial packages request
firstPackages = get_packages(nextUrl=None)

# output basic request information to user
print("base URL: " + baseUrl)
print("total number of packages: " + str(firstPackages["meta"]["total_count"]))
print("download limit: " + limit)

# initial METS request
get_mets(firstPackages)

print("AIP METS downloaded: " + str(totalAIPs))
nextUrl = firstPackages["meta"]["next"]

# iterate over all packages in the Archivematica Storage Service
while nextUrl is not None:
    print("next URL: " + nextUrl)
    ssPackages = get_packages(nextUrl)
    get_mets(ssPackages)
    print("AIP METS downloaded: " + str(totalAIPs))
    nextUrl = ssPackages["meta"]["next"]

# write download summary information to a file
with open("downloads/" + timestampStr + "/_download_info.txt", "w") as download_info:
    download_info.write("base URL of Archivematica Storage Service: " + baseUrl + "\n")
    download_info.write(
        "total number of packages in Storage Service: "
        + str(firstPackages["meta"]["total_count"])
        + "\n"
    )
    download_info.write("total number of AIP METS downloaded: " + str(totalAIPs) + "\n")
    download_info.write("download start time: " + timestampStr + "\n")
    nowdateTimeObj = datetime.now()
    nowtimestampStr = nowdateTimeObj.strftime("%Y-%m-%d--%H:%M:%S" + "\n")
    download_info.write("download finish time: " + nowtimestampStr)
    download_info.close()
