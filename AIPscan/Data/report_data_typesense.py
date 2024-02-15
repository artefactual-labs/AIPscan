from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import fields, report_dict
from AIPscan.models import AIP


def formats_count(
    storage_service_id,
    storage_location_id,
    start_date,
    end_date,
    include_size_data=True,
):
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMATS] = []

    file_filters = ts_helpers.file_filters(
        storage_service_id, storage_location_id, start_date, end_date
    )

    # Get format counts via facet data
    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": ts_helpers.assemble_filter_by(file_filters),
            "include_fields": "",
            "facet_by": ",".join(ts_helpers.FACET_FIELDS["file"]),
            "max_facet_values": 10000,
        },
    )

    value_counts = ts_helpers.facet_value_counts(results, "file_format")

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
                    "facet_by": ",".join(ts_helpers.FACET_FIELDS["file"]),
                    "max_facet_values": 10000,
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

    # Amalgamate data
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

    # Get format counts via facet data
    results = ts_helpers.search(
        "aip",
        {
            "q": "*",
            "filter_by": filter_by,
            "include_fields": "",
            "per_page": limit,
            "sort_by": "size:desc",
        },
    )

    for hit in results["hits"]:
        report[fields.FIELD_AIPS].append(
            {
                "UUID": hit["document"]["uuid"],
                "Name": hit["document"]["transfer_name"],
                "Size": hit["document"]["size"],
                "FileCount": hit["document"]["original_file_count"],
            }
        )

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

    # Assemble filter_by
    start_timestamp = ts_helpers.datetime_to_timestamp_int(start_date)
    end_timestamp = ts_helpers.datetime_to_timestamp_int(end_date)

    filters = [
        ("date_created", ">=", start_timestamp),
        ("date_created", "<", end_timestamp),
        ("storage_service_id", "=", storage_service_id),
    ]

    if storage_location_id is not None and storage_location_id != "":
        filters.append(("storage_location_id", "=", storage_location_id))

    filter_by = ts_helpers.assemble_filter_by(filters)

    # Get format counts via facet data
    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": filter_by,
            "include_fields": "",
            "per_page": limit,
            "sort_by": "size:desc",
        },
    )

    # Format results for report
    for hit in results["hits"]:
        file_info = {}

        file_info[fields.FIELD_ID] = hit["document"]["id"]
        file_info[fields.FIELD_UUID] = hit["document"]["uuid"]
        file_info[fields.FIELD_NAME] = hit["document"]["name"]
        try:
            file_info[fields.FIELD_SIZE] = int(hit["document"]["size"])
        except TypeError:
            file_info[fields.FIELD_SIZE] = 0
        file_info[fields.FIELD_AIP_ID] = hit["document"]["aip_id"]
        file_info[fields.FIELD_FILE_TYPE] = hit["document"]["file_type"]

        try:
            file_info[fields.FIELD_FORMAT] = hit["document"]["file_format"]
        except AttributeError:
            pass
        try:
            file_info[fields.FIELD_VERSION] = hit["document"]["format_version"]
        except AttributeError:
            pass
        try:
            file_info[fields.FIELD_PUID] = hit["document"]["puid"]
        except AttributeError:
            pass

        matching_aip = AIP.query.get(hit["document"]["aip_id"])
        if matching_aip is not None:
            file_info[fields.FIELD_AIP_NAME] = matching_aip.transfer_name
            file_info[fields.FIELD_AIP_UUID] = matching_aip.uuid

        report[fields.FIELD_FILES].append(file_info)

    return report


def format_versions_count(
    storage_service_id, start_date, end_date, storage_location_id=None
):
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMAT_VERSIONS] = []

    file_filters = ts_helpers.file_filters(
        storage_service_id, storage_location_id, start_date, end_date
    )

    # Get format counts via facet data
    results = ts_helpers.search(
        "file",
        {
            "q": "*",
            "filter_by": ts_helpers.assemble_filter_by(file_filters),
            "include_fields": "puid",
            "facet_by": ",".join(ts_helpers.FACET_FIELDS["file"]),
            "max_facet_values": 10000,
        },
    )

    puid_counts = ts_helpers.facet_value_counts(results, "puid")
    puids = list(puid_counts.keys())

    # Request total size of files for each PUID
    search_requests = {"searches": []}
    for puid in puids:
        format_filters = file_filters.copy()
        format_filters.append(("puid", "=", f"`{puid}`"))

        format_filter_by = ts_helpers.assemble_filter_by(format_filters)

        search_requests["searches"].append(
            {
                "collection": ts_helpers.collection_prefix("file"),
                "q": "*",
                "include_fields": "",
                "filter_by": format_filter_by,
                "facet_by": ",".join(ts_helpers.FACET_FIELDS["file"]),
                "max_facet_values": 10000,
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

    for puid in puids:
        version_info = {}

        version_info[fields.FIELD_PUID] = puid
        version_info[fields.FIELD_FORMAT] = puid_formats[puid]

        try:
            version_info[fields.FIELD_VERSION] = puid_versions[puid]
        except AttributeError:
            pass

        version_info[fields.FIELD_COUNT] = puid_counts[puid]
        version_info[fields.FIELD_SIZE] = 0

        if puid_sizes[puid] is not None:
            version_info[fields.FIELD_SIZE] = puid_sizes[puid]

        report[fields.FIELD_FORMAT_VERSIONS].append(version_info)

    return report
