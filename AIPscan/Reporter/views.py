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


@reporter.route("/view_aips/", methods=["GET"])
@reporter.route("/view_aips/<id>", methods=["GET"])
def view_aips(id=0):

    # CR: This is a really good attempt at being robust. There are a few things
    # we can do here to simplify it though. And a couple of other things we
    # might want to consider.
    #
    # Variable naming:
    #
    #    * 'storageService' should be 'storage_service' as we try to use snake
    #       case in Python with CamelCase reserved for classes. After a while
    #       it really helps to differentiate things.
    #
    # Logic:
    #
    #    * I suspect this isn't quite doing what we want it to do, even though
    #      it works, but I think this can come out of simplifying it. I'll
    #      propose an alternative below and see what you think.
    #
    """

    DEFAULT_STORAGE_SERVICE_ID = 1
    storage_services_ = {}
    storage_id = int(id)
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

    """
    # The variable names are tough eh? Maybe we can expand the model names so
    # we can use our nice shorter names for local vars? Let's have a think
    # though.
    #

    if id != 0:
        storageService = storage_services.query.get(id)
        storageServiceId = storageService.id
    else:
        storageService = storage_services.query.filter_by(default=1).first()
        if storageService:
            storageServiceId = storageService.id
        else:
            storageService = storage_services.query.first()
            if storageService:
                storageServiceId = storageService.id
            else:
                storageServiceId = 0

    if storageService:
        AIPs = aips.query.filter_by(storage_service_id=storageService.id).all()
        totalAIPs = aips.query.filter_by(storage_service_id=storageService.id).count()
    else:
        AIPs = None
        totalAIPs = 0

    storageServices = storage_services.query.all()

    return render_template(
        "view_aips.html",
        storageServices=storageServices,
        storageServiceId=storageServiceId,
        totalAIPs=totalAIPs,
        AIPs=AIPs,
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
    COL_UUID = "UUID"
    COL_AIPNAME = "AipName"
    COL_CREATED = "CreatedDate"
    COL_SIZE = "AipSize"
    COL_FORMATS = "Formats"
    COL_COUNT = "Count"
    COL_NAME = "StorageName"
    headers = [COL_UUID, COL_AIPNAME, COL_CREATED, COL_SIZE]
    format_lookup = aip_data[COL_FORMATS]
    format_headers = list(aip_data[COL_FORMATS].keys())
    storage_service_name = aip_data[COL_NAME]
    aip_data.pop(COL_FORMATS, None)
    aip_data.pop(COL_NAME, None)
    rows = []
    for k, v in aip_data.items():
        row = []
        for header in headers:
            if header == COL_UUID:
                row.append(k)
            elif header == COL_SIZE:
                row.append(GetHumanReadableFilesize(v.get(header)))
            elif header != COL_FORMATS:
                row.append(v.get(header))
        formats = v.get(COL_FORMATS)
        for format_header in format_headers:
            format_ = formats.get(format_header)
            count = 0
            if format_:
                count = format_.get(COL_COUNT, 0)
            row.append(count)
        rows.append(row)
    headers = headers + format_headers
    return render_template(
        "aip_contents.html",
        storage_service=storage_service_id,
        storage_service_name=storage_service_name,
        aip_data=aip_data,
        columns=headers,
        rows=rows,
        format_lookup=format_lookup,
    )
