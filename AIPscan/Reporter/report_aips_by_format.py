# -*- coding: utf-8 -*-

from datetime import datetime
from flask import render_template, request

from AIPscan.Data import data
from AIPscan.Reporter import reporter, translate_headers


@reporter.route("/aips_by_file_format/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get("amss_id")
    file_format = request.args.get("file_format")

    start_date = request.args.get("start_date")
    if start_date is not None:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            # TODO: Log error for invalid start_date value
            start_date = None

    end_date = request.args.get("end_date")
    if end_date is not None:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            # TODO: Log error for invalid end_date value
            end_date = None

    aip_data = data.aips_by_file_format(
        storage_service_id=storage_service_id,
        file_format=file_format,
        start_date=start_date,
        end_date=end_date,
    )
    storage_service_name = aip_data[data.FIELD_STORAGE_NAME]
    headers = [data.FIELD_AIP_NAME, data.FIELD_UUID, data.FIELD_COUNT, data.FIELD_SIZE]
    return render_template(
        "report_aips_by_format.html",
        storage_service_id=storage_service_id,
        storage_service_name=storage_service_name,
        file_format=file_format,
        columns=translate_headers(headers),
        aips=aip_data[data.FIELD_AIPS],
        start_date=start_date,
        end_date=end_date,
    )
