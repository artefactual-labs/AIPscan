"""Report on who ingested AIPs and when. An indication is also provided
about how long they took to process.
"""

import pandas as pd
import plotly.express as px
from flask import render_template
from flask import request

from AIPscan.Data import fields
from AIPscan.Data import report_data
from AIPscan.helpers import _simplify_datetime
from AIPscan.helpers import parse_bool
from AIPscan.helpers import parse_datetime_bound
from AIPscan.Reporter import download_csv
from AIPscan.Reporter import get_display_end_date
from AIPscan.Reporter import reporter
from AIPscan.Reporter import request_params
from AIPscan.Reporter import translate_headers

# Response fields.
TRANSFER_COUNT = "transfer_count"
FIGURE_HTML = "figure"

# Error response for the Gantt chart. Because the chart itself is
# returned as HTML we have the opportunity to inject a useful string
# for those using the report incorrectly, e.g. not requesting a valid
# storage service.
ERR_HTM = "<div>There is no data for this chart, please check you are looking at a valid storage service.</div>"

CSV_HEADERS = [
    fields.FIELD_AIP_UUID,
    fields.FIELD_AIP_NAME,
    fields.FIELD_DATE_START,
    fields.FIELD_DATE_END,
    fields.FIELD_USER,
    fields.FIELD_DURATION,
]


def get_table_data(ingests):
    """Format the data needed for an ingest log table and augment it
    where needed.
    """
    transfer_count = 0
    for ingest in ingests[fields.FIELD_INGESTS]:
        transfer_count = transfer_count + 1
        start_date = ingest[fields.FIELD_DATE_START]
        end_date = ingest[fields.FIELD_DATE_END]
        start_date_obj = _simplify_datetime(start_date)
        end_date_obj = _simplify_datetime(end_date)
        ingest[fields.FIELD_DURATION] = end_date_obj - start_date_obj
    ingests[TRANSFER_COUNT] = transfer_count
    return ingests


@reporter.route("/ingest_log_tabular/", methods=["GET"])
def ingest_log_tabular():
    """Return the information needed to present an ingest gantt chart."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    ingests = report_data.agents_transfers(
        storage_service_id, start_date, end_date, storage_location_id
    )
    ingests = get_table_data(ingests)

    if csv:
        filename = "user_ingest_log.csv"
        headers = translate_headers(CSV_HEADERS)
        return download_csv(headers, ingests[fields.FIELD_INGESTS], filename)

    return render_template(
        "report_ingest_log_tabular.html",
        storage_service_name=ingests.get(fields.FIELD_STORAGE_NAME),
        storage_location_description=ingests.get(fields.FIELD_STORAGE_LOCATION),
        number_of_transfers=ingests[TRANSFER_COUNT],
        data=ingests[fields.FIELD_INGESTS],
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )


def get_figure_html(ingests):
    """Augment the ingest log data and append the Gantt's HTML source
    for printing in the report template.
    """
    pd_list = []
    transfer_count = 0
    for ingest in ingests[fields.FIELD_INGESTS]:
        transfer_count = transfer_count + 1
        pd_list.append(
            dict(
                User=ingest[fields.FIELD_USER],
                Start=ingest[fields.FIELD_DATE_START],
                Finish=ingest[fields.FIELD_DATE_END],
            )
        )
    if not pd_list:
        ingests[FIGURE_HTML] = ERR_HTM
        ingests[TRANSFER_COUNT] = transfer_count
        return ingests
    df = pd.DataFrame(pd_list)
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="User")
    fig.update_yaxes(autorange="reversed")
    ingests[FIGURE_HTML] = fig.to_html(full_html=False)
    ingests[TRANSFER_COUNT] = transfer_count
    return ingests


@reporter.route("/ingest_log_gantt/", methods=["GET"])
def ingest_log():
    """Return the information needed to present an ingest gantt chart."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    ingests = report_data.agents_transfers(
        storage_service_id, start_date, end_date, storage_location_id
    )
    ingests = get_figure_html(ingests)
    return render_template(
        "report_ingest_log_gantt.html",
        storage_service_name=ingests.get(fields.FIELD_STORAGE_NAME),
        storage_location_description=ingests.get(fields.FIELD_STORAGE_LOCATION),
        number_of_transfers=ingests[TRANSFER_COUNT],
        plot=ingests[FIGURE_HTML],
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )
