import json

from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.Data import report_dict


def document_to_report_row(document, report_fields):
    row = {}

    for report_field in report_fields:
        document_field = report_fields[report_field]

        if document_field == "size":
            row[report_field] = int(document.get(document_field, 0))
        else:
            row[report_field] = document.get(document_field, "")

    return row


def formats_count(
    storage_service_id,
    storage_location_id,
    start_date,
    end_date,
    include_size_data=True,
):
    if not ts_helpers.collection_has_facets("file", {"format_name"}):
        return report_data.formats_count(
            storage_service_id, start_date, end_date, storage_location_id
        )
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMATS] = []

    # Get format counts via facet data
    file_filters = ts_helpers.file_filters(
        storage_service_id, storage_location_id, start_date, end_date
    )

    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": ts_helpers.assemble_filter_by(file_filters),
            "exclude_fields": "*",
            "facet_by": "format_name",
            "max_facet_values": 10000,
        },
    )

    value_counts = ts_helpers.facet_value_counts(results, "format_name")

    # If no formats were found then don't proceed to get counts
    if len(value_counts) == 0:
        return report

    format_size_sums = {}
    if include_size_data:
        # Request total size of files for each file format
        search_requests = {"searches": []}
        for file_format in value_counts.keys():
            format_filters = file_filters.copy()
            format_filters.append(("format_name", "=", f"`{file_format}`"))

            format_filter_by = ts_helpers.assemble_filter_by(format_filters)

            search_requests["searches"].append(
                {
                    "collection": ts_helpers.collection_prefix("file"),
                    "q": "*",
                    "include_fields": "format_name",
                    "filter_by": format_filter_by,
                    "facet_by": "size",
                    "facet_strategy": "exhaustive",
                    "max_facet_values": 1,
                }
            )

        searches = ts_helpers.client().multi_search.perform(
            search_requests, {"limit_multi_searches": len(search_requests["searches"])}
        )

        # Summarize file format sizes
        for results in searches["results"]:
            if "hits" in results:
                file_format = results["hits"][0]["document"]["format_name"]

                for count in results["facet_counts"]:
                    if count["field_name"] == "size":
                        format_size_sums[file_format] = int(
                            count.get("stats", {}).get("sum", 0)
                        )

    # Format results for report
    format_data = {}

    for file_format in value_counts.keys():
        format_data[file_format] = {
            fields.FIELD_FORMAT: file_format,
            fields.FIELD_COUNT: value_counts[file_format],
        }

        if format_size_sums != {}:
            format_data[file_format][fields.FIELD_SIZE] = format_size_sums.get(
                file_format, 0
            )

    report[fields.FIELD_FORMATS] = list(format_data.values())

    return report


def largest_aips(
    storage_service_id, start_date, end_date, storage_location_id, limit=20
):
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_AIPS] = []

    # Assemble filter_by
    start_timestamp = ts_helpers.datetime_to_timestamp_int(start_date)
    end_timestamp = ts_helpers.datetime_to_timestamp_int(end_date)

    filters = [
        ("create_date", ">=", start_timestamp),
        ("create_date", "<", end_timestamp),
        ("storage_service_id", "=", storage_service_id),
    ]

    if storage_location_id is not None and storage_location_id != "":
        filters.append(("storage_location_id", "=", storage_location_id))

    filter_by = ts_helpers.assemble_filter_by(filters)

    # Get AIPs in descending order of size
    report_fields = {
        fields.FIELD_NAME: "transfer_name",
        fields.FIELD_UUID: "uuid",
        fields.FIELD_SIZE: "size",
        fields.FIELD_FILE_COUNT: "original_file_count",
    }

    results = ts_helpers.search(
        "aip",
        {
            "q": "*",
            "filter_by": filter_by,
            "include_fields": ",".join(list(report_fields.values())),
            "per_page": limit,
            "sort_by": "size:desc",
        },
    )

    # Format results for report
    for hit in results["hits"]:
        file_info = document_to_report_row(hit["document"], report_fields)
        report[fields.FIELD_AIPS].append(file_info)

    return report


def largest_files(
    storage_service_id,
    start_date,
    end_date,
    storage_location_id,
    file_type=None,
    limit=20,
):
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FILES] = []

    # Get files in descending order of size
    file_filters = ts_helpers.file_filters(
        storage_service_id, storage_location_id, start_date, end_date, file_type
    )

    report_fields = {
        fields.FIELD_ID: "id",
        fields.FIELD_UUID: "uuid",
        fields.FIELD_NAME: "name",
        fields.FIELD_SIZE: "size",
        fields.FIELD_FILE_TYPE: "file_type",
        fields.FIELD_FORMAT: "file_format",
        fields.FIELD_VERSION: "format_version",
        fields.FIELD_PUID: "puid",
        fields.FIELD_AIP_NAME: "transfer_name",
        fields.FIELD_AIP_UUID: "aip_uuid",
    }

    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": ts_helpers.assemble_filter_by(file_filters),
            "include_fields": ",".join(list(report_fields.values())),
            "per_page": limit,
            "sort_by": "size:desc",
        },
    )

    # Format results for report
    for hit in results["hits"]:
        file_info = document_to_report_row(hit["document"], report_fields)
        report[fields.FIELD_FILES].append(file_info)

    return report


def format_versions_count(
    storage_service_id, start_date, end_date, storage_location_id=None
):
    if not ts_helpers.collection_has_facets("file", {"format_group"}):
        return report_data.format_versions_count(
            storage_service_id, start_date, end_date, storage_location_id
        )
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMAT_VERSIONS] = []

    file_filters = ts_helpers.file_filters(
        storage_service_id, storage_location_id, start_date, end_date
    )
    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": ts_helpers.assemble_filter_by(file_filters),
            "exclude_fields": "*",
            "facet_by": "format_group",
            "max_facet_values": 10000,
        },
    )
    groups = ts_helpers.facet_value_counts(results, "format_group")
    if not groups:
        return report

    searches = {"searches": []}
    for group in groups:
        filters = file_filters + [("format_group", "=", f"`{group}`")]
        searches["searches"].append(
            {
                "collection": ts_helpers.collection_prefix("file"),
                "q": "*",
                "exclude_fields": "*",
                "filter_by": ts_helpers.assemble_filter_by(filters),
                "facet_by": "size",
                "facet_strategy": "exhaustive",
                "max_facet_values": 1,
            }
        )
    totals = ts_helpers.client().multi_search.perform(
        searches, {"limit_multi_searches": len(groups)}
    )
    for group, result in zip(groups, totals["results"], strict=True):
        puid, file_format, version = json.loads(group)
        size = next(
            facet.get("stats", {}).get("sum", 0)
            for facet in result["facet_counts"]
            if facet["field_name"] == "size"
        )
        report[fields.FIELD_FORMAT_VERSIONS].append(
            {
                fields.FIELD_PUID: puid,
                fields.FIELD_FORMAT: file_format,
                fields.FIELD_VERSION: version,
                fields.FIELD_COUNT: groups[group],
                fields.FIELD_SIZE: int(size),
            }
        )
    report[fields.FIELD_FORMAT_VERSIONS].sort(
        key=lambda row: (row[fields.FIELD_COUNT], row[fields.FIELD_SIZE]), reverse=True
    )
    return report
