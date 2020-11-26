# -*- coding: utf-8 -*-

"""Report on who ingested AIPs and when. An indication is also provided
about how long they took to process.
"""
from flask import render_template, request
import pandas as pd
import plotly.express as px


from AIPscan.Data import report_data
from AIPscan.helpers import _simplify_datetime
from AIPscan.Reporter import reporter, request_params


# Request parameters.
STORAGE_SERVICE_ID = "storage_service_id"

# Response fields.
INGESTS = "Ingests"
STORAGE_SERVICE = "StorageName"
INGEST_START_DATE = "IngestStartDate"
INGEST_FINISH_DATE = "IngestFinishDate"
USER = "User"
DURATION = "duration"
TRANSFER_COUNT = "transfer_count"
FIGURE_HTML = "figure"

# Error response for the Gantt chart. Because the chart itself is
# returned as HTML we have the opportunity to inject a useful string
# for those using the report incorrectly, e.g. not requesting a valid
# storage service.
ERR_HTM = "<div>There is no data for this chart, please check you are looking at a valid storage service.</div>"


def get_table_data(ingests):
    """Format the data needed for an ingest log table and augment it
    where needed.
    """
    transfer_count = 0
    for ingest in ingests[INGESTS]:
        transfer_count = transfer_count + 1
        start_date = ingest[INGEST_START_DATE]
        end_date = ingest[INGEST_FINISH_DATE]
        start_date_obj = _simplify_datetime(start_date)
        end_date_obj = _simplify_datetime(end_date)
        ingest[DURATION] = end_date_obj - start_date_obj
    ingests[TRANSFER_COUNT] = transfer_count
    return ingests


@reporter.route("/ingest_log_tabular/", methods=["GET"])
def ingest_log_tabular():
    """Return the information needed to present an ingest gantt chart."""
    TABULAR_TEMPLATE = "report_ingest_log_tabular.html"
    storage_service_id = request.args.get(request_params[STORAGE_SERVICE_ID])
    ingests = report_data.agents_transfers(storage_service_id)
    ingests = get_table_data(ingests)
    return render_template(
        TABULAR_TEMPLATE,
        storage_service_name=ingests[STORAGE_SERVICE],
        number_of_transfers=ingests[TRANSFER_COUNT],
        data=ingests[INGESTS],
    )


def get_figure_html(ingests):
    """Augment the ingest log data and append the Gantt's HTML source
    for printing in the report template.
    """
    pd_list = []
    transfer_count = 0
    for ingest in ingests[INGESTS]:
        transfer_count = transfer_count + 1
        pd_list.append(
            dict(
                User=ingest[USER],
                Start=ingest[INGEST_START_DATE],
                Finish=ingest[INGEST_FINISH_DATE],
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
    GANTT_TEMPLATE = "report_ingest_log_gantt.html"
    storage_service_id = request.args.get(request_params[STORAGE_SERVICE_ID])
    ingests = report_data.agents_transfers(storage_service_id)
    ingests = get_figure_html(ingests)
    return render_template(
        GANTT_TEMPLATE,
        storage_service_name=ingests[STORAGE_SERVICE],
        number_of_transfers=ingests[TRANSFER_COUNT],
        plot=ingests[FIGURE_HTML],
    )
