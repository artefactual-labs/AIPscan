# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import data
from AIPscan.Reporter import reporter, translate_headers


@reporter.route("/aips_by_file_format/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get("amss_id")
    file_format = request.args.get("file_format")
    aip_data = data.aips_by_file_format(
        storage_service_id=storage_service_id, file_format=file_format
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
    )
