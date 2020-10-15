# -*- coding: utf-8 -*-

from datetime import datetime
import os
import shutil

from celery.result import AsyncResult
from flask import Blueprint, render_template, redirect, request, flash, url_for, jsonify

from AIPscan import db
from AIPscan.Aggregator.task_helpers import get_packages_directory
from AIPscan.Aggregator.forms import StorageServiceForm
from AIPscan.Aggregator import tasks
from AIPscan.extensions import celery
from AIPscan.models import (
    FetchJob,
    StorageService,
    # Custom celery Models.
    package_tasks,
    get_mets_tasks,
)

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


@aggregator.route("/storage_service/<id>", methods=["GET"])
def storage_service(id):
    storage_service = StorageService.query.get(id)
    mets_fetch_jobs = FetchJob.query.filter_by(storage_service_id=id).all()
    return render_template(
        "storage_service.html",
        storage_service=storage_service,
        mets_fetch_jobs=mets_fetch_jobs,
    )


@aggregator.route("/storage_services", methods=["GET"])
def storage_services():
    storage_services = StorageService.query.all()
    return render_template("storage_services.html", storage_services=storage_services)


@aggregator.route("/edit_storage_service/<id>", methods=["GET", "POST"])
def edit_storage_service(id):
    form = StorageServiceForm()
    storage_service = StorageService.query.get(id)
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
        flash("Storage service {} updated".format(form.name.data))
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
        flash("New storage service {} created".format(form.name.data))
        return redirect(url_for("aggregator.storage_services"))
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@aggregator.route("/delete_storage_service/<id>", methods=["GET"])
def delete_storage_service(id):
    storage_service = StorageService.query.get(id)
    mets_fetch_jobs = FetchJob.query.filter_by(storage_service_id=id).all()
    for mets_fetch_job in mets_fetch_jobs:
        if os.path.exists(mets_fetch_job.download_directory):
            shutil.rmtree(mets_fetch_job.download_directory)
    db.session.delete(storage_service)
    db.session.commit()
    flash("Storage service '{}' is deleted".format(storage_service.name))
    return redirect(url_for("aggregator.storage_services"))


@aggregator.route("/new_fetch_job/<id>", methods=["POST"])
def new_fetch_job(id):

    # this function is triggered by the Javascript attached to the "New Fetch Job" button

    storage_service = StorageService.query.get(id)
    api_url = {
        "baseUrl": storage_service.url,
        "userName": storage_service.user_name,
        "apiKey": storage_service.api_key,
        "offset": str(storage_service.download_offset),
        "limit": str(storage_service.download_limit),
    }

    # create "downloads/" directory if it doesn't exist
    if not os.path.exists("AIPscan/Aggregator/downloads/"):
        os.makedirs("AIPscan/Aggregator/downloads/")

    # create a subdirectory for the download job using a timestamp as its name
    datetime_obj_start = datetime.now().replace(microsecond=0)
    timestamp_str = datetime_obj_start.strftime("%Y-%m-%d-%H-%M-%S")
    timestamp = datetime_obj_start.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("AIPscan/Aggregator/downloads/" + timestamp_str + "/packages/")
    os.makedirs("AIPscan/Aggregator/downloads/" + timestamp_str + "/mets/")

    # create a fetch_job record in the aipscan database
    # write fetch job info to database
    fetch_job = FetchJob(
        total_packages=None,
        total_deleted_aips=None,
        total_aips=None,
        download_start=datetime_obj_start,
        download_end=None,
        download_directory="AIPscan/Aggregator/downloads/" + timestamp_str + "/",
        storage_service_id=storage_service.id,
    )
    db.session.add(fetch_job)
    db.session.commit()

    packages_directory = get_packages_directory(timestamp_str)

    # send the METS fetch job to a background job that will coordinate other workers
    task = tasks.workflow_coordinator.delay(
        api_url, timestamp_str, storage_service.id, fetch_job.id, packages_directory
    )

    """
    # this only works on the first try, after that Flask is not able to get task info from Celery
    # the compromise is to write the task ID from the Celery worker to its SQLite backend

    coordinator_task = tasks.workflow_coordinator.AsyncResult(task.id, app=celery)
    taskId = coordinator_task.info.get("package_lists_taskId")
    response = {"timestamp": timestamp, "taskId": taskId}
    """

    # Run a while loop in case the workflow coordinator task hasn't
    # finished writing to database yet
    while True:
        obj = package_tasks.query.filter_by(workflow_coordinator_id=task.id).first()
        try:
            task_id = obj.package_task_id
            if task_id is not None:
                break
        except AttributeError:
            continue

    # Send response back to JavaScript function that was triggered by
    # the 'New Fetch Job' button.
    response = {"timestamp": timestamp, "taskId": task_id, "fetchJobId": fetch_job.id}
    return jsonify(response)


@aggregator.route("/delete_fetch_job/<id>", methods=["GET"])
def delete_fetch_job(id):
    fetch_job = FetchJob.query.get(id)
    storage_service = StorageService.query.get(fetch_job.storage_service_id)
    if os.path.exists(fetch_job.download_directory):
        shutil.rmtree(fetch_job.download_directory)
    db.session.delete(fetch_job)
    db.session.commit()
    flash("Fetch job {} is deleted".format(fetch_job.download_start))
    return redirect(url_for("aggregator.storage_service", id=storage_service.id))


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
    for row in mets_tasks:
        task_id = row.get_mets_task_id
        package_uuid = row.package_uuid
        task_result = AsyncResult(id=task_id, app=celery)
        mets_task_status = task_result.state
        if mets_task_status is None:
            continue
        if (mets_task_status == "SUCCESS") or (mets_task_status[0] == "FAILURE"):
            totalAIPs += 1
            response.append(
                {
                    "state": mets_task_status,
                    "package": "METS.{}.xml".format(package_uuid),
                    "totalAIPs": totalAIPs,
                }
            )
            obj = get_mets_tasks.query.filter_by(get_mets_task_id=task_id).first()
            obj.status = mets_task_status
            db.session.commit()
    if len(mets_tasks) != 0:
        return jsonify(response)
    if totalAIPs == 0:
        response = {"state": "PENDING"}
        return jsonify(response)
    downloadEnd = datetime.now().replace(microsecond=0)
    obj = FetchJob.query.filter_by(id=fetchJobId).first()
    start = obj.download_start
    downloadStart = _format_date(start)
    obj.download_end = downloadEnd
    db.session.commit()
    response = {"state": "COMPLETED"}
    flash("Fetch Job {} completed".format(downloadStart))
    return jsonify(response)
