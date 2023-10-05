from datetime import datetime
import json
import logging
import os
import sys

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.orm.exc import DetachedInstanceError

# Add parent directory to Python path
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from AIPscan import create_app
from AIPscan import db
from AIPscan.models import StorageService

from AIPscan.Aggregator import database_helpers

from AIPscan.Aggregator.task_helpers import (
    create_numbered_subdirs,
    format_api_url_with_limit_offset,
    get_packages_directory,
    process_package_object,
)

from AIPscan.Aggregator.tasks import delete_aip, make_request, get_mets

from argparse import ArgumentParser, ArgumentTypeError


def check_positive(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue


def arg_parser():
    description = """The AIPscan fetch tool enables subsets of packages
        from a storage server to be processed."""

    parser = ArgumentParser(description=description)

    storage_id_help = "storage server ID"
    parser.add_argument(
        "-s",
        "--ss-id",
        action="store",
        type=check_positive,
        required=True,
        help=storage_id_help,
    )

    session_id_help = "session identifier"
    parser.add_argument(
        "-i", "--session-id", action="store", required=True, help=session_id_help
    )

    page_help = "page"
    parser.add_argument(
        "-p",
        "--page",
        action="store",
        type=check_positive,
        required=True,
        help=page_help,
    )

    packages_per_page_help = "items per page"
    parser.add_argument(
        "-n",
        "--packages-per-page",
        action="store",
        type=check_positive,
        required=True,
        help=packages_per_page_help,
    )

    logging_help = "log file"
    parser.add_argument("-l", "--log-file", action="store", help=logging_help)

    return parser


# Process CLI arguments
parser = arg_parser()
args = parser.parse_args()

storage_service_id = args.ss_id
timestamp_str = args.session_id
page = args.page
packages_per_page = args.packages_per_page
logfile = args.log_file

package_list_no = "batch"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    filename=logfile,
)

logger_name = os.path.basename(sys.argv[0])
logger = logging.getLogger(logger_name)
logger.setLevel(logging.INFO)

root = logging.getLogger()
root.setLevel(logging.INFO)

# Set up Flask instance and SQLAlchemy DB session
app = create_app("default")
app_ctx = app.app_context()
app_ctx.push()

db.init_app(app)

# Get storage service configuration
storage_service = StorageService.query.get(storage_service_id)

if storage_service is None:
    logger.critical(f"Storage service ID {storage_service_id} not found.")
    sys.exit(1)

# Intialize variables used to make requests
api_url = {
    "baseUrl": storage_service.url,
    "userName": storage_service.user_name,
    "apiKey": storage_service.api_key,
    "offset": 0,
    "limit": 1_000_000,
}

(_, request_url_without_api_key, request_url) = format_api_url_with_limit_offset(
    api_url
)

# Create a fetch_job record in the AIPscan database and take note of its ID
datetime_obj_start = datetime.now().replace(microsecond=0)

fetch_job = database_helpers.create_fetch_job(
    datetime_obj_start, timestamp_str, storage_service_id
)
fetch_job_id = fetch_job.id

logger.info(f"Created fetch job record {fetch_job_id}.")

# Create directories, if need be
packages_dir = get_packages_directory(timestamp_str)
if not os.path.isdir(packages_dir):
    os.makedirs(packages_dir)

mets_dir = os.path.join("AIPscan/Aggregator/downloads", timestamp_str, "mets")
if not os.path.isdir(mets_dir):
    os.makedirs(mets_dir)

numbered_subdir = create_numbered_subdirs(timestamp_str, package_list_no)
package_filename = os.path.join(packages_dir, "packages.json")

# Get package data
if os.path.isfile(package_filename):
    with open(package_filename) as f:
        packages = json.load(f)
else:
    packages = make_request(request_url, request_url_without_api_key)
    with open(package_filename, "w", encoding="utf-8") as f:
        json.dump(packages, f)

# Determine start and end package
start_item = ((page - 1) * packages_per_page) + 1
end_item = start_item + packages_per_page - 1
total_packages = len(packages["objects"])

# Describe start and end package
real_end_item = end_item
if total_packages < real_end_item:
    real_end_item = total_packages

# Make sure page is valid and delete fetch job if not
if start_item > total_packages:
    logger.error(
        f"Fetch job deleted. Page {page} would start at package {start_item} but there are only {total_packages} packages."
    )
    db.session.delete(fetch_job)
    db.session.commit()
    sys.exit(1)

logger.info(f"Processing packages {start_item} to {real_end_item} of {total_packages}.")

# Import packages
processed_packages = []

package_count = 0
for package_obj in packages["objects"]:
    package_count += 1

    package = process_package_object(package_obj)

    if package_count >= start_item and package_count <= end_item:
        processed_packages.append(package)

        current_item = len(processed_packages)
        logger.info(
            f"Processing {package.uuid} ({current_item} of {packages_per_page})"
        )

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
        get_mets_task = get_mets.apply(args=args)

fetch_job = database_helpers.update_fetch_job(
    fetch_job_id, processed_packages, total_packages
)

summary = "aips: '{}'; sips: '{}'; dips: '{}'; deleted: '{}'; replicated: '{}'".format(
    fetch_job.total_aips,
    fetch_job.total_sips,
    fetch_job.total_dips,
    fetch_job.total_deleted_aips,
    fetch_job.total_replicas,
)
logger.info("%s", summary)
logger.info(f"Updated fetch job record {fetch_job_id} with package type counts.")
logger.info("Processing complete.")
