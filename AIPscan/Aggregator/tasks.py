import json
import os
import shutil
from datetime import datetime

import requests
from celery.utils.log import get_task_logger

from AIPscan import db
from AIPscan import typesense_helpers
from AIPscan.Aggregator import database_helpers
from AIPscan.Aggregator.celery_helpers import with_db_session
from AIPscan.Aggregator.celery_helpers import write_celery_update
from AIPscan.Aggregator.mets_parse_helpers import METSError
from AIPscan.Aggregator.mets_parse_helpers import download_mets
from AIPscan.Aggregator.mets_parse_helpers import get_aip_original_name
from AIPscan.Aggregator.mets_parse_helpers import parse_mets_with_metsrw
from AIPscan.Aggregator.task_helpers import format_api_url_with_limit_offset
from AIPscan.Aggregator.task_helpers import parse_package_list_file
from AIPscan.Aggregator.task_helpers import process_package_object
from AIPscan.Aggregator.task_helpers import summarize_fetch_job_results
from AIPscan.celery import celery
from AIPscan.models import AIP
from AIPscan.models import Agent
from AIPscan.models import FetchJob
from AIPscan.models import StorageService
from AIPscan.models import get_mets_tasks
from AIPscan.models import index_tasks

logger = get_task_logger(__name__)


class TaskError(Exception):
    """Exception to call when there is a problem downloading from the
    storage service. The exception is known and asks for user
    intervention.
    """


def write_packages_json(count, packages, packages_directory):
    """Write package JSON to disk"""
    json_download_file = os.path.join(packages_directory, f"packages{count}.json")
    logger.info("Packages file is downloaded to '%s'", json_download_file)
    try:
        with open(json_download_file, "w") as json_file:
            json.dump(packages, json_file, indent=4)
    except json.JSONDecodeError:
        logger.error("Cannot decode JSON from %s", json_download_file)


def start_mets_task(
    package_uuid,
    aip_size,
    relative_path_to_mets,
    current_location,
    origin_pipeline,
    timestamp_str,
    package_list_no,
    storage_service_id,
    fetch_job_id,
    run_as_task=True,
):
    """Initiate a get_mets task worker and record the event in the
    celery database.
    """
    storage_service = db.session.get(StorageService, storage_service_id)
    storage_location = database_helpers.create_or_update_storage_location(
        current_location, storage_service
    )

    pipeline = database_helpers.create_or_update_pipeline(
        origin_pipeline, storage_service
    )

    args = [
        package_uuid,
        aip_size,
        relative_path_to_mets,
        timestamp_str,
        package_list_no,
        storage_service_id,
        storage_location.id,
        pipeline.id,
        fetch_job_id,
    ]

    if run_as_task:
        # Call worker to download and parse METS File.
        get_mets_task = get_mets.delay(*args)
        mets_task = get_mets_tasks(
            get_mets_task_id=get_mets_task.id,
            workflow_coordinator_id=workflow_coordinator.request.id,
            package_uuid=package_uuid,
            status=None,
        )
        db.session.add(mets_task)
        db.session.commit()
    else:
        # Execute immediately.
        get_mets.apply(args=args)


def delete_aip(uuid):
    logger.warning("Package deleted from SS: '%s'", uuid)

    deleted_aip = AIP.query.filter_by(uuid=uuid).first()

    if deleted_aip is not None:
        logger.warning("Deleting AIP: %s", uuid)
        database_helpers.delete_aip_object(deleted_aip)


@celery.task(bind=True)
@with_db_session
def workflow_coordinator(
    self, timestamp, storage_service_id, fetch_job_id, packages_directory
):
    logger.info("Packages directory is: %s", packages_directory)

    # Send package list request to a worker.
    package_lists_task = package_lists_request.delay(
        storage_service_id, timestamp, packages_directory
    )

    write_celery_update(package_lists_task, workflow_coordinator)

    # Wait for package lists task to finish downloading all package
    # lists.
    task = package_lists_request.AsyncResult(package_lists_task.id, app=celery)
    while True:
        if (task.state == "SUCCESS") or (task.state == "FAILURE"):
            break

    if isinstance(package_lists_task.info, TaskError):
        # Re-raise.
        raise (package_lists_task.info)

    total_package_lists = package_lists_task.info["totalPackageLists"]

    all_packages = []
    for package_list_no in range(1, total_package_lists + 1):
        json_file_path = os.path.join(
            packages_directory, f"packages{package_list_no}.json"
        )
        # Process packages and create a new worker to download and parse
        # each METS separately.
        packages = parse_package_list_file(json_file_path, logger, True)

        packages = process_packages(
            packages, storage_service_id, timestamp, package_list_no, fetch_job_id, True
        )

        all_packages = all_packages + packages

    total_packages_count = package_lists_task.info["totalPackages"]

    obj = database_helpers.update_fetch_job(
        fetch_job_id, all_packages, total_packages_count
    )

    logger.info("%s", summarize_fetch_job_results(obj))


def make_request(request_url, request_url_without_api_key):
    """Make our request to the storage service and return a valid
    response to our caller or raise a TaskError for celery.
    """
    response = requests.get(request_url)
    if response.status_code != requests.codes.ok:
        err = f"Check the URL and API details, cannot connect to: `{request_url_without_api_key}`"
        logger.error(err)
        raise TaskError(f"Bad response from server: {err}")
    try:
        packages = response.json()
    except json.JSONDecodeError as exc:
        msg = "Response is OK, but cannot decode JSON from server"
        logger.error(msg)
        raise TaskError(msg) from exc
    return packages


@celery.task(bind=True)
@with_db_session
def package_lists_request(self, storage_service_id, timestamp, packages_directory):
    """Request package lists from the storage service. Package lists
    will contain details of the AIPs that we want to download.
    """
    META = "meta"
    NEXT = "next"
    COUNT = "total_count"
    IN_PROGRESS = "IN PROGRESS"

    storage_service = db.session.get(StorageService, storage_service_id)

    (
        base_url,
        request_url_without_api_key,
        request_url,
    ) = format_api_url_with_limit_offset(storage_service)

    # First packages request.
    packages = make_request(request_url, request_url_without_api_key)
    packages_count = 1

    # Calculate how many package list files will be downloaded based on
    # total number of packages and the download limit
    total_packages = int(packages.get(META, {}).get(COUNT, 0))
    total_package_lists = int(total_packages / int(storage_service.download_limit)) + (
        total_packages % int(storage_service.download_limit) > 0
    )

    # There may be more packages to download to let's access those here.
    # TODO: `request_url_without_api_key` at this point will not be as
    # accurate. If we have more time, modify `format_api_url_with_limit_offset(...)`
    # to work with raw offset and limit data to make up for the fact
    # that an API key is plain-encoded in next_url.
    next_url = packages.get(META, {}).get(NEXT, None)
    write_packages_json(packages_count, packages, packages_directory)
    while next_url is not None:
        next_request = f"{base_url}{next_url}"
        next_packages = make_request(next_request, request_url_without_api_key)
        packages_count += 1
        write_packages_json(packages_count, next_packages, packages_directory)
        next_url = next_packages.get(META, {}).get(NEXT, None)
        self.update_state(
            state=IN_PROGRESS,
            meta={
                "message": f"Total packages: {total_packages} Total package lists: {total_package_lists}"
            },
        )

    return {
        "totalPackageLists": total_package_lists,
        "totalPackages": total_packages,
        "timestampStr": timestamp,
    }


def start_index_task(fetch_job_id):
    task = index_task.delay(fetch_job_id)

    index_task_obj = index_tasks(
        index_task_id=task.id, fetch_job_id=fetch_job_id, indexing_start=datetime.now()
    )
    db.session.add(index_task_obj)
    db.session.commit()


@celery.task()
@with_db_session
def index_task(fetch_job_id):
    # Update Typesense index
    typesense_helpers.initialize_index()

    index_task_obj = index_tasks.query.filter_by(fetch_job_id=fetch_job_id).first()

    for status in typesense_helpers.populate_index():
        if status["percent"] is not None:
            index_task_obj.indexing_progress = (
                f"Indexing {status['type']} data ({status['percent']}%)"
            )

            db.session.add(index_task_obj)
            db.session.commit()

    # Record indexing end time
    index_task_obj.indexing_end = datetime.now()

    db.session.add(index_task_obj)
    db.session.commit()


@celery.task()
@with_db_session
def get_mets(
    package_uuid,
    aip_size,
    relative_path_to_mets,
    timestamp_str,
    package_list_no,
    storage_service_id,
    storage_location_id,
    origin_pipeline_id,
    fetch_job_id,
    customlogger=None,
):
    """Request METS XML file from the storage service and parse.

    Download a METS file from an AIP that is stored in the storage
    service and then parse the results into the AIPscan database.

    This function relies on being able to use mets-reader-writer which
    is the primary object we will be passing about.

    TODO: Log METS errors.

    The "customlogger" argument allows an external logger to be specified when
    the task's logic is executed, using the task's "apply" method, by an
    external application like a batch script.
    """
    # Set logger
    tasklogger = logger
    if customlogger is not None:
        tasklogger = customlogger

    # Download METS file
    storage_service = db.session.get(StorageService, storage_service_id)
    download_file, mets_hash = download_mets(
        storage_service,
        package_uuid,
        relative_path_to_mets,
        timestamp_str,
        package_list_no,
    )
    mets_name = os.path.basename(download_file)

    # If METS file's hash matches an existing value, this is a duplicate of an
    # existing AIP and we can safely ignore it.
    matching_aip = AIP.query.filter_by(mets_sha256=mets_hash).first()
    if matching_aip is not None:
        tasklogger.info(
            f"Skipping METS file {mets_name} - identical to existing record"
        )
        try:
            os.remove(download_file)
        except OSError as err:
            tasklogger.warning(f"Unable to delete METS file: {err}")
        return

    tasklogger.info(f"Processing METS file {mets_name}")

    try:
        mets = parse_mets_with_metsrw(download_file)
    except METSError:
        # An error we need to log and report back to the user.
        return

    try:
        original_name = get_aip_original_name(mets)
    except METSError:
        # Some other error with the METS file that we might want to
        # log and act upon.
        original_name = package_uuid

    # Delete records of any previous versions of this AIP, which will shortly
    # be replaced by new records from the updated METS.
    previous_aips = AIP.query.filter_by(uuid=package_uuid).all()
    for previous_aip in previous_aips:
        tasklogger.info(
            f"Deleting record for AIP {package_uuid} to replace from newer METS"
        )
        database_helpers.delete_aip_object(previous_aip)

    aip = database_helpers.create_aip_object(
        package_uuid=package_uuid,
        transfer_name=original_name,
        create_date=mets.createdate,
        mets_sha256=mets_hash,
        size=aip_size,
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job_id,
        origin_pipeline_id=origin_pipeline_id,
    )

    database_helpers.process_aip_data(aip, mets)

    # Delete downloaded METS file.
    try:
        os.remove(download_file)
    except OSError as err:
        tasklogger.warning(f"Unable to delete METS file: {err}")


@celery.task()
@with_db_session
def delete_fetch_job(fetch_job_id):
    fetch_job = db.session.get(FetchJob, fetch_job_id)
    if os.path.exists(fetch_job.download_directory):
        shutil.rmtree(fetch_job.download_directory)
    db.session.delete(fetch_job)
    db.session.commit()


@celery.task()
@with_db_session
def delete_storage_service(storage_service_id):
    storage_service = db.session.get(StorageService, storage_service_id)
    mets_fetch_jobs = FetchJob.query.filter_by(
        storage_service_id=storage_service_id
    ).all()
    for mets_fetch_job in mets_fetch_jobs:
        if os.path.exists(mets_fetch_job.download_directory):
            shutil.rmtree(mets_fetch_job.download_directory)

    # Delete agents associated to the deleted storage service
    agents = Agent.query.filter_by(storage_service_id=storage_service_id).all()
    for agent in agents:
        logger.info("Deleting agent: %s", agent)
        db.session.delete(agent)

    db.session.delete(storage_service)
    db.session.commit()


def handle_deletion(package):
    if package.is_deleted():
        delete_aip(package.uuid)


def process_packages(
    packages,
    storage_service_id,
    timestamp_str,
    package_list_no,
    fetch_job_id,
    run_as_task=False,
    logger=None,
    start_item=None,
    end_item=None,
):
    """Parse packages documents from the storage service and initiate
    the load mets functions of AIPscan. Results are written to the
    database.
    """
    processed_packages = []

    package_count = 0
    for package_obj in packages.get("objects", []):
        package_count += 1

        package = process_package_object(package_obj)

        # Only process packages within paging window, if specified
        if start_item is None or (
            package_count >= start_item and package_count <= end_item
        ):
            # Calculate current item being processed
            if start_item is not None:
                current_item = start_item + len(processed_packages)

                if logger:
                    logger.info(
                        f"Processing {package.uuid} ({current_item} of {end_item})"
                    )

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
                run_as_task,
            )

    return processed_packages
