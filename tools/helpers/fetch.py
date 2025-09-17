import json
import pathlib

from AIPscan.Aggregator.task_helpers import format_api_url_with_limit_offset
from AIPscan.Aggregator.task_helpers import get_packages_directory
from AIPscan.Aggregator.task_helpers import parse_package_list_file
from AIPscan.Aggregator.tasks import make_request


def determine_start_and_end_item(page, packages_per_page, total_packages):
    if page is None:
        start_item = 1
        end_item = total_packages
    else:
        start_item = ((page - 1) * packages_per_page) + 1
        end_item = start_item + packages_per_page - 1

    # Describe start and end package
    if total_packages < end_item:
        end_item = total_packages

    return start_item, end_item


def fetch_and_write_packages(storage_service, package_filepath):
    (_, request_url_without_api_key, request_url) = format_api_url_with_limit_offset(
        storage_service
    )

    packages = make_request(request_url, request_url_without_api_key)
    with open(package_filepath, "w", encoding="utf-8") as f:
        json.dump(packages, f)

    return packages


def create_packages_directory(timestamp_str):
    packages_dir = get_packages_directory(timestamp_str)
    if not pathlib.Path(packages_dir).is_dir():
        pathlib.Path(packages_dir).mkdir(parents=True, exist_ok=True)

    return packages_dir


def create_mets_directory(timestamp_str):
    mets_dir = pathlib.Path("AIPscan/Aggregator/downloads") / timestamp_str / "mets"

    if not pathlib.Path(mets_dir).is_dir():
        pathlib.Path(mets_dir).mkdir(parents=True, exist_ok=True)


def get_packages(storage_service, packages_dir):
    package_filepath = pathlib.Path(packages_dir) / "packages.json"

    if pathlib.Path(package_filepath).is_file():
        packages = parse_package_list_file(package_filepath, None, False)
    else:
        packages = fetch_and_write_packages(storage_service, package_filepath)

    return packages
