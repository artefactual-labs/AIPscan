import json
import pathlib

from AIPscan.Aggregator.task_helpers import (
    format_api_url_with_limit_offset,
    get_packages_directory,
    parse_package_list_file,
    process_package_object,
)
from AIPscan.Aggregator.tasks import handle_deletion, make_request, start_mets_task


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


def import_packages(
    packages,
    start_item,
    end_item,
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
            handle_deletion(package)

            if not package.is_undeleted_aip():
                continue

            start_mets_task(
                package.uuid,
                package.size,
                package.get_relative_path(),
                package.current_location,
                package.origin_pipeline,
                timestamp_str,
                package_list_no,
                storage_service_id,
                fetch_job_id,
                False,
            )

    return processed_packages
