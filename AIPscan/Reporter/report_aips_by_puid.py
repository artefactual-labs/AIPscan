# -*- coding: utf-8 -*-

from datetime import datetime
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

    start_date = request.args.get("start_date")
    if start_date is not None:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            # TODO: Log error for invalid start_date value
            start_date = None

    end_date = request.args.get("end_date")
    if end_date is not None:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            # TODO: Log error for invalid end_date value
            end_date = None

    aip_data = data.aips_by_puid(
        storage_service_id=storage_service_id,
        puid=puid,
        start_date=start_date,
        end_date=end_date,
    )
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
        start_date=start_date,
        end_date=end_date,
    )
