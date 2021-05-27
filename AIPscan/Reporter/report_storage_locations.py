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
    fields.FIELD_UUID,
    fields.FIELD_STORAGE_LOCATION,
    fields.FIELD_AIPS,
    fields.FIELD_SIZE,
]


@reporter.route("/storage_locations/", methods=["GET"])
def storage_locations():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    headers = translate_headers(HEADERS)

    locations_data = report_data.storage_locations(
        storage_service_id=storage_service_id
    )
    locations = locations_data.get(fields.FIELD_LOCATIONS)

    if csv:
        filename = "storage_locations.csv"
        csv_data = format_size_for_csv(locations)
        return download_csv(headers, csv_data, filename)

    return render_template(
        "report_storage_locations.html",
        storage_service_id=storage_service_id,
        storage_service_name=locations_data.get(fields.FIELD_STORAGE_NAME),
        columns=headers,
        locations=locations,
    )
