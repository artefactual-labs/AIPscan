import os
import time
from datetime import datetime

from celery.result import AsyncResult
from flask import Blueprint
from flask import abort
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from AIPscan import db
from AIPscan import decorators
from AIPscan import typesense_helpers
from AIPscan.Aggregator import database_helpers
from AIPscan.Aggregator import tasks
from AIPscan.Aggregator.forms import StorageServiceForm
from AIPscan.Aggregator.task_helpers import format_api_url_with_limit_offset
from AIPscan.Aggregator.task_helpers import get_packages_directory
from AIPscan.Aggregator.tasks import TaskError
from AIPscan.celery import celery

# Custom celery Models.
from AIPscan.models import FetchJob
from AIPscan.models import StorageService
from AIPscan.models import get_mets_tasks
from AIPscan.models import index_tasks
from AIPscan.models import package_tasks

aggregator = Blueprint("aggregator", __name__, template_folder="templates")


# PICTURAE TODO: Starting to see patterns shared across modules, e.g.
# date handling in the data module and in here. Let's bring those
# together in a helpful kind of way.
def _split_ms(date_string):
    """Remove microseconds from the given date string."""
    return str(date_string).split(".")[0]


def _format_date(date_string):
    """Format date to something nicer that can played back in reports"""
    DATE_FORMAT_FULL = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT_PARTIAL = "%Y-%m-%d"
    formatted_date = datetime.strptime(_split_ms(date_string), DATE_FORMAT_FULL)
    return formatted_date.strftime(DATE_FORMAT_PARTIAL)


def _test_storage_service_connection(storage_service):
    """Test Storage Service credentials.

    :param storage_service: StorageService instance

    :raises ConnectionError: if credentials are invalid
    """
    _, request_url_without_api_key, request_url = format_api_url_with_limit_offset(
        storage_service
    )
    try:
        _ = tasks.make_request(request_url, request_url_without_api_key)
    except TaskError as err:
        raise ConnectionError(str(err)) from err


@aggregator.route("/", methods=["GET"])
def ss_default():
    # load the default storage service
    storage_service = StorageService.query.filter_by(default=True).first()
    if storage_service is None:
        # no default is set, retrieve the first storage service
        storage_service = StorageService.query.first()
        # there are no storage services defined at all
        if storage_service is None:
            return redirect(url_for("aggregator.storage_services"))
    mets_fetch_jobs = FetchJob.query.filter_by(
        storage_service_id=storage_service.id
    ).all()
    return render_template(
        "storage_service.html",
        storage_service=storage_service,
        mets_fetch_jobs=mets_fetch_jobs,
    )


@aggregator.route("/storage_service/<storage_service_id>", methods=["GET"])
def storage_service(storage_service_id):
    storage_service = db.session.get(StorageService, storage_service_id)

    if storage_service is None:
        abort(404)

    mets_fetch_jobs = FetchJob.query.filter_by(
        storage_service_id=storage_service_id
    ).all()
    return render_template(
        "storage_service.html",
        storage_service=storage_service,
        mets_fetch_jobs=mets_fetch_jobs,
    )


@aggregator.route("/storage_services", methods=["GET"])
def storage_services():
    storage_services = StorageService.query.all()
    return render_template("storage_services.html", storage_services=storage_services)


@aggregator.route("/edit_storage_service/<storage_service_id>", methods=["GET", "POST"])
def edit_storage_service(storage_service_id):
    form = StorageServiceForm()
    storage_service = db.session.get(StorageService, storage_service_id)

    if storage_service is None:
        abort(404)

    if request.method == "GET":
        form.name.data = storage_service.name
        form.url.data = storage_service.url
        form.user_name.data = storage_service.user_name
        form.download_limit.data = storage_service.download_limit
        form.download_offset.data = storage_service.download_offset
        form.api_key.data = storage_service.api_key
        form.default.data = storage_service.default
    if form.validate_on_submit():
        storage_service.name = form.name.data
        storage_service.url = form.url.data
        storage_service.user_name = form.user_name.data
        storage_service.api_key = form.api_key.data
        storage_service.download_limit = form.download_limit.data
        storage_service.download_offset = form.download_offset.data
        if form.default.data is True:
            storage_services = StorageService.query.all()
            for ss in storage_services:
                ss.default = False
        storage_service.default = form.default.data
        db.session.commit()
        flash(f"Storage service {form.name.data} updated")
        return redirect(url_for("aggregator.storage_services"))
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@aggregator.route("/new_storage_service", methods=["GET", "POST"])
def new_storage_service():
    form = StorageServiceForm()
    if form.validate_on_submit():
        ss = StorageService(
            name=form.name.data,
            url=form.url.data,
            user_name=form.user_name.data,
            api_key=form.api_key.data,
            download_limit=form.download_limit.data,
            download_offset=form.download_offset.data,
            default=form.default.data,
        )
        db.session.add(ss)
        db.session.commit()
        flash(f"New storage service {form.name.data} created")
        return redirect(url_for("aggregator.storage_services"))
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@aggregator.route("/delete_storage_service/<storage_service_id>", methods=["GET"])
@decorators.confirm_required(
    StorageService,
    "storage_service_id",
    "Are you sure you'd like to delete this storage service?",
    "Delete",
    "aggregator.ss_default",
)
def delete_storage_service(storage_service_id):
    storage_service = db.session.get(StorageService, storage_service_id)

    if storage_service is None:
        abort(404)

    tasks.delete_storage_service.delay(storage_service_id)

    return render_template(
        "result_message.html",
        title="Storage Service",
        message=f"Storage service '{storage_service.name}' is being deleted",
    )


@aggregator.route("/new_fetch_job/<fetch_job_id>", methods=["POST"])
def new_fetch_job(fetch_job_id):
    """Fetch and process AIP METS files from Storage Service."""
    storage_service = db.session.get(StorageService, fetch_job_id)

    # Check Storage Service credentials and return 400 if invalid prior to
    # creating the Fetch Job and kicking off the Celery task.
    try:
        _test_storage_service_connection(storage_service)
    except ConnectionError:
        return jsonify({}), 400

    # create a subdirectory for the download job using a timestamp as its name
    datetime_obj_start = datetime.now().replace(microsecond=0)
    timestamp_str = datetime_obj_start.strftime("%Y-%m-%d-%H-%M-%S")
    timestamp = datetime_obj_start.strftime("%Y-%m-%d %H:%M:%S")

    try:
        os.makedirs(f"AIPscan/Aggregator/downloads/{timestamp_str}/packages/")
        os.makedirs(f"AIPscan/Aggregator/downloads/{timestamp_str}/mets/")
    except PermissionError:
        return jsonify({"message": "Permissions error"}), 500

    # create a fetch_job record in the aipscan database
    fetch_job = database_helpers.create_fetch_job(
        datetime_obj_start, timestamp_str, storage_service.id
    )

    packages_directory = get_packages_directory(timestamp_str)

    # send the METS fetch job to a background job that will coordinate other workers
    task = tasks.workflow_coordinator.delay(
        timestamp_str, storage_service.id, fetch_job.id, packages_directory
    )

    fetch_job_id = fetch_job.id
    task_id = _wait_for_package_list_task_id(task.id)
    if task_id is None:
        return (
            jsonify(
                {
                    "message": "The background task failed to start in a timely manner. Please check the system logs or try again later."
                }
            ),
            500,
        )

    # Send response back to JavaScript function that was triggered by
    # the 'New Fetch Job' button.
    response = {"timestamp": timestamp, "taskId": task_id, "fetchJobId": fetch_job_id}
    return jsonify(response)


@aggregator.route("/delete_fetch_job/<fetch_job_id>", methods=["GET"])
@decorators.confirm_required(
    FetchJob,
    "fetch_job_id",
    "Are you sure you'd like to delete this fetch job?",
    "Delete",
    "aggregator.ss_default",
)
def delete_fetch_job(fetch_job_id):
    fetch_job = db.session.get(FetchJob, fetch_job_id)

    if fetch_job is None:
        abort(404)

    storage_service = db.session.get(StorageService, fetch_job.storage_service_id)
    tasks.delete_fetch_job.delay(fetch_job_id)

    flash(f"Fetch job {fetch_job.download_start} is being deleted")
    return redirect(
        url_for("aggregator.storage_service", storage_service_id=storage_service.id)
    )


@aggregator.route("/package_list_task_status/<taskid>")
def task_status(taskid):
    task = tasks.package_lists_request.AsyncResult(taskid, app=celery)
    if task.state == "PENDING":
        # job did not start yet
        response = {"state": task.state}
    elif task.state != "FAILURE":
        if task.state == "SUCCESS":
            obj = package_tasks.query.filter_by(package_task_id=task.id).first()
            coordinator_id = obj.workflow_coordinator_id
            response = {"state": task.state, "coordinatorId": coordinator_id}
        else:
            response = {"state": task.state, "message": task.info.get("message")}
    # CR Note: I am not sure we will ever meet this else, because
    # task.state will always be intercepted through != FAILUTE. IDK. Do
    # you read it the same way?
    else:
        # something went wrong in the background job
        response = {
            "state": task.state,
            "status": str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@aggregator.route("/get_mets_task_status/<coordinatorid>")
def get_mets_task_status(coordinatorid):
    """Get mets task status"""
    totalAIPs = int(request.args.get("totalAIPs"))
    fetchJobId = int(request.args.get("fetchJobId"))
    mets_tasks = get_mets_tasks.query.filter_by(
        workflow_coordinator_id=coordinatorid, status=None
    ).all()
    response = []
    incomplete = 0
    for row in mets_tasks:
        task_id = row.get_mets_task_id
        package_uuid = row.package_uuid
        task_result = AsyncResult(id=task_id, app=celery)
        mets_task_status = task_result.state
        if mets_task_status is None:
            incomplete = incomplete + 1
            continue
        if (mets_task_status == "SUCCESS") or (mets_task_status[0] == "FAILURE"):
            totalAIPs += 1
            response.append(
                {
                    "state": mets_task_status,
                    "package": f"METS.{package_uuid}.xml",
                    "totalAIPs": totalAIPs,
                }
            )
            obj = get_mets_tasks.query.filter_by(get_mets_task_id=task_id).first()
            obj.status = mets_task_status
            db.session.commit()
    if len(mets_tasks) != 0:
        return jsonify(response)
    if incomplete > 0 and totalAIPs == 0:
        response = {"state": "PENDING"}
        return jsonify(response)
    downloadEnd = datetime.now().replace(microsecond=0)
    obj = FetchJob.query.filter_by(id=fetchJobId).first()
    start = obj.download_start
    downloadStart = _format_date(start)
    obj.download_end = downloadEnd
    db.session.commit()
    response = {"state": "COMPLETED"}
    flash(f"Fetch Job {downloadStart} completed")
    return jsonify(response)


@aggregator.route("/index_refresh/<fetch_job_id>")
def index_refresh(fetch_job_id):
    if not typesense_helpers.typesense_enabled():
        abort(422)

    tasks.start_index_task(fetch_job_id)

    response = {"state": "ACCEPTED"}
    return jsonify(response)


@aggregator.route("/indexing_status/<fetch_job_id>")
def index_status(fetch_job_id):
    if not typesense_helpers.typesense_enabled():
        abort(422)

    # Get status from DB
    obj = index_tasks.query.filter_by(fetch_job_id=fetch_job_id).first()

    response = {}

    if obj.indexing_end is None:
        response["progress"] = obj.indexing_progress
        response["state"] = "PENDING"
    else:
        response = {"state": "COMPLETED"}

    return jsonify(response)


def _wait_for_package_list_task_id(
    coordinator_task_id, timeout_seconds=60, sleep_seconds=0.2
):
    """Wait briefly for the child package-list task id created by the coordinator.

    The coordinator worker enqueues a child task and writes a mapping row
    (workflow_coordinator_id -> package_task_id). Due to DB transaction
    isolation (e.g. MySQL REPEATABLE READ) the current session may not see
    that worker's commit, so we remove the session between polls to get fresh
    reads.

    This spin-wait is a pragmatic shortcut. Long-term, avoid server-side
    polling: return immediately with the coordinator id and have the client
    poll a dedicated endpoint until the child id appears.

    Returns the child task id string or None if not observed within timeout.
    """
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout_seconds:
        # End current transaction to avoid repeatable-read snapshot issues.
        db.session.remove()
        obj = package_tasks.query.filter_by(
            workflow_coordinator_id=coordinator_task_id
        ).first()
        if obj and obj.package_task_id:
            return obj.package_task_id
        time.sleep(sleep_seconds)
    return None
