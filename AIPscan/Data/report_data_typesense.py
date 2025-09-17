from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import fields
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
            "facet_by": "file_format",
            "max_facet_values": 10000,
        },
    )

    value_counts = ts_helpers.facet_value_counts(results, "file_format")

    # If no formats were found then don't proceed to get counts
    if len(value_counts) == 0:
        return report

    format_size_sums = {}
    if include_size_data:
        # Request total size of files for each file format
        search_requests = {"searches": []}
        for file_format in value_counts.keys():
            format_filters = file_filters.copy()
            format_filters.append(("file_format", "=", f"`{file_format}`"))

            format_filter_by = ts_helpers.assemble_filter_by(format_filters)

            search_requests["searches"].append(
                {
                    "collection": ts_helpers.collection_prefix("file"),
                    "q": "*",
                    "include_fields": "file_format",
                    "filter_by": format_filter_by,
                    "facet_by": "size",
                    "max_facet_values": 1,
                }
            )

        searches = ts_helpers.client().multi_search.perform(
            search_requests, {"limit_multi_searches": len(search_requests["searches"])}
        )

        # Summarize file format sizes
        for results in searches["results"]:
            if "hits" in results:
                file_format = results["hits"][0]["document"]["file_format"]

                for count in results["facet_counts"]:
                    if count["field_name"] == "size":
                        format_size_sums[file_format] = count["stats"]["sum"]

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
        fields.FIELD_UUID: "uuid",
        fields.FIELD_NAME: "transfer_name",
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
        storage_service_id, storage_location_id, start_date, end_date
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
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMAT_VERSIONS] = []

    # Get format counts via facet data
    file_filters = ts_helpers.file_filters(
        storage_service_id, storage_location_id, start_date, end_date
    )

    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": ts_helpers.assemble_filter_by(file_filters),
            "include_fields": "puid",
            "facet_by": "puid",
            "max_facet_values": 10000,
        },
    )

    puid_counts = ts_helpers.facet_value_counts(results, "puid")

    # If no format versions were found then don't proceed to get counts
    if len(puid_counts) == 0:
        return report

    # Request total size of files for each PUID
    puids = list(puid_counts.keys())

    search_requests = {"searches": []}
    for puid in puids:
        format_filters = file_filters.copy()
        format_filters.append(("puid", "=", f"`{puid}`"))

        format_filter_by = ts_helpers.assemble_filter_by(format_filters)

        search_requests["searches"].append(
            {
                "collection": ts_helpers.collection_prefix("file"),
                "q": "*",
                "include_fields": "puid,file_format,format_version",
                "filter_by": format_filter_by,
                "facet_by": "size",
                "max_facet_values": 1,
            }
        )

    searches = ts_helpers.client().multi_search.perform(
        search_requests, {"limit_multi_searches": len(search_requests["searches"])}
    )

    # Summarize PUID sizes
    puid_sizes = {}
    puid_formats = {}
    puid_versions = {}

    for results in searches["results"]:
        document = results["hits"][0]["document"]

        puid = document["puid"]
        puid_formats[puid] = document["file_format"]
        puid_versions[puid] = document.get("format_version", "")

        for count in results["facet_counts"]:
            if count["field_name"] == "size":
                puid_sizes[puid] = count["stats"]["sum"]

    # Format results for report
    for puid in puids:
        version_info = {}

        version_info[fields.FIELD_PUID] = puid
        version_info[fields.FIELD_FORMAT] = puid_formats[puid]
        version_info[fields.FIELD_VERSION] = puid_versions.get("puid", "")
        version_info[fields.FIELD_COUNT] = puid_counts[puid]

        version_info[fields.FIELD_SIZE] = 0

        if puid_sizes[puid] is not None:
            version_info[fields.FIELD_SIZE] = puid_sizes[puid]

        report[fields.FIELD_FORMAT_VERSIONS].append(version_info)

    return report
