# -*- coding: utf-8 -*-
from flask import render_template, request

from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import (
    fields,
    get_storage_location_description,
    get_storage_service_name,
)
from AIPscan.helpers import parse_bool
from AIPscan.Reporter import (
    download_csv,
    format_size_for_csv,
    reporter,
    request_params,
    translate_headers,
)

HEADERS = [
    fields.FIELD_AIP_NAME,
    fields.FIELD_UUID,
    fields.FIELD_COUNT,
    fields.FIELD_SIZE,
]


def _aips_by_file_format(
    storage_service_id, storage_location_id, file_format, original_files
):
    # Cache AIP data
    aip_data = {}
    page = 1
    results = None

    while results is None or len(results["hits"]) != 0:
        # Get page of hits (250 is the most possible per page)
        results = ts_helpers.search("aip", {"q": "*", "page": page, "per_page": 250})

        for hit in results["hits"]:
            doc = hit["document"]

            aip_data[int(doc["id"])] = {
                "uuid": doc["uuid"],
                "transfer_name": doc["transfer_name"],
                "size": doc["size"],
            }

        page += 1

    # Fetch number of files (of the requested format) in AIPs
    filters = [
        ("storage_service_id", "=", storage_service_id),
        ("file_format", "=", "" + file_format + ""),
    ]

    if storage_location_id is not None and storage_location_id != "":
        filters.append(("storage_location_id", "=", storage_location_id))

    if original_files:
        filters.append(("file_type", "=", "'original'"))

    filter_by = ts_helpers.assemble_filter_by(filters)

    aip_file_counts = {}
    page = 1
    results = None

    while results is None or len(results["grouped_hits"]) != 0:
        # Get page of hits (250 is the most possible per page)
        results = ts_helpers.search(
            "file",
            {
                "q": "*",
                "page": page,
                "per_page": 250,
                "filter_by": filter_by,
                "group_by": "aip_id",
            },
        )

        for grouped_hit in results["grouped_hits"]:
            aip_id = grouped_hit["group_key"][0]

            if aip_id not in aip_file_counts:
                aip_file_counts[aip_id] = 0

            aip_file_counts[aip_id] += grouped_hit["found"]

        print(results)
        page += 1

    # Format display data
    aips = []
    for aip_id in aip_file_counts:
        aip = {}

        aip["AIPName"] = aip_data[aip_id]["transfer_name"]
        aip["UUID"] = aip_data[aip_id]["uuid"]
        aip["Count"] = aip_file_counts[aip_id]
        aip["Size"] = aip_data[aip_id]["size"]

        aips.append(aip)

    return aips


@reporter.route("/aips_by_file_format/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    file_format = request.args.get(request_params.FILE_FORMAT)
    original_files = parse_bool(request.args.get(request_params.ORIGINAL_FILES, True))
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    aip_data = _aips_by_file_format(
        storage_service_id=storage_service_id,
        file_format=file_format,
        original_files=original_files,
        storage_location_id=storage_location_id,
    )

    if csv:
        headers = translate_headers(HEADERS, True)

        filename = "aips_by_file_format_{}.csv".format(file_format)
        csv_data = format_size_for_csv(aip_data)
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(HEADERS)

    # aip_data.get(fields.FIELD_AIPS)
    return render_template(
        "report_aips_by_format.html",
        storage_service_id=storage_service_id,
        storage_service_name=get_storage_service_name(storage_service_id),
        storage_location_description=get_storage_location_description(
            storage_location_id
        ),
        file_format=file_format,
        original_files=original_files,
        columns=headers,
        aips=aip_data,
    )
