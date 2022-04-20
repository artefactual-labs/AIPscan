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
    fields.FIELD_AIP_NAME,
    fields.FIELD_UUID,
    fields.FIELD_AIP_SIZE,
    fields.FIELD_FILE_COUNT,
]


@reporter.route("/largest_aips/", methods=["GET"])
def largest_aips():
    """Return largest files."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    limit = 20
    try:
        limit = int(request.args.get(request_params.LIMIT, 20))
    except ValueError:
        pass
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    headers = translate_headers(HEADERS)

    aip_data = report_data.largest_aips(
        storage_service_id=storage_service_id,
        start_date=start_date,
        end_date=end_date,
        storage_location_id=storage_location_id,
        limit=limit,
    )

    if csv:
        filename = "largest_aips.csv"
        headers = translate_headers(HEADERS)
        csv_data = format_size_for_csv(aip_data[fields.FIELD_AIPS])
        return download_csv(headers, csv_data, filename)

    return render_template(
        "report_largest_aips.html",
        storage_service_id=storage_service_id,
        storage_service_name=aip_data.get(fields.FIELD_STORAGE_NAME),
        storage_location_id=storage_location_id,
        storage_location_description=aip_data.get(fields.FIELD_STORAGE_LOCATION),
        columns=headers,
        aips=aip_data[fields.FIELD_AIPS],
        limit=limit,
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )
