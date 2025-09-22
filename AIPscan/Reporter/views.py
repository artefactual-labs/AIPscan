"""Views contains the primary routes for navigation around AIPscan's
Reporter module. Reports themselves as siphoned off into separate module
files with singular responsibility for a report.
"""

from datetime import datetime

import requests
from flask import Response
from flask import abort
from flask import current_app
from flask import jsonify
from flask import make_response
from flask import render_template
from flask import request
from flask import session

from AIPscan import db
from AIPscan.Aggregator.task_helpers import get_mets_url
from AIPscan.models import AIP
from AIPscan.models import Event
from AIPscan.models import FetchJob
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.models import Pipeline
from AIPscan.models import StorageLocation
from AIPscan.models import StorageService

# Flask's idiom requires code using routing decorators to be imported
# up-front. But that means it might not be called directly by a module.
from AIPscan.Reporter import report_aip_contents  # noqa: F401
from AIPscan.Reporter import report_aips_by_format  # noqa: F401
from AIPscan.Reporter import report_aips_by_puid  # noqa: F401
from AIPscan.Reporter import report_format_versions_count  # noqa: F401
from AIPscan.Reporter import report_formats_count  # noqa: F401
from AIPscan.Reporter import report_ingest_log  # noqa: F401
from AIPscan.Reporter import report_largest_aips  # noqa: F401
from AIPscan.Reporter import report_largest_files  # noqa: F401
from AIPscan.Reporter import report_preservation_derivatives  # noqa: F401
from AIPscan.Reporter import report_storage_locations  # noqa: F401
from AIPscan.Reporter import reporter  # noqa: F401
from AIPscan.Reporter import request_params  # noqa: F401
from AIPscan.Reporter import sort_puids  # noqa: F401
from AIPscan.Reporter.database_helpers import get_possible_storage_locations
from AIPscan.Reporter.helpers import calculate_paging_window
from AIPscan.Reporter.helpers import remove_dict_none_values


def _get_default_storage_service():
    """Return the default StorageService if present, otherwise the first one or None."""
    storage_service = StorageService.query.filter_by(default=True).first()
    if storage_service is None:
        storage_service = StorageService.query.first()
    return storage_service


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
    if not storage_service_id:
        return _get_default_storage_service()

    storage_service = db.session.get(StorageService, storage_service_id)
    if storage_service is None:
        storage_service = _get_default_storage_service()

    return storage_service


def _get_storage_location(storage_location_id):
    """Return Storage Location or None."""
    if not storage_location_id:
        return None
    return db.session.get(StorageLocation, storage_location_id)


def storage_locations_with_aips(storage_locations):
    """Return list of Storage Locations filtered to those with AIPs."""
    return [loc for loc in storage_locations if loc.aips]


def get_aip_pager(page, per_page, storage_service, **kwargs):
    storage_service_id = None
    if storage_service is not None:
        storage_service_id = storage_service.id

    storage_location_id = None
    if kwargs.get("storage_location", None):
        storage_location_id = kwargs["storage_location"].id

    query = kwargs.get("query", None)

    aips = AIP.query

    # Filter by storage service
    aips = aips.filter_by(storage_service_id=storage_service_id)

    # Optionally filter by storage location
    if storage_location_id:
        aips = aips.filter_by(storage_location_id=storage_location_id)

    # Optionally filter by text search
    if query is not None:
        aips = aips.filter(
            AIP.uuid.like(f"%{query}%")
            | AIP.transfer_name.like(f"%{query}%")
            | AIP.create_date.like(f"%{query}%")
        )

    pager = aips.paginate(page=page, per_page=per_page, error_out=False)

    return pager


def get_file_pager(page, per_page, aip):
    try:
        page = int(page)
    except ValueError:
        page = 1

    return File.query.filter_by(aip_id=aip.id, file_type=FileType.original).paginate(
        page=page, per_page=per_page, error_out=False
    )


@reporter.route("/aips/", methods=["GET"])
def view_aips():
    """Overview of AIPs in given Storage Service and Location."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_service = _get_storage_service(storage_service_id)

    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    try:
        storage_location = _get_storage_location(storage_location_id)
    except Exception:
        current_app.logger.exception(
            f"Failed to get storage location id={storage_location_id}"
        )

    query = request.args.get("query", "")

    try:
        page = int(request.args.get(request_params.PAGE, default=1))
    except ValueError:
        page = 1

    pager = get_aip_pager(
        page, 10, storage_service, storage_location=storage_location, query=query
    )

    first_item, last_item = calculate_paging_window(pager)

    state_query_params = {
        request_params.STORAGE_SERVICE_ID: storage_service_id,
        request_params.STORAGE_LOCATION_ID: storage_location_id,
    }

    return render_template(
        "aips.html",
        storage_services=StorageService.query.all(),
        storage_service=storage_service,
        storage_locations=storage_locations_with_aips(
            get_possible_storage_locations(storage_service)
        ),
        storage_location=storage_location,
        pager=pager,
        first_item=first_item,
        last_item=last_item,
        state_query_params=remove_dict_none_values(state_query_params),
    )


# Picturae TODO: Does this work with AIP UUID as well?
@reporter.route("/aip/<aip_id>", methods=["GET"])
def view_aip(aip_id):
    """Detailed view of specific AIP."""
    aip = db.session.get(AIP, aip_id)

    if aip is None:
        abort(404)

    fetch_job = db.session.get(FetchJob, aip.fetch_job_id)
    storage_service = db.session.get(StorageService, fetch_job.storage_service_id)
    storage_location = db.session.get(StorageLocation, aip.storage_location_id)
    aips_count = AIP.query.filter_by(storage_service_id=storage_service.id).count()
    original_file_count = aip.original_file_count
    preservation_file_count = aip.preservation_file_count
    origin_pipeline = db.session.get(Pipeline, aip.origin_pipeline_id)

    originals = []

    page = request.args.get(request_params.PAGE, default="1")
    pager = get_file_pager(page, 10, aip)

    first_item, last_item = calculate_paging_window(pager)

    for file_ in pager.items:
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
        first_item=first_item,
        last_iten=last_item,
        pager=pager,
        storage_service=storage_service,
        storage_location=storage_location,
        aips_count=aips_count,
        originals=originals,
        original_file_count=original_file_count,
        preservation_file_count=preservation_file_count,
        origin_pipeline=origin_pipeline,
    )


@reporter.route("/file/<file_id>", methods=["GET"])
def view_file(file_id):
    """File page displays Object and Event metadata for file"""
    file_ = db.session.get(File, file_id)

    if file_ is None:
        abort(404)

    aip = db.session.get(AIP, file_.aip_id)
    events = Event.query.filter_by(file_id=file_id).all()
    preservation_file = File.query.filter_by(
        file_type=FileType.preservation, original_file_id=file_.id
    ).first()

    original_filename = None
    if file_.original_file_id is not None:
        original_file = db.session.get(File, file_.original_file_id)
        original_filename = original_file.name

    return render_template(
        "file.html",
        file_=file_,
        premisxml=file_.get_premis_xml_lines(),
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
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_service = _get_storage_service(storage_service_id)

    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    storage_location = _get_storage_location(storage_location_id)

    original_file_formats = []
    preservation_file_formats = []
    original_puids = []
    preservation_puids = []

    # Filter dropdowns by Storage Location if one is selected. If a location is
    # not selected, populate dropdowns from Storage Service instead.
    if storage_location:
        # Original file formats and PUIDs should be present for any Storage
        # Loocation with ingested files.
        try:
            original_file_formats = storage_location.unique_original_file_formats
            original_puids = sort_puids(storage_location.unique_original_puids)
        except AttributeError:
            pass

        # Preservation file formats and PUIDs may be present depending on
        # a number of factors such as processing configuration choices,
        # normalization rules, and use of manual normalization.
        try:
            preservation_file_formats = (
                storage_location.unique_preservation_file_formats
            )
        except AttributeError:
            pass
        try:
            preservation_puids = sort_puids(storage_location.unique_preservation_puids)
        except AttributeError:
            pass

    else:
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

    if "start_date" not in session:
        earliest_aip_created = storage_service.earliest_aip_created
        session["start_date"] = earliest_aip_created.strftime("%Y-%m-%d")

    if "end_date" not in session:
        now = datetime.now()
        session["end_date"] = str(datetime(now.year, now.month, now.day))[:-9]

    return render_template(
        "reports.html",
        storage_service=storage_service,
        storage_services=StorageService.query.all(),
        storage_location=storage_location,
        storage_locations=storage_locations_with_aips(
            get_possible_storage_locations(storage_service)
        ),
        original_file_formats=original_file_formats,
        preservation_file_formats=preservation_file_formats,
        original_puids=original_puids,
        preservation_puids=preservation_puids,
        start_date=session["start_date"],
        end_date=session["end_date"],
    )


@reporter.route("/update_dates/", methods=["POST"])
def update_dates():
    if request.json and request.json.get("start_date"):
        req = request.get_json()
        session["start_date"] = request.json.get("start_date")
        return make_response(jsonify(req), 200)

    if request.json and request.json.get("end_date"):
        req = request.get_json()
        session["end_date"] = request.json.get("end_date")
        return make_response(jsonify(req), 200)


@reporter.route("/download_mets/<aip_id>", methods=["GET"])
def download_mets(aip_id):
    aip = db.session.get(AIP, aip_id)
    storage_service = db.session.get(StorageService, aip.storage_service_id)

    mets_response = requests.get(
        get_mets_url(
            storage_service,
            aip.uuid,
            f"{aip.transfer_name}-{aip.uuid}/data/METS.{aip.uuid}.xml",
        )
    )

    headers = {
        "Content-Disposition": f'attachment; filename="METS-{aip.uuid}.xml"',
        "Content-length": len(mets_response.content),
    }
    return Response(mets_response.content, mets_response.status_code, headers)
