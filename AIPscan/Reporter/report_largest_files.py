# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import data
from AIPscan.Reporter import reporter, translate_headers


@reporter.route("/largest_files/", methods=["GET"])
def largest_files():
    """Return largest files."""
    storage_service_id = request.args.get("amss_id")
    file_type = request.args.get("file_type")
    limit = 20
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        pass
    # TODO: Make limit configurable - currently set to default of 20
    file_data = data.largest_files(
        storage_service_id=storage_service_id, file_type=file_type, limit=limit
    )
    storage_service_name = file_data[data.FIELD_STORAGE_NAME]
    headers = [
        data.FIELD_FILENAME,
        data.FIELD_SIZE,
        data.FIELD_FORMAT,
        data.FIELD_PUID,
        data.FIELD_FILE_TYPE,
        data.FIELD_AIP,
    ]
    return render_template(
        "report_largest_files.html",
        storage_service_id=storage_service_id,
        storage_service_name=storage_service_name,
        columns=translate_headers(headers),
        files=file_data[data.FIELD_FILES],
        file_type=file_type,
        limit=limit,
    )
