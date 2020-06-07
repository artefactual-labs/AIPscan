from flask import Flask, render_template, flash, redirect, request, session, jsonify
from AIPscan import app, db
from .models import fetch_jobs, storage_services, aips, files
from .forms import StorageServiceForm
from .am_ss_requests import storage_service_request
from .mets_2_sql import parse_mets
import os
import shutil
from datetime import datetime
from collections import Counter
from . import tasks

# AIPscan/add_sample_data.py is excluded from the code repository for
# security reasons. See more info below at @app.route("/add_sample_data")
# from .add_sample_data import adddata


@app.route("/task1")
def task1():
    result = tasks.add_together.delay(10, 20)
    print(result.wait())
    return "Welcome to task1!"


@app.route("/", methods=["GET"])
def ss_default():
    storageService = storage_services.query.filter_by(default=True).first()
    if storageService is None:
        storageService = storage_services.query.first()
        if storageService is None:
            return redirect("/storage_services")
    metsFetchJobs = fetch_jobs.query.filter_by(
        storage_service_id=storageService.id
    ).all()
    return render_template(
        "storage_service.html",
        storageService=storageService,
        metsFetchJobs=metsFetchJobs,
    )


@app.route("/storage_service/<id>", methods=["GET"])
def storage_service(id):
    storageService = storage_services.query.get(id)
    metsFetchJobs = fetch_jobs.query.filter_by(storage_service_id=id).all()
    return render_template(
        "storage_service.html",
        storageService=storageService,
        metsFetchJobs=metsFetchJobs,
    )


@app.route("/storage_services", methods=["GET"])
def ss():
    storageServices = storage_services.query.all()
    return render_template("storage_services.html", storageServices=storageServices)


@app.route("/edit_storage_service/<id>", methods=["GET", "POST"])
def edit_storage_service(id):
    form = StorageServiceForm()
    storageService = storage_services.query.get(id)
    if request.method == "GET":
        form.name.data = storageService.name
        form.url.data = storageService.url
        form.user_name.data = storageService.user_name
        form.api_key.data = storageService.api_key
        form.default.data = storageService.default
    if form.validate_on_submit():
        storageService.name = form.name.data
        storageService.url = form.url.data
        storageService.user_name = form.user_name.data
        storageService.api_key = form.api_key.data
        if form.default.data is True:
            storageServices = storage_services.query.all()
            for ss in storageServices:
                ss.default = False
        storageService.default = form.default.data
        db.session.commit()
        flash("Storage service {} updated".format(form.name.data))
        return redirect("/storage_services")
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@app.route("/new_storage_service", methods=["GET", "POST"])
def new_storage_service():
    form = StorageServiceForm()
    if form.validate_on_submit():
        ss = storage_services(
            name=form.name.data,
            url=form.url.data,
            user_name=form.user_name.data,
            api_key=form.api_key.data,
            default=form.default.data,
        )
        db.session.add(ss)
        db.session.commit()
        flash("New storage service {} created".format(form.name.data))
        return redirect("/storage_services")
    return render_template(
        "edit_storage_service.html", title="Storage Service", form=form
    )


@app.route("/delete_storage_service/<id>", methods=["GET"])
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
    return redirect("/storage_services")


@app.route("/new_fetch_job/<id>", methods=["GET"])
def new_fetch_job(id):
    storageService = storage_services.query.get(id)
    fetchJob = storage_service_request(
        storageService.url, storageService.user_name, storageService.api_key, id
    )
    flash("New METS fetch job {} created".format(fetchJob.download_start))
    dateTimeObjStart = datetime.now().replace(microsecond=0)
    parse_mets(fetchJob)
    flash("METS files parsed")
    dateTimeObjEnd = datetime.now().replace(microsecond=0)
    fetch_jobs.query.filter_by(id=fetchJob.id).update(
        {"parse_start": dateTimeObjStart, "parse_end": dateTimeObjEnd}
    )
    db.session.commit()
    return redirect("/storage_service/{}".format(id))


@app.route("/delete_fetch_job/<id>", methods=["GET"])
def delete_fetch_job(id):
    fetchJob = fetch_jobs.query.get(id)
    storageService = storage_services.query.get(fetchJob.storage_service_id)
    if os.path.exists(fetchJob.download_directory):
        shutil.rmtree(fetchJob.download_directory)
    db.session.delete(fetchJob)
    db.session.commit()
    flash("Fetch job {} is deleted".format(fetchJob.download_start))
    return redirect("/storage_service/{}".format(storageService.id))


@app.route("/view_fetch_jobs", methods=["GET"])
def view_fetch_jobs():
    metsFetchJobs = fetch_jobs.query.all()
    return render_template("view_fetch_jobs.html", metsFetchJobs=metsFetchJobs)


@app.route("/view_aips/<id>", methods=["GET"])
def view_aips(id):
    metsFetchJob = fetch_jobs.query.get(id)
    storageService = storage_services.query.get(metsFetchJob.storage_service_id)
    AIPs = aips.query.filter_by(fetch_job_id=metsFetchJob.id).all()

    formatLabels = []
    originalsCount = 0
    for aip in AIPs:
        originals = files.query.filter_by(aip_id=aip.id, type="original").all()
        for original in originals:
            formatLabels.append(original.format)
            originalsCount += 1
    formatCounts = Counter(formatLabels)
    labels = list(formatCounts.keys())
    values = list(formatCounts.values())

    return render_template(
        "view_aips.html",
        metsFetchJob=metsFetchJob,
        storageService=storageService,
        AIPs=AIPs,
        labels=labels,
        values=values,
        originalsCount=originalsCount,
    )


@app.route("/view_aip/<id>", methods=["GET"])
def view_aip(id):
    aip = aips.query.get(id)
    fetchJob = fetch_jobs.query.get(aip.fetch_job_id)
    storageService = storage_services.query.get(fetchJob.storage_service_id)
    originals = files.query.filter_by(aip_id=aip.id, type="original").all()
    preservationCopies = files.query.filter_by(aip_id=aip.id, type="preservation").all()

    formatLabels = []
    for original in originals:
        formatLabels.append(original.format)
    formatCounts = Counter(formatLabels)
    labels = list(formatCounts.keys())
    values = list(formatCounts.values())

    return render_template(
        "view_aip.html",
        aip=aip,
        fetchJob=fetchJob,
        storageService=storageService,
        originals=originals,
        preservationCopies=preservationCopies,
        labels=labels,
        values=values,
    )


@app.route("/report_file_formats/<id>", methods=["GET"])
def report_file_formats(id):
    if session.get("formats_startdate"):
        startdate = session.get("formats_startdate")
        session["formats_startdate"] = ""
    else:
        startdate = ""
    if session.get("formats_enddate"):
        enddate = session.get("formats_enddate")
        session["formats_enddate"] = ""
    else:
        enddate = ""

    metsFetchJob = fetch_jobs.query.get(id)
    storageService = storage_services.query.get(metsFetchJob.storage_service_id)
    AIPs = aips.query.filter_by(fetch_job_id=metsFetchJob.id).all()

    formatLabels = []
    originalsCount = 0
    for aip in AIPs:
        if startdate != "":
            originals = (
                files.query.filter_by(aip_id=aip.id, type="original")
                .filter(files.ingestion_date.between(startdate, enddate))
                .all()
            )
        else:
            originals = files.query.filter_by(aip_id=aip.id, type="original").all()

        for original in originals:
            formatLabels.append(original.format)
            originalsCount += 1
    formatCounts = Counter(formatLabels)

    return render_template(
        "report_file_formats.html",
        metsFetchJob=metsFetchJob,
        storageService=storageService,
        AIPs=AIPs,
        formatCounts=formatCounts,
        originalsCount=originalsCount,
        startdate=startdate,
        enddate=enddate,
    )


@app.route("/report_file_formats_range", methods=["GET"])
def report_file_format_range():
    startdate = request.args.get("startdate")
    enddate = request.args.get("enddate")
    session["formats_startdate"] = startdate
    session["formats_enddate"] = enddate

    return jsonify({"status": "success"})


@app.route("/add_sample_data", methods=["GET"])
def add_sample_data():
    """
    This function requires a file at 'AIPscan/add_sample_data.py'
    This file is excluded from code commits for security. Contents of the file
    are below. Add more ss# and fetch# tuples to add more sample data. Then run
    http://[root]/add_sample_data to populate the database.

    from AIPscan import db
    from .models import fetch_jobs, storage_services
    from datetime import datetime


    def adddata():
        ss1 = storage_services(
            name="Artefactual AMdemo 1.11",
            url="https://amdemo.artefactual.com:8000",
            user_name="test",
            api_key="cfbb2ae9677d80eac64c40f10ec84b865b4b4bc2",
            default=True,
        )
        fetch1 = fetch_jobs(
            total_packages="3",
            total_aips="1",
            download_start=datetime(2020, 4, 7, 16, 10, 51),
            download_end=datetime(2020, 4, 7, 16, 10, 54),
            download_directory="downloads/2020-04-07--16:10:51/",
            storage_service_id="1",
        )
        db.session.add(ss1)
        db.session.add(fetch1)
        db.session.commit()
        return ()
    adddata()
    """
    return render_template("add_sample_data.html")
