import requests

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

## write response to a file
# import json
# with open("ss_packages.json", "w") as json_file:
# json.dump(ss_packages, json_file)

for package in ss_packages["objects"]:
    # build relative path to METS file
    relative_path = package["current_path"][40:-3]
    relative_path_to_mets = relative_path + "/data/METS." + package["uuid"] + ".xml"

    # request METS file and save to disk
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

    with open(package["uuid"] + ".xml", "wb") as file:
        file.write(mets_response.content)

    # TODO move to a separate downloads folder
