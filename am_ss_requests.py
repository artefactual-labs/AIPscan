import requests
import os.path
from datetime import datetime

base_url = "http://am111xenial.qa.archivematica.net:8000"
api_command = "/api/v2/file/"
limit = "10"
username = "test"
api_key = "110xapikey"

packages_response = requests.get(
    base_url
    + api_command
    + "?limit="
    + limit
    + "&username="
    + username
    + "&api_key="
    + api_key
)

ss_packages = packages_response.json()

# output basic request information to user
print("base URL: " + base_url)
print("total AIP count: " + str(ss_packages["meta"]["total_count"]))
print("limit: " + limit)
print("next URL: " + ss_packages["meta"]["next"])

# create "downloads/" directory if it doesn't exist
if not os.path.exists("downloads/"):
    os.makedirs("downloads/")

# create a downloads/ subdirectory for each job using timestamp as name
dateTimeObj = datetime.now()
timestampStr = dateTimeObj.strftime("%Y-%m-%d--%H:%M:%S")
os.makedirs("downloads/" + timestampStr + "/")

for package in ss_packages["objects"]:
    # build relative path to METS file
    relative_path = package["current_path"][40:-3]
    relative_path_to_mets = relative_path + "/data/METS." + package["uuid"] + ".xml"

    # request METS file
    mets_response = requests.get(
        base_url
        + api_command
        + package["uuid"]
        + "/extract_file/?relative_path_to_file="
        + relative_path_to_mets
        + "&username="
        + username
        + "&api_key="
        + api_key
    )

    # save METS files to disk
    filename = package["uuid"] + ".xml"
    with open("downloads/" + timestampStr + "/" + filename, "wb") as file:
        file.write(mets_response.content)
