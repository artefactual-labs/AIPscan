# -*- coding: utf-8 -*-

"""Report formats count consists of the tabular report, plot, and
chart which describe the file formats present across the AIPs in a
storage service with AIPs filtered by date range.
"""

from collections import Counter
from datetime import datetime, timedelta

from flask import render_template, request

from AIPscan.models import aips, events, originals, storage_services
from AIPscan.helpers import get_human_readable_file_size
from AIPscan.Reporter import reporter


@reporter.route("/report_formats_count/", methods=["GET"])
def report_formats_count():
    """Report (tabular) on all file formats and their counts and size on
    disk across all AIPs in the storage service.
    """
    start_date = request.args.get("startdate")
    end_date = request.args.get("enddate")
    # make date range inclusive
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    day_before = start - timedelta(days=1)
    day_after = end + timedelta(days=1)

    storage_service_id = request.args.get("ssId")
    storage_service = storage_services.query.get(storage_service_id)
    packages = aips.query.filter_by(storage_service_id=storage_service_id).all()

    format_count = {}
    originals_count = 0

    for aip in packages:
        original_files = originals.query.filter_by(aip_id=aip.id)
        for original in original_files:
            # Note that original files in packages do not have a PREMIS ingestion
            # event. Therefore "message digest calculation" is used to get the
            # ingest date for all originals. This event typically happens within
            # the same second or seconds of the ingestion event and is done for all files.
            ingest_event = events.query.filter_by(
                original_id=original.id, type="message digest calculation"
            ).first()
            if ingest_event.date < day_before:
                continue
            elif ingest_event.date > day_after:
                continue
            else:
                file_format = original.file_format
                size = original.size
                originals_count += 1

                if file_format in format_count:
                    format_count[file_format]["count"] += 1
                    if format_count[file_format]["size"] is not None:
                        format_count[file_format]["size"] += size
                else:
                    format_count.update({file_format: {"count": 1, "size": size}})

    total_size = 0

    for key, value in format_count.items():
        size = value["size"]
        if size is not None:
            total_size += size
            human_size = get_human_readable_file_size(size)
            format_count[key] = {
                "count": value["count"],
                "size": size,
                "humansize": human_size,
            }

    different_formats = len(format_count.keys())
    total_human_size = get_human_readable_file_size(total_size)

    return render_template(
        "report_formats_count.html",
        startdate=start_date,
        enddate=end_date,
        storageService=storage_service,
        originalsCount=originals_count,
        formatCount=format_count,
        differentFormats=different_formats,
        totalHumanSize=total_human_size,
    )


@reporter.route("/chart_formats_count/", methods=["GET"])
def chart_formats_count():
    """Report (pie chart) on all file formats and their counts and size
    on disk across all AIPs in the storage service."""
    start_date = request.args.get("startdate")
    end_date = request.args.get("enddate")
    # make date range inclusive
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    day_before = start - timedelta(days=1)
    day_after = end + timedelta(days=1)

    storage_service_id = request.args.get("ssId")
    storage_service = storage_services.query.get(storage_service_id)
    packages = aips.query.filter_by(storage_service_id=storage_service_id).all()

    format_labels = []
    format_counts = []
    originals_count = 0

    for aip in packages:
        original_files = originals.query.filter_by(aip_id=aip.id)
        for original in original_files:
            # Note that original files in packages do not have a PREMIS ingestion
            # event. Therefore "message digest calculation" is used to get the
            # ingest date for all originals. This event typically happens within
            # the same second or seconds of the ingestion event and is done for all files.
            ingest_event = events.query.filter_by(
                original_id=original.id, type="message digest calculation"
            ).first()
            if ingest_event.date < day_before:
                continue
            elif ingest_event.date > day_after:
                continue
            else:
                format_labels.append(original.file_format)
                originals_count += 1

    format_counts = Counter(format_labels)
    labels = list(format_counts.keys())
    values = list(format_counts.values())

    different_formats = len(format_counts.keys())

    return render_template(
        "chart_formats_count.html",
        startdate=start_date,
        enddate=end_date,
        storageService=storage_service,
        labels=labels,
        values=values,
        originalsCount=originals_count,
        differentFormats=different_formats,
    )


@reporter.route("/plot_formats_count/", methods=["GET"])
def plot_formats_count():
    """Report (scatter) on all file formats and their counts and size on
    disk across all AIPs in the storage service.
    """
    start_date = request.args.get("startdate")
    end_date = request.args.get("enddate")
    # make date range inclusive
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    day_before = start - timedelta(days=1)
    day_after = end + timedelta(days=1)

    storage_service_id = request.args.get("ssId")
    storage_service = storage_services.query.get(storage_service_id)
    packages = aips.query.filter_by(storage_service_id=storage_service_id).all()

    format_count = {}
    originals_count = 0

    for aip in packages:
        original_files = originals.query.filter_by(aip_id=aip.id)
        for original in original_files:
            # Note that original files in packages do not have a PREMIS ingestion
            # event. Therefore "message digest calculation" is used to get the
            # ingest date for all originals. This event typically happens within
            # the same second or seconds of the ingestion event and is done for all files.
            ingest_event = events.query.filter_by(
                original_id=original.id, type="message digest calculation"
            ).first()
            if ingest_event.date < day_before:
                continue
            elif ingest_event.date > day_after:
                continue
            else:
                file_format = original.file_format
                size = original.size
                originals_count += 1

                if file_format in format_count:
                    format_count[file_format]["count"] += 1
                    format_count[file_format]["size"] += size
                else:
                    format_count.update({file_format: {"count": 1, "size": size}})

    total_size = 0
    x_axis = []
    y_axis = []
    file_format = []
    human_size = []

    for _, value in format_count.items():
        y_axis.append(value["count"])
        size = value["size"]
        if size is None:
            size = 0
        x_axis.append(size)
        total_size += size
        human_size.append(get_human_readable_file_size(size))

    file_format = list(format_count.keys())
    different_formats = len(format_count.keys())
    total_human_size = get_human_readable_file_size(total_size)

    return render_template(
        "plot_formats_count.html",
        startdate=start_date,
        enddate=end_date,
        storageService=storage_service,
        originalsCount=originals_count,
        formatCount=format_count,
        differentFormats=different_formats,
        totalHumanSize=total_human_size,
        x_axis=x_axis,
        y_axis=y_axis,
        format=file_format,
        humansize=human_size,
    )
