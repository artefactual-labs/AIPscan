import json
import os

from AIPscan.Aggregator import database_helpers
from AIPscan.Aggregator.task_helpers import (
    format_api_url_with_limit_offset,
    get_packages_directory,
    process_package_object,
)
from AIPscan.Aggregator.tasks import delete_aip, get_mets, make_request


def assemble_api_url_dict(storage_service, offset=0, limit=1_000_000):
    return {
        "baseUrl": storage_service.url,
        "userName": storage_service.user_name,
        "apiKey": storage_service.api_key,
        "offset": offset,
        "limit": limit,
    }


def fetch_and_write_packages(storage_service, package_filename):
    api_url = assemble_api_url_dict(storage_service)

    (_, request_url_without_api_key, request_url) = format_api_url_with_limit_offset(
        api_url
    )

    packages = make_request(request_url, request_url_without_api_key)
    with open(package_filename, "w", encoding="utf-8") as f:
        json.dump(packages, f)

    return packages


def create_packages_directory(timestamp_str):
    packages_dir = get_packages_directory(timestamp_str)
    if not os.path.isdir(packages_dir):
        os.makedirs(packages_dir)

    return packages_dir


def create_mets_directory(timestamp_str):
    mets_dir = os.path.join("AIPscan/Aggregator/downloads", timestamp_str, "mets")
    if not os.path.isdir(mets_dir):
        os.makedirs(mets_dir)


def get_packages(storage_service, packages_dir):
    package_filename = os.path.join(packages_dir, "packages.json")

    if os.path.isfile(package_filename):
        with open(package_filename) as f:
            packages = json.load(f)
    else:
        packages = fetch_and_write_packages(storage_service, package_filename)

    return packages


def import_packages(
    packages,
    start_item,
    end_item,
    api_url,
    storage_service_id,
    timestamp_str,
    package_list_no,
    fetch_job_id,
    packages_per_page,
    logger,
):
    processed_packages = []

    package_count = 0
    for package_obj in packages["objects"]:
        package_count += 1

        package = process_package_object(package_obj)

        if package_count >= start_item and package_count <= end_item:
            # Calculate current item being processed
            current_item = start_item + len(processed_packages)
            logger.info(f"Processing {package.uuid} ({current_item} of {end_item})")

            processed_packages.append(package)

            if package.is_deleted():
                delete_aip(package.uuid)
                continue

            if not package.is_aip():
                continue

            storage_location = database_helpers.create_or_update_storage_location(
                package.current_location, api_url, storage_service_id
            )

            pipeline = database_helpers.create_or_update_pipeline(
                package.origin_pipeline, api_url
            )

            args = [
                package.uuid,
                package.size,
                package.get_relative_path(),
                api_url,
                timestamp_str,
                package_list_no,
                storage_service_id,
                storage_location.id,
                pipeline.id,
                fetch_job_id,
                logger,
            ]
            get_mets.apply(args=args)

    return processed_packages
