"""Report on original copies that have a preservation derivative and
the different file formats associated with both.
"""

from flask import render_template
from flask import request

from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_bool
from AIPscan.Reporter import download_csv
from AIPscan.Reporter import reporter
from AIPscan.Reporter import request_params
from AIPscan.Reporter import translate_headers

HEADERS = [
    fields.FIELD_AIP_NAME,
    fields.FIELD_ORIGINAL_FILE,
    fields.FIELD_ORIGINAL_FORMAT,
    fields.FIELD_DERIVATIVE_FILE,
    fields.FIELD_DERIVATIVE_FORMAT,
]

CSV_HEADERS = [
    fields.FIELD_AIP_UUID,
    fields.FIELD_AIP_NAME,
    fields.FIELD_UUID,
    fields.FIELD_NAME,
    fields.FIELD_FORMAT,
    fields.FIELD_ORIGINAL_UUID,
    fields.FIELD_ORIGINAL_NAME,
    fields.FIELD_ORIGINAL_FORMAT,
    fields.FIELD_ORIGINAL_VERSION,
    fields.FIELD_ORIGINAL_PUID,
]


def _get_unique_aips(derivative_files):
    """Return list of AIPs represented in data.

    :param derivative files: Derivative files from report endpoint data (list
        of dicts)

    :returns: Unique AIPs with derivatives (list of dicts with keys
        fields.FIELD_AIP_UUID and fields.FIELD_AIP_NAME)
    """
    captured_keys = [fields.FIELD_AIP_UUID, fields.FIELD_AIP_NAME]
    filtered = {
        tuple((k, file_[k]) for k in sorted(file_) if k in captured_keys): file_
        for file_ in derivative_files
    }
    filtered_files = list(filtered.values())
    return [
        {
            fields.FIELD_AIP_UUID: file_[fields.FIELD_AIP_UUID],
            fields.FIELD_AIP_NAME: file_[fields.FIELD_AIP_NAME],
        }
        for file_ in filtered_files
    ]


@reporter.route("preservation_derivatives/", methods=["GET"])
def preservation_derivatives():
    """Return a report of derivative files mapped to AIPs and originals."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    csv = parse_bool(request.args.get(request_params.CSV), default=False)
    aip_uuid = request.args.get(request_params.AIP_UUID)

    headers = translate_headers(HEADERS)

    derivative_data = report_data.preservation_derivatives(
        storage_service_id, storage_location_id, aip_uuid
    )
    derivative_files = derivative_data[fields.FIELD_FILES]

    total_files = len(derivative_files)

    unique_aips = _get_unique_aips(derivative_files)

    if csv:
        filename = "preservation_derivatives.csv"
        headers = translate_headers(CSV_HEADERS)
        return download_csv(headers, derivative_files, filename)

    return render_template(
        "report_preservation_derivatives.html",
        storage_service_id=storage_service_id,
        storage_service_name=derivative_data.get(fields.FIELD_STORAGE_NAME),
        storage_location_id=storage_location_id,
        storage_location_description=derivative_data.get(fields.FIELD_STORAGE_LOCATION),
        columns=headers,
        files=derivative_files,
        total_files=total_files,
        aips=unique_aips,
        selected_aip=aip_uuid,
    )
