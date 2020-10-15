# -*- coding: utf-8 -*-

from flask import render_template, request

from AIPscan.Data import data
from AIPscan.Reporter import reporter, translate_headers
from AIPscan.models import File


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
    storage_service_id = request.args.get("amss_id")
    puid = request.args.get("puid")
    aip_data = data.aips_by_puid(storage_service_id=storage_service_id, puid=puid)
    storage_service_name = aip_data[data.FIELD_STORAGE_NAME]
    headers = [data.FIELD_AIP_NAME, data.FIELD_UUID, data.FIELD_COUNT, data.FIELD_SIZE]
    return render_template(
        "report_aips_by_puid.html",
        storage_service_id=storage_service_id,
        storage_service_name=storage_service_name,
        puid=puid,
        file_format=get_format_string_from_puid(puid),
        columns=translate_headers(headers),
        aips=aip_data[data.FIELD_AIPS],
    )
