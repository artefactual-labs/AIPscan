# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request

# from AIPscan import db
from AIPscan.Data import data
from AIPscan.helpers import GetHumanReadableFilesize
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
from datetime import datetime, timedelta

reporter = Blueprint("reporter", __name__, template_folder="templates")


def translate_headers(headers):
    """Translate headers from something machine readable to something
    more user friendly and translatable.
    """
    field_lookup = {
        data.FIELD_AIP_NAME: "AIP Name",
        data.FIELD_AIPS: "AIPs",
        data.FIELD_AIP_SIZE: "Aip Size",
        data.FIELD_ALL_AIPS: "All Aips",
        data.FIELD_COUNT: "Count",
        data.FIELD_CREATED_DATE: "Created Date",
        data.FIELD_DERIVATIVE_COUNT: "Derivative Count",
        data.FIELD_DERIVATIVE_FORMAT: "Derivative Format",
        data.FIELD_DERIVATIVE_UUID: "Derivative UUID",
        data.FIELD_FILE_COUNT: "File Count",
        data.FIELD_FORMATS: "Formats",
        data.FIELD_NAME: "Name",
        data.FIELD_ORIGINAL_UUID: "Original UUID",
        data.FIELD_ORIGINAL_FORMAT: "Original Format",
        data.FIELD_RELATED_PAIRING: "Related Pairing",
        data.FIELD_STORAGE_NAME: "Storage Service Name",
        data.FIELD_TRANSFER_NAME: "Transfer Name",
        data.FIELD_VERSION: "Version",
    }
    return [field_lookup.get(header, header) for header in headers]


@reporter.route("/view_aips/", methods=["GET"])
@reporter.route("/view_aips/<storage_service_id>", methods=["GET"])
def view_aips(storage_service_id=0):
    """Provide an overview of the AIPs in the storage service."""
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
    size = GetHumanReadableFilesize(copy.size)
    original = originals.query.filter_by(uuid=copy.related_uuid).first()
    aip = aips.query.get(copy.aip_id)

    return render_template(
        "view_copy.html", copy=copy, original=original, aip=aip, size=size
    )


@reporter.route("/view_original/<id>", methods=["GET"])
def view_original(id):
    original = originals.query.get(id)
    original_events = events.query.filter_by(original_id=id).all()
    size = GetHumanReadableFilesize(original.size)
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


@reporter.route("/reports/", methods=["GET"])
def reports():
    storageServices = storage_services.query.all()

    now = datetime.now()
    startdate = str(datetime(now.year, 1, 1))[:-9]
    enddate = str(datetime(now.year, now.month, now.day))[:-9]

    return render_template(
        "reports.html",
        storageServices=storageServices,
        startdate=startdate,
        enddate=enddate,
    )


@reporter.route("/report_formats_count/", methods=["GET"])
def report_formats_count():
    startdate = request.args.get("startdate")
    enddate = request.args.get("enddate")
    # make date range inclusive
    start = datetime.strptime(startdate, "%Y-%m-%d")
    end = datetime.strptime(enddate, "%Y-%m-%d")
    daybefore = start - timedelta(days=1)
    dayafter = end + timedelta(days=1)

    storageServiceId = request.args.get("ssId")
    storageService = storage_services.query.get(storageServiceId)
    AIPs = aips.query.filter_by(storage_service_id=storageServiceId).all()

    formatCount = {}
    originalsCount = 0
    delta = timedelta(days=1)

    for aip in AIPs:
        originalFiles = originals.query.filter_by(aip_id=aip.id)
        for original in originalFiles:
            # Note that original files in packages do not have a PREMIS ingestion
            # event. Therefore "message digest calculation" is used to get the
            # ingest date for all originals. This event typically happens within
            # the same second or seconds of the ingestion event and is done for all files.
            ingestEvent = events.query.filter_by(
                original_id=original.id, type="message digest calculation"
            ).first()
            if ingestEvent.date < daybefore:
                continue
            elif ingestEvent.date > dayafter:
                continue
            else:
                format = original.format
                size = original.size
                originalsCount += 1

                if format in formatCount:
                    formatCount[format]["count"] += 1
                    if formatCount[format]["size"] != None:
                        formatCount[format]["size"] += size
                else:
                    formatCount.update({format: {"count": 1, "size": size}})

    totalSize = 0

    for key, value in formatCount.items():
        size = value["size"]
        if size != None:
            totalSize += size
            humanSize = GetHumanReadableFilesize(size)
            formatCount[key] = {
                "count": value["count"],
                "size": size,
                "humansize": humanSize,
            }

    differentFormats = len(formatCount.keys())
    totalHumanSize = GetHumanReadableFilesize(totalSize)

    return render_template(
        "report_formats_count.html",
        startdate=startdate,
        enddate=enddate,
        storageService=storageService,
        originalsCount=originalsCount,
        formatCount=formatCount,
        differentFormats=differentFormats,
        totalHumanSize=totalHumanSize,
    )


@reporter.route("/chart_formats_count/", methods=["GET"])
def chart_formats_count():
    startdate = request.args.get("startdate")
    enddate = request.args.get("enddate")
    # make date range inclusive
    start = datetime.strptime(startdate, "%Y-%m-%d")
    end = datetime.strptime(enddate, "%Y-%m-%d")
    daybefore = start - timedelta(days=1)
    dayafter = end + timedelta(days=1)

    storageServiceId = request.args.get("ssId")
    storageService = storage_services.query.get(storageServiceId)
    AIPs = aips.query.filter_by(storage_service_id=storageServiceId).all()

    formatLabels = []
    formatCounts = []
    originalsCount = 0

    for aip in AIPs:
        originalFiles = originals.query.filter_by(aip_id=aip.id)
        for original in originalFiles:
            # Note that original files in packages do not have a PREMIS ingestion
            # event. Therefore "message digest calculation" is used to get the
            # ingest date for all originals. This event typically happens within
            # the same second or seconds of the ingestion event and is done for all files.
            ingestEvent = events.query.filter_by(
                original_id=original.id, type="message digest calculation"
            ).first()
            if ingestEvent.date < daybefore:
                continue
            elif ingestEvent.date > dayafter:
                continue
            else:
                formatLabels.append(original.format)
                originalsCount += 1

    formatCounts = Counter(formatLabels)
    labels = list(formatCounts.keys())
    values = list(formatCounts.values())

    differentFormats = len(formatCounts.keys())

    return render_template(
        "chart_formats_count.html",
        startdate=startdate,
        enddate=enddate,
        storageService=storageService,
        labels=labels,
        values=values,
        originalsCount=originalsCount,
        differentFormats=differentFormats,
    )


@reporter.route("/plot_formats_count/", methods=["GET"])
def plot_formats_count():
    startdate = request.args.get("startdate")
    enddate = request.args.get("enddate")
    # make date range inclusive
    start = datetime.strptime(startdate, "%Y-%m-%d")
    end = datetime.strptime(enddate, "%Y-%m-%d")
    daybefore = start - timedelta(days=1)
    dayafter = end + timedelta(days=1)

    storageServiceId = request.args.get("ssId")
    storageService = storage_services.query.get(storageServiceId)
    AIPs = aips.query.filter_by(storage_service_id=storageServiceId).all()

    formatCount = {}
    originalsCount = 0

    for aip in AIPs:
        originalFiles = originals.query.filter_by(aip_id=aip.id)
        for original in originalFiles:
            # Note that original files in packages do not have a PREMIS ingestion
            # event. Therefore "message digest calculation" is used to get the
            # ingest date for all originals. This event typically happens within
            # the same second or seconds of the ingestion event and is done for all files.
            ingestEvent = events.query.filter_by(
                original_id=original.id, type="message digest calculation"
            ).first()
            if ingestEvent.date < daybefore:
                continue
            elif ingestEvent.date > dayafter:
                continue
            else:
                format = original.format
                size = original.size
                originalsCount += 1

                if format in formatCount:
                    formatCount[format]["count"] += 1
                    formatCount[format]["size"] += size
                else:
                    formatCount.update({format: {"count": 1, "size": size}})

    totalSize = 0
    x_axis = []
    y_axis = []
    format = []
    humanSize = []

    for key, value in formatCount.items():
        y_axis.append(value["count"])
        size = value["size"]
        if size == None:
            size = 0
        x_axis.append(size)
        totalSize += size
        humanSize.append(GetHumanReadableFilesize(size))

    format = list(formatCount.keys())
    differentFormats = len(formatCount.keys())
    totalHumanSize = GetHumanReadableFilesize(totalSize)

    return render_template(
        "plot_formats_count.html",
        startdate=startdate,
        enddate=enddate,
        storageService=storageService,
        originalsCount=originalsCount,
        formatCount=formatCount,
        differentFormats=differentFormats,
        totalHumanSize=totalHumanSize,
        x_axis=x_axis,
        y_axis=y_axis,
        format=format,
        humansize=humanSize,
    )


@reporter.route("/aip_contents/", methods=["GET"])
def aip_contents():
    """Return AIP contents organized by format."""
    storage_service_id = request.args.get("amss_id")
    aip_data = data.aip_overview_two(storage_service_id=storage_service_id)
    FIELD_UUID = "UUID"
    headers = [
        FIELD_UUID,
        data.FIELD_AIP_NAME,
        data.FIELD_CREATED_DATE,
        data.FIELD_AIP_SIZE,
    ]
    format_lookup = aip_data[data.FIELD_FORMATS]
    format_headers = list(aip_data[data.FIELD_FORMATS].keys())
    storage_service_name = aip_data[data.FIELD_STORAGE_NAME]
    aip_data.pop(data.FIELD_FORMATS, None)
    aip_data.pop(data.FIELD_STORAGE_NAME, None)
    rows = []
    for k, v in aip_data.items():
        row = []
        for header in headers:
            if header == FIELD_UUID:
                row.append(k)
            elif header == data.FIELD_AIP_SIZE:
                row.append(GetHumanReadableFilesize(v.get(header)))
            elif header != data.FIELD_FORMATS:
                row.append(v.get(header))
        formats = v.get(data.FIELD_FORMATS)
        for format_header in format_headers:
            format_ = formats.get(format_header)
            count = 0
            if format_:
                count = format_.get(data.FIELD_COUNT, 0)
            row.append(count)
        rows.append(row)
    headers = headers + format_headers
    return render_template(
        "aip_contents.html",
        storage_service=storage_service_id,
        storage_service_name=storage_service_name,
        aip_data=aip_data,
        columns=translate_headers(headers),
        rows=rows,
        format_lookup=format_lookup,
    )


# PICTURAE TODO: This can probably be a more descriptive name.
@reporter.route("/original_derivatives/", methods=["GET"])
def original_derivatives():
    """Return a mapping between original files and derivatives if they
    exist.
    """
    tables = []
    storage_service_id = request.args.get("amss_id")
    aip_data = data.derivative_overview(storage_service_id=storage_service_id)
    COL_NAME = data.FIELD_STORAGE_NAME
    ALL_AIPS = data.FIELD_ALL_AIPS
    storage_service_name = aip_data[COL_NAME]
    for aip in aip_data[ALL_AIPS]:
        aip_row = []
        transfer_name = aip[data.FIELD_TRANSFER_NAME]
        for pairing in aip[data.FIELD_RELATED_PAIRING]:
            row = []
            row.append(transfer_name)
            row.append(pairing[data.FIELD_ORIGINAL_UUID])
            row.append(pairing[data.FIELD_ORIGINAL_FORMAT])
            row.append(pairing[data.FIELD_DERIVATIVE_UUID])
            row.append(pairing[data.FIELD_DERIVATIVE_FORMAT])
            aip_row.append(row)
        tables.append(aip_row)
    headers = [
        data.FIELD_TRANSFER_NAME,
        data.FIELD_ORIGINAL_UUID,
        data.FIELD_ORIGINAL_FORMAT,
        data.FIELD_DERIVATIVE_UUID,
        data.FIELD_DERIVATIVE_FORMAT,
    ]
    aip_count = len(tables)
    return render_template(
        "report_originals_derivatives.html",
        storage_service=storage_service_id,
        storage_service_name=storage_service_name,
        aip_count=aip_count,
        headers=translate_headers(headers),
        tables=tables,
    )
