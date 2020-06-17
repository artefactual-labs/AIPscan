from flask import Blueprint, render_template, redirect, request, flash, url_for, jsonify
from AIPscan import db, app, celery
from AIPscan.models import fetch_jobs, storage_services
from AIPscan.Aggregator.forms import StorageServiceForm
from AIPscan.Aggregator import tasks
import os
import shutil
from datetime import datetime
from celery.result import AsyncResult
import sqlite3

aggregator = Blueprint("aggregator", __name__, template_folder="templates")


@app.route("/")
@aggregator.route("/", methods=["GET"])
def ss_default():
    storageService = storage_services.query.filter_by(default=True).first()
    if storageService is None:
        storageService = storage_services.query.first()
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
    storageServices = storage_services.query.all()
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
    timestampStr = dateTimeObjStart.strftime("%Y-%m-%d--%H-%M-%S")
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

    # send the METS fetch job to a background job that will coordinate other workers
    task = tasks.workflow_coordinator.delay(apiUrl, timestampStr, fetchJob.id)

    """
    # this only works on the first try, after that Flask is not able to get task info from Celery
    # the compromise is to write the task ID from the Celery worker to its SQLite backend

    coordinator_task = tasks.workflow_coordinator.AsyncResult(task.id, app=celery)
    taskId = coordinator_task.info.get("package_lists_taskId")
    response = {"timestamp": timestamp, "taskId": taskId}
    """

    celerydb = sqlite3.connect("celerytasks.db")
    cursor = celerydb.cursor()
    sql = "SELECT package_task_id FROM package_tasks WHERE workflow_coordinator_id = ?"
    # run a while loop in case the workflow coordinator task hasn't finished writing to dbase yet
    while True:
        cursor.execute(
            sql, (task.id,),
        )
        taskId = cursor.fetchone()
        if taskId is not None:
            break

    # send response back to Javascript function that was triggered by the 'New Fetch Job' button
    response = {"timestamp": timestamp, "taskId": taskId}
    return jsonify(response)


@aggregator.route("/task_status/<taskid>")
def task_status(taskid):
    task = tasks.package_lists_request.AsyncResult(taskid, app=celery)
    if task.state == "PENDING":
        # job did not start yet
        response = {
            "state": task.state,
        }
    elif task.state != "FAILURE":
        if task.state == "SUCCESS":
            response = {
                "state": task.state,
            }
        else:
            response = {"state": task.state, "message": task.info.get("message")}
    else:
        # something went wrong in the background job
        response = {
            "state": task.state,
            "status": str(task.info),  # this is the exception raised
        }
    return jsonify(response)
