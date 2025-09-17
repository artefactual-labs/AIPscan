from flask import render_template
from flask import request

from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_bool
from AIPscan.Reporter import download_csv
from AIPscan.Reporter import format_size_for_csv
from AIPscan.Reporter import reporter
from AIPscan.Reporter import request_params
from AIPscan.Reporter import translate_headers

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
        headers = translate_headers(HEADERS, True)

        filename = f"aips_by_file_format_{file_format}.csv"
        csv_data = format_size_for_csv(aip_data[fields.FIELD_AIPS])
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(HEADERS)

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
