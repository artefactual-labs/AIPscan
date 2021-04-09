# -*- coding: utf-8 -*-

"""Views contains the primary routes for navigation around AIPscan's
Reporter module. Reports themselves as siphoned off into separate module
files with singular responsibility for a report.
"""

from datetime import datetime

from flask import render_template, request

from AIPscan.models import AIP, Event, FetchJob, File, FileType, StorageService

# Flask's idiom requires code using routing decorators to be imported
# up-front. But that means it might not be called directly by a module.
from AIPscan.Reporter import (  # noqa: F401
    report_aip_contents,
    report_aips_by_format,
    report_aips_by_puid,
    report_bayesian_modeling,
    report_format_versions_count,
    report_formats_count,
    report_ingest_log,
    report_largest_files,
    report_originals_with_derivatives,
    reporter,
    request_params,
    sort_puids,
)


def _get_storage_service(storage_service_id):
    """Get Storage Service from specified ID.

    If the requested Storage Service ID is invalid, return (in order of
    preference) one of the following:
    - First default Storage Service
    - First Storage Service
    - None

    :param storage_service_id: Storage Service ID

    :returns: StorageService object or None
    """
    storage_service = StorageService.query.get(storage_service_id)
    if storage_service is None:
        storage_service = StorageService.query.filter_by(default=True).first()
    if storage_service is None:
        storage_service = StorageService.query.first()
    return storage_service


@reporter.route("/aips/", methods=["GET"])
@reporter.route("/aips/<storage_service_id>", methods=["GET"])
def view_aips(storage_service_id=0):
    """View aips returns a standard page in AIPscan that provides an
    overview of the AIPs in a given storage service.
    """
    DEFAULT_STORAGE_SERVICE_ID = 1
    storage_services = {}
    storage_id = int(storage_service_id)
    if storage_id == 0 or storage_id is None:
        storage_id = DEFAULT_STORAGE_SERVICE_ID
    storage_service = StorageService.query.get(storage_id)
    if storage_service:
        aips = AIP.query.filter_by(storage_service_id=storage_service.id).all()
        aips_list = []
        for aip in aips:
            aip_info = {}
            aip_info["id"] = aip.id
            aip_info["transfer_name"] = aip.transfer_name
            aip_info["uuid"] = aip.uuid
            aip_info["create_date"] = aip.create_date
            aip_info["originals_count"] = aip.original_file_count
            aip_info["copies_count"] = aip.preservation_file_count
            aips_list.append(aip_info)

        aips_count = len(aips)
        storage_services = StorageService.query.all()
    else:
        aips_list = []
        aips_count = 0
    return render_template(
        "aips.html",
        storage_services=storage_services,
        storage_service_id=storage_id,
        aips_count=aips_count,
        aips=aips_list,
    )


# Picturae TODO: Does this work with AIP UUID as well?
@reporter.route("/aip/<aip_id>", methods=["GET"])
def view_aip(aip_id):
    """View aip returns a standard page in AIPscan that provides a more
    detailed view of a specific AIP given an AIPs ID.
    """
    aip = AIP.query.get(aip_id)
    fetch_job = FetchJob.query.get(aip.fetch_job_id)
    storage_service = StorageService.query.get(fetch_job.storage_service_id)
    aips_count = AIP.query.filter_by(storage_service_id=storage_service.id).count()
    original_file_count = aip.original_file_count
    preservation_file_count = aip.preservation_file_count
    originals = []
    original_files = File.query.filter_by(
        aip_id=aip.id, file_type=FileType.original
    ).all()
    for file_ in original_files:
        original = {}
        original["id"] = file_.id
        original["name"] = file_.name
        original["uuid"] = file_.uuid
        original["size"] = file_.size
        original["date_created"] = file_.date_created.strftime("%Y-%m-%d")
        original["puid"] = file_.puid
        original["file_format"] = file_.file_format
        original["format_version"] = file_.format_version
        preservation_file = File.query.filter_by(
            file_type=FileType.preservation, original_file_id=file_.id
        ).first()
        if preservation_file is not None:
            original["preservation_file_id"] = preservation_file.id
        originals.append(original)

    return render_template(
        "aip.html",
        aip=aip,
        storage_service=storage_service,
        aips_count=aips_count,
        originals=originals,
        original_file_count=original_file_count,
        preservation_file_count=preservation_file_count,
    )


@reporter.route("/file/<file_id>", methods=["GET"])
def view_file(file_id):
    """File page displays Object and Event metadata for file"""
    file_ = File.query.get(file_id)
    aip = AIP.query.get(file_.aip_id)
    events = Event.query.filter_by(file_id=file_id).all()
    preservation_file = File.query.filter_by(
        file_type=FileType.preservation, original_file_id=file_.id
    ).first()

    original_filename = None
    if file_.original_file_id is not None:
        original_file = File.query.get(file_.original_file_id)
        original_filename = original_file.name

    return render_template(
        "file.html",
        file_=file_,
        aip=aip,
        events=events,
        preservation_file=preservation_file,
        original_filename=original_filename,
    )


@reporter.route("/reports/", methods=["GET"])
def reports():
    """Reports page lists available built-in reports

    Storage Service ID can be specified as an optional parameter. If
    one is not specified, use the default Storage Service.
    """
    storage_service_id = request.args.get(request_params["storage_service_id"])
    storage_service = _get_storage_service(storage_service_id)

    original_file_formats = []
    preservation_file_formats = []
    original_puids = []
    preservation_puids = []

    # Original file formats and PUIDs should be present for any Storage
    # Service with ingested files.
    try:
        original_file_formats = storage_service.unique_original_file_formats
        original_puids = sort_puids(storage_service.unique_original_puids)
    except AttributeError:
        pass

    # Preservation file formats and PUIDs may be present depending on
    # a number of factors such as processing configuration choices,
    # normalization rules, and use of manual normalization.
    try:
        preservation_file_formats = storage_service.unique_preservation_file_formats
    except AttributeError:
        pass
    try:
        preservation_puids = sort_puids(storage_service.unique_preservation_puids)
    except AttributeError:
        pass

    now = datetime.now()
    start_date = str(datetime(now.year, 1, 1))[:-9]
    end_date = str(datetime(now.year, now.month, now.day))[:-9]

    return render_template(
        "reports.html",
        storage_service=storage_service,
        storage_services=StorageService.query.all(),
        original_file_formats=original_file_formats,
        preservation_file_formats=preservation_file_formats,
        original_puids=original_puids,
        preservation_puids=preservation_puids,
        start_date=start_date,
        end_date=end_date,
    )
