# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.Reporter import reporter, translate_headers, request_params


@reporter.route("/largest_files/", methods=["GET"])
def largest_files():
    """Return largest files."""
    storage_service_id = request.args.get(request_params["storage_service_id"])
    file_type = request.args.get(request_params["file_type"])
    limit = 20
    try:
        limit = int(request.args.get(request_params["limit"], 20))
    except ValueError:
        pass
    file_data = report_data.largest_files(
        storage_service_id=storage_service_id, file_type=file_type, limit=limit
    )
    storage_service_name = file_data[fields.FIELD_STORAGE_NAME]
    headers = [
        fields.FIELD_FILENAME,
        fields.FIELD_SIZE,
        fields.FIELD_FORMAT,
        fields.FIELD_PUID,
        fields.FIELD_FILE_TYPE,
        fields.FIELD_AIP_NAME,
    ]
    return render_template(
        "report_largest_files.html",
        storage_service_id=storage_service_id,
        storage_service_name=storage_service_name,
        columns=translate_headers(headers),
        files=file_data[fields.FIELD_FILES],
        file_type=file_type,
        limit=limit,
    )
