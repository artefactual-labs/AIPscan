from flask import Flask, render_template, flash, redirect, request
from AIPscan import app, db
from .models import fetch_jobs, storage_services
from .add_sample_data import adddata
from .forms import StorageServiceForm
from .am_ss_requests import storage_service_request
import os
import shutil


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
    flash("Storage service {} is deleted".format(storageService.name))
    db.session.delete(storageService)
    db.session.commit()
    storageServices = storage_services.query.all()
    return redirect("/storage_services")


@app.route("/new_fetch_job/<id>", methods=["GET"])
def new_fetch_job(id):
    storageService = storage_services.query.get(id)
    storage_service_request(
        storageService.url, storageService.user_name, storageService.api_key
    )
    flash("New METS fetch job created")
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


@app.route("/view_aips", methods=["GET"])
def view_aips():
    metsFetchJobs = fetch_jobs.query.all()
    return render_template("view_aips.html", metsFetchJobs=metsFetchJobs)


@app.route("/add_sample_data", methods=["GET"])
def add_sample_data():
    adddata()
    return render_template("add_sample_data.html")
