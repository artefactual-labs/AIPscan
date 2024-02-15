from datetime import datetime

from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import (
    fields,
    get_storage_location_description,
    get_storage_service_name,
)
from AIPscan.models import AIP


def formats_count(storage_service_id, storage_location_id, start_date, end_date):
    report = {}

    report[fields.FIELD_FORMATS] = []
    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)
    report[fields.FIELD_STORAGE_LOCATION] = get_storage_location_description(
        storage_location_id
    )

    # Assemble filter_by
    if type(start_date) is datetime:
        start_timestamp = ts_helpers.datetime_to_timestamp_int(start_date)
        end_timestamp = ts_helpers.datetime_to_timestamp_int(end_date) - 1
    else:
        start_timestamp = ts_helpers.date_string_to_timestamp_int(start_date)
        end_timestamp = ts_helpers.date_string_to_timestamp_int(end_date) - 1

    filters = [
        ("date_created", ">", start_timestamp),
        ("date_created", "<", end_timestamp),
        ("storage_service_id", "=", storage_service_id),
        ("file_type", "=", "'original'"),
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
            "facet_by": ",".join(ts_helpers.FACET_FIELDS["file"]),
            "max_facet_values": 10000,
        },
    )

    value_counts = ts_helpers.facet_value_counts(results, "file_format")

    # Request total size of files for each file format
    search_requests = {"searches": []}
    for file_format in value_counts.keys():
        format_filters = filters.copy()
        format_filters.append(("file_format", "=", f"`{file_format}`"))

        format_filter_by = ts_helpers.assemble_filter_by(format_filters)

        search_requests["searches"].append(
            {
                "collection": "aipscan_file",
                "q": "*",
                "include_fields": "file_format",
                "filter_by": format_filter_by,
                "facet_by": ",".join(ts_helpers.FACET_FIELDS["file"]),
                "max_facet_values": 10000,
            }
        )

    searches = ts_helpers.client().multi_search.perform(search_requests, {})

    # Summarize file format sizes
    format_size_sums = {}
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
            fields.FIELD_SIZE: format_size_sums[file_format],
        }

    report[fields.FIELD_FORMATS] = list(format_data.values())

    return report


def largest_aips(storage_service_id, start_date, end_date, storage_location_id, limit):
    report = {}

    report[fields.FIELD_AIPS] = []
    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)
    report[fields.FIELD_STORAGE_LOCATION] = get_storage_location_description(
        storage_location_id
    )

    # Assemble filter_by
    if type(start_date) is datetime:
        start_timestamp = ts_helpers.datetime_to_timestamp_int(start_date)
        end_timestamp = ts_helpers.datetime_to_timestamp_int(end_date) - 1
    else:
        start_timestamp = ts_helpers.date_string_to_timestamp_int(start_date)
        end_timestamp = ts_helpers.date_string_to_timestamp_int(end_date) - 1

    filters = [
        ("create_date", ">", start_timestamp),
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
    storage_service_id, start_date, end_date, storage_location_id, file_type, limit
):
    report = {}

    report[fields.FIELD_FILES] = []
    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)
    report[fields.FIELD_STORAGE_LOCATION] = get_storage_location_description(
        storage_location_id
    )

    # Assemble filter_by
    if type(start_date) is datetime:
        start_timestamp = ts_helpers.datetime_to_timestamp_int(start_date)
        end_timestamp = ts_helpers.datetime_to_timestamp_int(end_date) - 1
    else:
        start_timestamp = ts_helpers.date_string_to_timestamp_int(start_date)
        end_timestamp = ts_helpers.date_string_to_timestamp_int(end_date) - 1

    filters = [
        ("date_created", ">", start_timestamp),
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
            file_info[fields.FIELD_FORMAT] = hit["document"]["file_type"]
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
