# -*- coding: utf-8 -*-
from operator import itemgetter

from flask import render_template, request

from AIPscan import db
from AIPscan.Data import data, fields
from AIPscan.helpers import filesizeformat, parse_bool
from AIPscan.models import AIP, File, FileType, StorageService
from AIPscan.Reporter import download_csv, reporter, request_params, translate_headers

HEADERS = [
    fields.FIELD_UUID,
    fields.FIELD_AIP_NAME,
    fields.FIELD_CREATED_DATE,
    fields.FIELD_AIP_SIZE,
]


def _prepare_csv_data(storage_service_id, rows, puids):
    """Return data prepared for CSV file.

    :param storage_service_id: Storage Service ID (int)
    :param rows: Data assembled for tabular report (list of lists)
    :param puids: List of all PUIDs in report (list)

    :returns: Data formatted for CSV export (list of dicts)
    """
    csv_rows = []
    sorted_rows = _sort_rows_by_uuid(rows)
    for row in sorted_rows:
        row_dict = {}
        aip_uuid = row[0]
        row_dict[fields.FIELD_AIP_UUID] = aip_uuid
        row_dict[fields.FIELD_AIP_NAME] = row[1]
        row_dict[fields.FIELD_CREATED_DATE] = row[2]
        row_dict[fields.FIELD_AIP_SIZE] = row[3]
        for puid in puids:
            row_dict[puid] = _get_aip_puid_count(storage_service_id, aip_uuid, puid)
        csv_rows.append(row_dict)
    return csv_rows


def _sort_rows_by_uuid(rows):
    """Sort list of lists by AIP UUID.

    :param rows: Data assembled for tabular report (list of lists)

    :returns: rows but sorted by PUID (list of lists)
    """
    return sorted(rows, key=itemgetter(0))


def _get_aip_puid_count(storage_service_id, aip_uuid, puid):
    """Return count of files in AIP with given PUID.

    :param storage_service_id: Storage Service ID (int)
    :param aip_uuid: AIP UUID (str)
    :param puid: PUID to get count for (str)

    :returns: Count of files with PUID in given AIP for CSV report (str)
    """
    count = 0
    if puid == "null":
        puid = None
    aip_puid_count = (
        db.session.query(db.func.count(File.file_format).label("count"))
        .join(AIP)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.original.value)
        .filter(AIP.uuid == aip_uuid)
        .filter(File.puid == puid)
        .first()
    )
    try:
        count = str(aip_puid_count.count)
    except AttributeError:
        pass
    return str(count)


@reporter.route("/aip_contents/", methods=["GET"])
def aip_contents():
    """Return AIP contents organized by format."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    aip_data = data.aip_file_format_overview(storage_service_id=storage_service_id)

    format_lookup = aip_data[fields.FIELD_FORMATS]
    format_headers = list(aip_data[fields.FIELD_FORMATS].keys())

    storage_name = aip_data[fields.FIELD_STORAGE_NAME]

    aip_data.pop(fields.FIELD_FORMATS, None)
    aip_data.pop(fields.FIELD_STORAGE_NAME, None)
    rows = []
    for k, v in aip_data.items():
        row = []
        for header in HEADERS:
            if header == fields.FIELD_UUID:
                row.append(k)
            elif header == fields.FIELD_AIP_SIZE:
                row.append(filesizeformat(v.get(header)))
            elif header != fields.FIELD_FORMATS:
                row.append(v.get(header))
        formats = v.get(fields.FIELD_FORMATS)
        for format_header in format_headers:
            format_ = formats.get(format_header)
            count = 0
            if format_:
                count = format_.get(fields.FIELD_COUNT, 0)
            row.append(count)
        rows.append(row)

    headers = HEADERS + format_headers
    headers = translate_headers(headers)

    if csv:
        filename = "aip_contents.csv"
        csv_data = _prepare_csv_data(storage_service_id, rows, format_headers)
        return download_csv(headers, csv_data, filename)

    return render_template(
        "report_aip_contents.html",
        storage_service=storage_service_id,
        storage_service_name=storage_name,
        aip_data=aip_data,
        columns=headers,
        rows=rows,
        format_lookup=format_lookup,
    )
