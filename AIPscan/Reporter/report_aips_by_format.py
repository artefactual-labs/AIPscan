# -*- coding: utf-8 -*-
from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_bool
from AIPscan.Reporter import download_csv, reporter, request_params, translate_headers

HEADERS = [
    fields.FIELD_AIP_NAME,
    fields.FIELD_UUID,
    fields.FIELD_COUNT,
    fields.FIELD_SIZE,
]


@reporter.route("/aips_by_file_format/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    file_format = request.args.get(request_params.FILE_FORMAT)
    original_files = parse_bool(request.args.get(request_params.ORIGINAL_FILES, True))
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    headers = translate_headers(HEADERS)

    aip_data = report_data.aips_by_file_format(
        storage_service_id=storage_service_id,
        file_format=file_format,
        original_files=original_files,
    )

    if csv:
        filename = "aips_by_file_format_{}.csv".format(file_format)
        return download_csv(headers, aip_data[fields.FIELD_AIPS], filename)

    return render_template(
        "report_aips_by_format.html",
        storage_service_id=storage_service_id,
        storage_service_name=aip_data.get(fields.FIELD_STORAGE_NAME),
        file_format=file_format,
        original_files=original_files,
        columns=headers,
        aips=aip_data.get(fields.FIELD_AIPS),
    )
