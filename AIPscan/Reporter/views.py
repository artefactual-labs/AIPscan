from flask import Blueprint, render_template
from AIPscan import db
from AIPscan.models import aips, originals, fetch_jobs, storage_services
from collections import Counter

reporter = Blueprint("reporter", __name__, template_folder="templates")


@reporter.route("/view_aips/<id>", methods=["GET"])
def view_aips(id):
    storageService = storage_services.query.get(id)
    AIPs = aips.query.filter_by(storage_service_id=id).all()
    totalAIPs = aips.query.filter_by(storage_service_id=id).count()

    return render_template(
        "view_aips.html", storageService=storageService, totalAIPs=totalAIPs, AIPs=AIPs,
    )


@reporter.route("/view_aip/<id>", methods=["GET"])
def view_aip(id):
    aip = aips.query.get(id)
    fetchJob = fetch_jobs.query.get(aip.fetch_job_id)
    storageService = storage_services.query.get(fetchJob.storage_service_id)
    original = originals.query.filter_by(aip_id=aip.id).all()

    return render_template(
        "view_aip.html",
        aip=aip,
        fetchJob=fetchJob,
        storageService=storageService,
        originals=original,
    )


@reporter.route("/view_file/<id>", methods=["GET"])
def view_file(id):
    file = originals.query.get(id)
    aip = aips.query.get(file.aip_id)

    return render_template("view_file.html", file=file, aip=aip,)
