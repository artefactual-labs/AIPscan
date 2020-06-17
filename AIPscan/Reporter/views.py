from flask import Blueprint, render_template
from AIPscan import db
from AIPscan.models import aips, files, fetch_jobs, storage_services
from collections import Counter

reporter = Blueprint("reporter", __name__, template_folder="templates")


@reporter.route("/view_aips/<id>", methods=["GET"])
def view_aips(id):
    storageService = storage_services.query.get(id)
    AIPs = aips.query.filter_by(storage_service_id=id).all()
    totalAIPs = aips.query.filter_by(storage_service_id=id).count()

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
        storageService=storageService,
        totalAIPs=totalAIPs,
        AIPs=AIPs,
        labels=labels,
        values=values,
        originalsCount=originalsCount,
    )
