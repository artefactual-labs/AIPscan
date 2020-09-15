# -*- coding: utf-8 -*-

"""Views contains the primary routes for navigation around AIPscan's
Reporter module. Reports themselves as siphoned off into separate module
files with singular responsibility for a report.
"""

from datetime import datetime

from flask import render_template

# from AIPscan import db
from AIPscan.helpers import get_human_readable_file_size
from AIPscan.models import aips, originals, events, copies, fetch_jobs, storage_services
from AIPscan.Reporter import reporter

# Flask's idiom requires code using routing decorators to be imported
# up-front. But that means it might not be called directly by a module.
from AIPscan.Reporter import (  # noqa: F401
    report_aip_contents,
    report_formats_count,
    report_originals_with_derivatives,
)


@reporter.route("/view_aips/", methods=["GET"])
@reporter.route("/view_aips/<storage_service_id>", methods=["GET"])
def view_aips(storage_service_id=0):
    """View aips returns a standard page in AIPscan that provides an
    overview of the AIPs in a given storage service.
    """
    DEFAULT_STORAGE_SERVICE_ID = 1
    storage_services_ = {}
    storage_id = int(storage_service_id)
    if storage_id == 0 or storage_id is None:
        storage_id = DEFAULT_STORAGE_SERVICE_ID
    storage_service = storage_services.query.get(storage_id)
    if storage_service:
        aips_ = aips.query.filter_by(storage_service_id=storage_service.id).all()
        aips_count = len(aips_)
        storage_services_ = storage_services.query.all()
    else:
        aips_ = None
        aips_count = 0
    return render_template(
        "view_aips.html",
        storageServices=storage_services_,
        storageServiceId=storage_id,
        totalAIPs=aips_count,
        AIPs=aips_,
    )


# Picturae TODO: Does this work with AIP UUID as well?
@reporter.route("/view_aip/<aip_id>", methods=["GET"])
def view_aip(aip_id):
    """View aip returns a standard page in AIPscan that provides a more
    detailed view of a specific AIP given an AIPs ID.
    """
    aip = aips.query.get(aip_id)
    fetch_job = fetch_jobs.query.get(aip.fetch_job_id)
    storage_service = storage_services.query.get(fetch_job.storage_service_id)
    total_aips = aips.query.filter_by(storage_service_id=storage_service.id).count()
    original = originals.query.filter_by(aip_id=aip.id).all()

    return render_template(
        "view_aip.html",
        aip=aip,
        fetchJob=fetch_job,
        storageService=storage_service,
        totalAIPs=total_aips,
        originals=original,
    )


@reporter.route("/view_original/<original_file_id>", methods=["GET"])
def view_original(original_file_id):
    """View copy returns a standard page in AIPscan that provides a
    detailed view of a an original file within a given AIP.
    """
    original = originals.query.get(original_file_id)
    original_events = events.query.filter_by(id=original_file_id).all()
    size = get_human_readable_file_size(original.size)
    aip = aips.query.get(original.aip_id)
    copy = copies.query.filter_by(uuid=original.related_uuid).first()
    return render_template(
        "view_original.html",
        original=original,
        original_events=original_events,
        copy=copy,
        aip=aip,
        size=size,
    )


@reporter.route("/view_copy/<preservation_copy_id>", methods=["GET"])
def view_copy(preservation_copy_id):
    """View copy returns a standard page in AIPscan that provides a
    detailed view of a preservation copy within a given AIP.
    """
    copy = copies.query.filter_by(uuid=preservation_copy_id).first()
    size = get_human_readable_file_size(copy.size)
    original = originals.query.filter_by(uuid=copy.related_uuid).first()
    aip = aips.query.get(copy.aip_id)
    return render_template(
        "view_copy.html", copy=copy, original=original, aip=aip, size=size
    )


@reporter.route("/reports/", methods=["GET"])
def reports():
    """Reports returns a standard page in AIPscan that lists the
    in-built reports available to the caller.
    """
    all_storage_services = storage_services.query.all()
    now = datetime.now()
    start_date = str(datetime(now.year, 1, 1))[:-9]
    end_date = str(datetime(now.year, now.month, now.day))[:-9]
    return render_template(
        "reports.html",
        storageServices=all_storage_services,
        startdate=start_date,
        enddate=end_date,
    )
