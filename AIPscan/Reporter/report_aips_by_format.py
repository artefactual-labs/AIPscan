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
    fields.FIELD_AIP_NAME,
    fields.FIELD_UUID,
    fields.FIELD_COUNT,
    fields.FIELD_SIZE,
    fields.FIELD_SIZE_BYTES,
]


@reporter.route("/aips_by_file_format/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    file_format = request.args.get(request_params.FILE_FORMAT)
    original_files = parse_bool(request.args.get(request_params.ORIGINAL_FILES, True))
    csv = parse_bool(request.args.get(request_params.CSV), default=False)


    aip_data = report_data.aips_by_file_format(
        storage_service_id=storage_service_id,
        file_format=file_format,
        original_files=original_files,
        storage_location_id=storage_location_id,
    )

    if csv:
        headers = translate_headers(HEADERS)

        filename = "aips_by_file_format_{}.csv".format(file_format)
        csv_data = format_size_for_csv(aip_data[fields.FIELD_AIPS])
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(HEADERS, [fields.FIELD_SIZE_BYTES])

    return render_template(
        "report_aips_by_format.html",
        storage_service_id=storage_service_id,
        storage_service_name=aip_data.get(fields.FIELD_STORAGE_NAME),
        storage_location_description=aip_data.get(fields.FIELD_STORAGE_LOCATION),
        file_format=file_format,
        original_files=original_files,
        columns=headers,
        aips=aip_data.get(fields.FIELD_AIPS),
    )
