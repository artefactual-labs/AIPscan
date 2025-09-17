import tempfile

import pandas as pd
import plotly.express as px
from flask import render_template
from flask import request
from flask import send_file

from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_bool
from AIPscan.helpers import parse_datetime_bound
from AIPscan.Reporter import download_csv
from AIPscan.Reporter import format_size_for_csv
from AIPscan.Reporter import get_display_end_date
from AIPscan.Reporter import reporter
from AIPscan.Reporter import request_params
from AIPscan.Reporter import translate_headers

FIGURE_HTML = "figure"
ERR_HTML = "<div>There is no data for this chart, please check you are looking at a valid storage service.</div>"

HEADERS = [
    fields.FIELD_UUID,
    fields.FIELD_STORAGE_LOCATION,
    fields.FIELD_AIPS,
    fields.FIELD_SIZE,
    fields.FIELD_FILE_COUNT,
]


@reporter.route("/storage_locations/", methods=["GET"])
def storage_locations():
    """Return AIPs containing file format, sorted by count and total size."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    locations_data = report_data.storage_locations(
        storage_service_id=storage_service_id, start_date=start_date, end_date=end_date
    )
    locations = locations_data.get(fields.FIELD_LOCATIONS)

    if csv:
        headers = translate_headers(HEADERS, True)

        filename = "storage_locations.csv"
        csv_data = format_size_for_csv(locations)
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(HEADERS)

    return render_template(
        "report_storage_locations.html",
        storage_service_id=storage_service_id,
        storage_service_name=locations_data.get(fields.FIELD_STORAGE_NAME),
        columns=headers,
        locations=locations,
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )


def _get_line_chart_figure_html(locations, metric="aips"):
    """Return partial HTML of bar chart plot and the underlying pandas df."""
    table_dict = {"days": [], "aips": [], "size": [], "files": [], "location": []}
    for day, locations_data in locations.items():
        for location in locations_data:
            table_dict["days"].append(day)
            table_dict["aips"].append(location.get(fields.FIELD_AIPS, 0))
            # Display size in GB
            table_dict["size"].append(location.get(fields.FIELD_SIZE, 0) / 1000000)
            table_dict["files"].append(location.get(fields.FIELD_FILE_COUNT, 0))
            table_dict["location"].append(
                "{} ({})".format(location["StorageLocation"], location["UUID"])
            )

    df = pd.DataFrame(table_dict)
    fig = px.line(df, x="days", y=metric, color="location", markers=True)
    return fig.to_html(full_html=False), df


@reporter.route("/storage_locations_usage_over_time/", methods=["GET"])
def storage_location_usage_over_time():
    """Return the information needed to present a timeseries line chart."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    csv = parse_bool(request.args.get(request_params.CSV), default=False)
    request_metric = request.args.get(request_params.METRIC, "aips")
    cumulative = parse_bool(request.args.get(request_params.CUMULATIVE), default=False)

    # Determine which metric we're looking to chart.
    metric = "aips"
    if request_metric in ("files", "size"):
        metric = request_metric

    locations_data = report_data.storage_locations_usage_over_time(
        storage_service_id=storage_service_id,
        start_date=start_date,
        end_date=end_date,
        cumulative=cumulative,
    )

    html_figure, dataframe = _get_line_chart_figure_html(
        locations_data.get(fields.FIELD_LOCATIONS_USAGE_OVER_TIME), metric=metric
    )

    if csv:
        # Use the pandas dataframe created as part of plotting our timeseries
        # to download a CSV containing the data underpinning the chart that is
        # currently displayed to the user in the UI.
        filename = "storage_locations_usage_over_time.csv"
        with tempfile.NamedTemporaryFile() as tmp:
            dataframe.to_csv(tmp.name, encoding="utf-8", index=False)
            return send_file(
                tmp.name,
                mimetype="text/csv",
                as_attachment=True,
                download_name=filename,
            )

    return render_template(
        "report_storage_locations_usage_over_time.html",
        storage_service_id=storage_service_id,
        storage_service_name=locations_data.get(fields.FIELD_STORAGE_NAME),
        plot=html_figure,
        start_date=start_date,
        end_date=get_display_end_date(end_date),
        metric=metric,
        cumulative=cumulative,
    )
