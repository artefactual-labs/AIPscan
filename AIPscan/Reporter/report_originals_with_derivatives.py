# -*- coding: utf-8 -*-

"""Report on original copies that have a preservation derivative and
the different file formats associated with both.
"""

from flask import render_template, request

from AIPscan.Data import data
from AIPscan.Reporter import reporter, translate_headers


@reporter.route("/original_derivatives/", methods=["GET"])
def original_derivatives():
    """Return a mapping between original files and derivatives if they
    exist.
    """
    tables = []
    storage_service_id = request.args.get("amss_id")
    aip_data = data.derivative_overview(storage_service_id=storage_service_id)
    COL_NAME = data.FIELD_STORAGE_NAME
    ALL_AIPS = data.FIELD_ALL_AIPS
    storage_service_name = aip_data[COL_NAME]
    for aip in aip_data[ALL_AIPS]:
        aip_row = []
        transfer_name = aip[data.FIELD_TRANSFER_NAME]
        for pairing in aip[data.FIELD_RELATED_PAIRING]:
            row = []
            row.append(transfer_name)
            row.append(pairing[data.FIELD_ORIGINAL_UUID])
            row.append(pairing[data.FIELD_ORIGINAL_FORMAT])
            row.append(pairing[data.FIELD_DERIVATIVE_UUID])
            row.append(pairing[data.FIELD_DERIVATIVE_FORMAT])
            aip_row.append(row)
        tables.append(aip_row)
    headers = [
        data.FIELD_TRANSFER_NAME,
        data.FIELD_ORIGINAL_UUID,
        data.FIELD_ORIGINAL_FORMAT,
        data.FIELD_DERIVATIVE_UUID,
        data.FIELD_DERIVATIVE_FORMAT,
    ]
    aip_count = len(tables)
    return render_template(
        "report_originals_derivatives.html",
        storage_service=storage_service_id,
        storage_service_name=storage_service_name,
        aip_count=aip_count,
        headers=translate_headers(headers),
        tables=tables,
    )
