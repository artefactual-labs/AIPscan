# -*- coding: utf-8 -*-
from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_bool, parse_datetime_bound
from AIPscan.Reporter import (
    download_csv,
    format_size_for_csv,
    get_display_end_date,
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
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    headers = translate_headers(HEADERS)

    locations_data = report_data.storage_locations(
        storage_service_id=storage_service_id, start_date=start_date, end_date=end_date
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
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )
