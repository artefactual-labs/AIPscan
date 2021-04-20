# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_bool
from AIPscan.models import File
from AIPscan.Reporter import download_csv, reporter, request_params, translate_headers

HEADERS = [
    fields.FIELD_AIP_NAME,
    fields.FIELD_UUID,
    fields.FIELD_COUNT,
    fields.FIELD_SIZE,
]


def get_format_string_from_puid(puid):
    """Return file format and version info for a PUID or None

    :param puid: PUID (str)

    :returns: "File format (version)", "File Format", or None.
    """
    file_with_puid = File.query.filter_by(puid=puid).first()
    if file_with_puid is None:
        return None
    try:
        file_format = file_with_puid.file_format
    except AttributeError:
        return None
    try:
        format_version = file_with_puid.format_version
    except AttributeError:
        pass
    if format_version:
        return "{} ({})".format(file_format, format_version)
    return file_format


@reporter.route("/aips_by_puid/", methods=["GET"])
def aips_by_puid():
    """Return AIPs containing PUID, sorted by count and total size."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    puid = request.args.get(request_params.PUID)
    original_files = parse_bool(request.args.get(request_params.ORIGINAL_FILES, True))
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    headers = translate_headers(HEADERS)

    aip_data = report_data.aips_by_puid(
        storage_service_id=storage_service_id, puid=puid, original_files=original_files
    )

    if csv:
        filename = "aips_by_puid_{}.csv".format(puid)
        return download_csv(headers, aip_data[fields.FIELD_AIPS], filename)

    return render_template(
        "report_aips_by_puid.html",
        storage_service_id=storage_service_id,
        storage_service_name=aip_data.get(fields.FIELD_STORAGE_NAME),
        puid=puid,
        file_format=get_format_string_from_puid(puid),
        original_files=original_files,
        columns=translate_headers(headers),
        aips=aip_data.get(fields.FIELD_AIPS),
    )
