# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_bool
from AIPscan.Reporter import (
    download_csv,
    format_size_for_csv,
    reporter,
    request_params,
    translate_headers,
)

HEADERS = [
    fields.FIELD_FILENAME,
    fields.FIELD_SIZE,
    fields.FIELD_FORMAT,
    fields.FIELD_PUID,
    fields.FIELD_FILE_TYPE,
    fields.FIELD_AIP_NAME,
]

CSV_HEADERS = [
    fields.FIELD_UUID,
    fields.FIELD_FILENAME,
    fields.FIELD_SIZE,
    fields.FIELD_FILE_TYPE,
    fields.FIELD_FORMAT,
    fields.FIELD_VERSION,
    fields.FIELD_PUID,
    fields.FIELD_AIP_NAME,
    fields.FIELD_AIP_UUID,
]


@reporter.route("/largest_files/", methods=["GET"])
def largest_files():
    """Return largest files."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    file_type = request.args.get(request_params.FILE_TYPE)
    limit = 20
    try:
        limit = int(request.args.get(request_params.LIMIT, 20))
    except ValueError:
        pass
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    headers = translate_headers(HEADERS)

    file_data = report_data.largest_files(
        storage_service_id=storage_service_id, file_type=file_type, limit=limit
    )

    if csv:
        filename = "largest_files.csv"
        headers = translate_headers(CSV_HEADERS)
        csv_data = format_size_for_csv(file_data[fields.FIELD_FILES])
        return download_csv(headers, csv_data, filename)

    return render_template(
        "report_largest_files.html",
        storage_service_id=storage_service_id,
        storage_service_name=file_data[fields.FIELD_STORAGE_NAME],
        columns=headers,
        files=file_data[fields.FIELD_FILES],
        file_type=file_type,
        limit=limit,
    )
