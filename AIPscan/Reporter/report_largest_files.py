from flask import render_template
from flask import request

from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.Data import report_data_typesense
from AIPscan.helpers import parse_bool
from AIPscan.helpers import parse_datetime_bound
from AIPscan.Reporter import download_csv
from AIPscan.Reporter import format_size_for_csv
from AIPscan.Reporter import get_display_end_date
from AIPscan.Reporter import reporter
from AIPscan.Reporter import request_params
from AIPscan.Reporter import translate_headers

TABLE_HEADERS = [
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
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    file_type = request.args.get(request_params.FILE_TYPE)
    limit = 20
    try:
        limit = int(request.args.get(request_params.LIMIT, 20))
    except ValueError:
        pass
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    if ts_helpers.typesense_enabled():
        file_data = report_data_typesense.largest_files(
            storage_service_id,
            start_date,
            end_date,
            storage_location_id,
            file_type,
            limit,
        )
    else:
        file_data = report_data.largest_files(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            storage_location_id=storage_location_id,
            file_type=file_type,
            limit=limit,
        )

    if csv:
        headers = translate_headers(CSV_HEADERS, True)

        filename = "largest_files.csv"
        csv_data = format_size_for_csv(file_data[fields.FIELD_FILES])
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(TABLE_HEADERS)

    return render_template(
        "report_largest_files.html",
        storage_service_id=storage_service_id,
        storage_service_name=file_data.get(fields.FIELD_STORAGE_NAME),
        storage_location_id=storage_location_id,
        storage_location_description=file_data.get(fields.FIELD_STORAGE_LOCATION),
        columns=headers,
        files=file_data[fields.FIELD_FILES],
        file_type=file_type,
        limit=limit,
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )
