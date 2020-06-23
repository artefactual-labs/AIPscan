from flask import Blueprint, render_template
from AIPscan import db
from AIPscan.models import (
    aips,
    originals,
    events,
    agents,
    event_agents,
    copies,
    fetch_jobs,
    storage_services,
)
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
    totalAIPs = aips.query.filter_by(storage_service_id=storageService.id).count()
    original = originals.query.filter_by(aip_id=aip.id).all()

    return render_template(
        "view_aip.html",
        aip=aip,
        fetchJob=fetchJob,
        storageService=storageService,
        totalAIPs=totalAIPs,
        originals=original,
    )


@reporter.route("/view_copy/<uuid>", methods=["GET"])
def view_copy(uuid):
    copy = copies.query.filter_by(uuid=uuid).first()
    original = originals.query.filter_by(uuid=copy.related_uuid).first()
    aip = aips.query.get(copy.aip_id)

    return render_template("view_copy.html", copy=copy, original=original, aip=aip)


@reporter.route("/view_original/<id>", methods=["GET"])
def view_original(id):
    original = originals.query.get(id)
    original_events = events.query.filter_by(original_id=id).all()
    aip = aips.query.get(original.aip_id)
    copy = copies.query.filter_by(uuid=original.related_uuid).first()

    return render_template(
        "view_original.html",
        original=original,
        original_events=original_events,
        copy=copy,
        aip=aip,
    )
