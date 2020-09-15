# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, redirect, request, flash, url_for, jsonify
from AIPscan import db, app, celery

from AIPscan.models import (
    fetch_jobs,
    storage_services,
    # Custom celery Models.
    package_tasks,
    get_mets_tasks,
)

from AIPscan.Aggregator.task_helpers import get_packages_directory

from AIPscan.Aggregator.forms import StorageServiceForm
from AIPscan.Aggregator import tasks
import os
import shutil
from datetime import datetime
from celery.result import AsyncResult

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


@app.route("/")
@aggregator.route("/", methods=["GET"])
def ss_default():
    # load the default storage service
    storageService = storage_services.query.filter_by(default=True).first()
    if storageService is None:
        # no default is set, retrieve the first storage service
        storageService = storage_services.query.first()
        # there are no storage services defined at all
        if storageService is None:
            return redirect(url_for("aggregator.ss"))
    metsFetchJobs = fetch_jobs.query.filter_by(
        storage_service_id=storageService.id
    ).all()
    return render_template(
        "storage_service.html",
        storageService=storageService,
        metsFetchJobs=metsFetchJobs,
    )


@aggregator.route("/storage_service/<id>", methods=["GET"])
def storage_service(id):
    storageService = storage_services.query.get(id)
    metsFetchJobs = fetch_jobs.query.filter_by(storage_service_id=id).all()
    return render_template(
        "storage_service.html",
        storageService=storageService,
        metsFetchJobs=metsFetchJobs,
    )


@aggregator.route("/storage_services", methods=["GET"])
def ss():
    storageServices = storage_services.query.all()
    return render_template("storage_services.html", storageServices=storageServices)


@aggregator.route("/edit_storage_service/<id>", methods=["GET", "POST"])
def edit_storage_service(id):
    form = StorageServiceForm()
    storageService = storage_services.query.get(id)
    if request.method == "GET":
        form.name.data = storageService.name
        form.url.data = storageService.url
        form.user_name.data = storageService.user_name
        form.download_limit.data = storageService.download_limit
        form.download_offset.data = storageService.download_offset
        form.api_key.data = storageService.api_key
        form.default.data = storageService.default
    if form.validate_on_submit():
        storageService.name = form.name.data
        storageService.url = form.url.data
        storageService.user_name = form.user_name.data
        storageService.api_key = form.api_key.data
        storageService.download_limit = form.download_limit.data
        storageService.download_offset = form.download_offset.data
        if form.default.data is True:
            storageServices = storage_services.query.all()
            for ss in storageServices:
                ss.default = False
        storageService.default = form.default.data
        db.session.commit()
        flash("Storage service {} updated".format(form.name.data))
        return redirect(url_for("aggregator.ss"))
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@aggregator.route("/new_storage_service", methods=["GET", "POST"])
def new_storage_service():
    form = StorageServiceForm()
    if form.validate_on_submit():
        ss = storage_services(
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
        return redirect(url_for("aggregator.ss"))
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@aggregator.route("/delete_storage_service/<id>", methods=["GET"])
def delete_storage_service(id):
    storageService = storage_services.query.get(id)
    metsFetchJobs = fetch_jobs.query.filter_by(storage_service_id=id).all()
    for metsFetchJob in metsFetchJobs:
        if os.path.exists(metsFetchJob.download_directory):
            shutil.rmtree(metsFetchJob.download_directory)
    db.session.delete(storageService)
    db.session.commit()
    flash("Storage service '{}' is deleted".format(storageService.name))
    return redirect(url_for("aggregator.ss"))


@aggregator.route("/new_fetch_job/<id>", methods=["POST"])
def new_fetch_job(id):

    # this function is triggered by the Javascript attached to the "New Fetch Job" button

    storageService = storage_services.query.get(id)
    apiUrl = {
        "baseUrl": storageService.url,
        "userName": storageService.user_name,
        "apiKey": storageService.api_key,
        "offset": str(storageService.download_offset),
        "limit": str(storageService.download_limit),
    }

    # create "downloads/" directory if it doesn't exist
    if not os.path.exists("AIPscan/Aggregator/downloads/"):
        os.makedirs("AIPscan/Aggregator/downloads/")

    # create a subdirectory for the download job using a timestamp as its name
    dateTimeObjStart = datetime.now().replace(microsecond=0)
    timestampStr = dateTimeObjStart.strftime("%Y-%m-%d-%H-%M-%S")
    timestamp = dateTimeObjStart.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("AIPscan/Aggregator/downloads/" + timestampStr + "/packages/")
    os.makedirs("AIPscan/Aggregator/downloads/" + timestampStr + "/mets/")

    # create a fetch_job record in the aipscan database
    # write fetch job info to database
    fetchJob = fetch_jobs(
        total_packages=None,
        total_deleted_aips=None,
        total_aips=None,
        download_start=dateTimeObjStart,
        download_end=None,
        download_directory="AIPscan/Aggregator/downloads/" + timestampStr + "/",
        storage_service_id=storageService.id,
    )
    db.session.add(fetchJob)
    db.session.commit()

    packages_directory = get_packages_directory(timestampStr)

    # send the METS fetch job to a background job that will coordinate other workers
    task = tasks.workflow_coordinator.delay(
        apiUrl, timestampStr, storageService.id, fetchJob.id, packages_directory
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
    response = {"timestamp": timestamp, "taskId": task_id, "fetchJobId": fetchJob.id}
    return jsonify(response)


@aggregator.route("/delete_fetch_job/<id>", methods=["GET"])
def delete_fetch_job(id):
    fetchJob = fetch_jobs.query.get(id)
    storageService = storage_services.query.get(fetchJob.storage_service_id)
    if os.path.exists(fetchJob.download_directory):
        shutil.rmtree(fetchJob.download_directory)
    db.session.delete(fetchJob)
    db.session.commit()
    flash("Fetch job {} is deleted".format(fetchJob.download_start))
    return redirect(url_for("aggregator.storage_service", id=storageService.id))


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
    obj = fetch_jobs.query.filter_by(id=fetchJobId).first()
    start = obj.download_start
    downloadStart = _format_date(start)
    obj.download_end = downloadEnd
    db.session.commit()
    response = {"state": "COMPLETED"}
    flash("Fetch Job {} completed".format(downloadStart))
    return jsonify(response)
