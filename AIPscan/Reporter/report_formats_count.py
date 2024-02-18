# -*- coding: utf-8 -*-

"""Report formats count consists of the tabular report, plot, and
chart which describe the file formats present across the AIPs in a
storage service with AIPs filtered by date range.
"""

from datetime import datetime

from flask import render_template, request

from AIPscan import typesense_helpers as ts_helpers
from AIPscan.Data import (
    fields,
    get_storage_location_description,
    get_storage_service_name,
)
from AIPscan.helpers import filesizeformat, parse_bool
from AIPscan.Reporter import (
    download_csv,
    format_size_for_csv,
    reporter,
    request_params,
    translate_headers,
)

HEADERS = [fields.FIELD_FORMAT, fields.FIELD_COUNT, fields.FIELD_SIZE]


def _formats_data(storage_service_id, storage_location_id, start_date, end_date):
    # Assemble filter_by
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
                if count["field_name"] == "file_format":
                    format_size_sums[file_format] = count["counts"][0]["count"]

    # Amalgamate data
    format_data = {}

    for file_format in value_counts.keys():
        format_data[file_format] = {
            fields.FIELD_FORMAT: file_format,
            fields.FIELD_COUNT: value_counts[file_format],
            fields.FIELD_SIZE: format_size_sums[file_format],
        }

    return format_data


@reporter.route("/report_formats_count/", methods=["GET"])
def report_formats_count():
    """Report (tabular) on all file formats and their counts and size on
    disk across all AIPs in the storage service.
    """
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)

    start_date = request.args.get(request_params.START_DATE)
    end_date = request.args.get(request_params.END_DATE)

    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    formats_data = _formats_data(
        storage_service_id, storage_location_id, start_date, end_date
    )

    if csv:
        headers = translate_headers(HEADERS, True)

        filename = "file_formats.csv"
        csv_data = format_size_for_csv(formats_data.values())
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(HEADERS)

    total_file_count = sum(
        formats_data[file_format][fields.FIELD_COUNT]
        for file_format in formats_data.keys()
    )
    total_file_size = sum(
        formats_data[file_format][fields.FIELD_SIZE]
        for file_format in formats_data.keys()
    )

    return render_template(
        "report_formats_count.html",
        storage_service_id=storage_service_id,
        storage_service_name=get_storage_service_name(storage_service_id),
        storage_location_description=get_storage_location_description(
            storage_location_id
        ),
        columns=headers,
        formats=formats_data,
        total_file_count=total_file_count,
        total_size=total_file_size,
        formats_count=len(formats_data),
        start_date=datetime.strptime(start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(end_date, "%Y-%m-%d"),
    )


@reporter.route("/chart_formats_count/", methods=["GET"])
def chart_formats_count():
    """Report (pie chart) on all file formats and their counts and size
    on disk across all AIPs in the storage service."""
    start_date = request.args.get(request_params.START_DATE)
    end_date = request.args.get(request_params.END_DATE)

    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)

    formats_data = _formats_data(
        storage_service_id, storage_location_id, start_date, end_date
    )
    labels = list(formats_data.keys())
    values = [
        formats_data[file_format][fields.FIELD_COUNT] for file_format in formats_data
    ]

    different_formats = len(labels)
    originals_count = sum(
        formats_data[file_format][fields.FIELD_COUNT]
        for file_format in formats_data.keys()
    )

    return render_template(
        "chart_formats_count.html",
        startdate=start_date,
        enddate=end_date,
        storage_service_name=get_storage_service_name(storage_service_id),
        storage_location_description=get_storage_location_description(
            storage_location_id
        ),
        labels=labels,
        values=values,
        originalsCount=originals_count,
        differentFormats=different_formats,
    )


@reporter.route("/plot_formats_count/", methods=["GET"])
def plot_formats_count():
    """Report (scatter) on all file formats and their counts and size on
    disk across all AIPs in the storage service.
    """
    start_date = request.args.get(request_params.START_DATE)
    end_date = request.args.get(request_params.END_DATE)

    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)

    format_data = _formats_data(
        storage_service_id, storage_location_id, start_date, end_date
    )

    # Assemble plot data
    total_count = 0
    total_size = 0
    x_axis = []
    y_axis = []
    file_format = []
    human_size = []

    for file_format in format_data.keys():
        y_axis.append(format_data[file_format][fields.FIELD_COUNT])
        total_count += format_data[file_format][fields.FIELD_COUNT]

        size = format_data[file_format][fields.FIELD_SIZE]
        if size is None:
            size = 0
        x_axis.append(size)

        total_size += size
        human_size.append(filesizeformat(size))

    # Determine summary data
    file_formats = list(format_data.keys())
    different_formats = len(file_formats)
    total_human_size = filesizeformat(total_size)
    originals_count = total_count

    format_count = {}
    for file_format in format_data:
        format_count[file_format] = format_data[file_format][fields.FIELD_COUNT]

    return render_template(
        "plot_formats_count.html",
        startdate=start_date,
        enddate=end_date,
        storage_service_name=get_storage_service_name(storage_service_id),
        storage_location_description=get_storage_location_description(
            storage_location_id
        ),
        originalsCount=originals_count,
        formatCount=format_count,
        differentFormats=different_formats,
        totalHumanSize=total_human_size,
        x_axis=x_axis,
        y_axis=y_axis,
        format=file_formats,
        humansize=human_size,
    )
