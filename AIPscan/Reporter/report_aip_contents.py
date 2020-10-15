# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import data
from AIPscan.helpers import get_human_readable_file_size
from AIPscan.Reporter import reporter, translate_headers, request_params


@reporter.route("/aip_contents/", methods=["GET"])
def aip_contents():
    """Return AIP contents organized by format."""
    storage_service_id = request.args.get(request_params["storage_service_id"])
    aip_data = data.aip_overview_two(storage_service_id=storage_service_id)
    FIELD_UUID = "UUID"
    headers = [
        FIELD_UUID,
        data.FIELD_AIP_NAME,
        data.FIELD_CREATED_DATE,
        data.FIELD_AIP_SIZE,
    ]
    format_lookup = aip_data[data.FIELD_FORMATS]
    format_headers = list(aip_data[data.FIELD_FORMATS].keys())
    storage_service_name = aip_data[data.FIELD_STORAGE_NAME]
    aip_data.pop(data.FIELD_FORMATS, None)
    aip_data.pop(data.FIELD_STORAGE_NAME, None)
    rows = []
    for k, v in aip_data.items():
        row = []
        for header in headers:
            if header == FIELD_UUID:
                row.append(k)
            elif header == data.FIELD_AIP_SIZE:
                row.append(get_human_readable_file_size(v.get(header)))
            elif header != data.FIELD_FORMATS:
                row.append(v.get(header))
        formats = v.get(data.FIELD_FORMATS)
        for format_header in format_headers:
            format_ = formats.get(format_header)
            count = 0
            if format_:
                count = format_.get(data.FIELD_COUNT, 0)
            row.append(count)
        rows.append(row)
    headers = headers + format_headers
    return render_template(
        "aip_contents.html",
        storage_service=storage_service_id,
        storage_service_name=storage_service_name,
        aip_data=aip_data,
        columns=translate_headers(headers),
        rows=rows,
        format_lookup=format_lookup,
    )
