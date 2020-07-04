from flask import Blueprint, render_template, request
from AIPscan import db
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
from datetime import datetime
import plotly.express as px
import pandas as pd
import json


reporter = Blueprint("reporter", __name__, template_folder="templates")


@reporter.route("/view_aips/", methods=["GET"])
@reporter.route("/view_aips/<id>", methods=["GET"])
def view_aips(id=0):
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
    lastYear = now.year - 1
    startdate = str(datetime(lastYear, 12, 31))[:-9]
    tomorrow = now.day + 1
    enddate = str(datetime(now.year, now.month, tomorrow))[:-9]

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
            if ingestEvent.date < datetime.strptime(startdate, "%Y-%m-%d"):
                continue
            elif ingestEvent.date > datetime.strptime(enddate, "%Y-%m-%d"):
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
            if ingestEvent.date < datetime.strptime(startdate, "%Y-%m-%d"):
                continue
            elif ingestEvent.date > datetime.strptime(enddate, "%Y-%m-%d"):
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
            if ingestEvent.date < datetime.strptime(startdate, "%Y-%m-%d"):
                continue
            elif ingestEvent.date > datetime.strptime(enddate, "%Y-%m-%d"):
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

    # format Pandas data frame for scatterplot
    df1 = pd.read_json(json.dumps(formatCount))
    df2 = df1.transpose()
    df3 = df2.rename_axis("format").reset_index()
    df4 = df3.sort_values(by="count", ascending=False)
    df5 = df4.rename(columns={"size": "size in bytes", "humansize": "size"})
    df6 = json.dumps(df5)

    return render_template(
        "plot_formats_count.html",
        startdate=startdate,
        enddate=enddate,
        storageService=storageService,
        originalsCount=originalsCount,
        formatCount=formatCount,
        differentFormats=differentFormats,
        totalHumanSize=totalHumanSize,
        df=df6,
    )
