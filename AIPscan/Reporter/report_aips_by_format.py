# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_bool
from AIPscan.Reporter import reporter, request_params, translate_headers


@reporter.route("/aips_by_file_format/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get(request_params["storage_service_id"])
    file_format = request.args.get(request_params["file_format"])
    original_files = parse_bool(
        request.args.get(request_params["original_files"], True)
    )
    aip_data = report_data.aips_by_file_format(
        storage_service_id=storage_service_id,
        file_format=file_format,
        original_files=original_files,
    )
    headers = [
        fields.FIELD_AIP_NAME,
        fields.FIELD_UUID,
        fields.FIELD_COUNT,
        fields.FIELD_SIZE,
    ]
    return render_template(
        "report_aips_by_format.html",
        storage_service_id=storage_service_id,
        storage_service_name=aip_data.get(fields.FIELD_STORAGE_NAME),
        file_format=file_format,
        original_files=original_files,
        columns=translate_headers(headers),
        aips=aip_data.get(fields.FIELD_AIPS),
    )
