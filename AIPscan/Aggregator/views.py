from flask import Blueprint, render_template, redirect, request, flash, url_for
from AIPscan.models import fetch_jobs, storage_services
from AIPscan.Aggregator.forms import StorageServiceForm
from AIPscan.Aggregator import tasks
from AIPscan import db, app
import os
import shutil

aggregator = Blueprint("aggregator", __name__, template_folder="templates")


@aggregator.route("/task1")
def task1():
    result = tasks.add_together.delay(10, 20)
    print(result.wait())
    return "Welcome to task1!"


@app.route("/")
@aggregator.route("/", methods=["GET"])
def ss_default():
    storageService = storage_services.query.filter_by(default=True).first()
    if storageService is None:
        storageService = storage_services.query.first()
        if storageService is None:
            return redirect("storage_services")
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
