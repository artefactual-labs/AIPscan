from flask import Flask, render_template
from AIPscope import app, db
from .models import fetch_jobs, storage_services
from .add_sample_data import adddata


@app.route("/", methods=["GET"])
def ss_default():
    storageService = storage_services.query.filter_by(default=True).first()
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


@app.route("/view_aips", methods=["GET"])
def view_aips():
    metsFetchJobs = fetch_jobs.query.all()
    return render_template("view_aips.html", metsFetchJobs=metsFetchJobs)


@app.route("/add_sample_data", methods=["GET"])
def add_sample_data():
    adddata()
    return render_template("add_sample_data.html")
