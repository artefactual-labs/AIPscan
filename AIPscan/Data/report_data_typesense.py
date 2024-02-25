from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import (
    fields,
    report_dict,
)


def formats_count(storage_service_id, storage_location_id, start_date, end_date):
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
