# -*- coding: utf-8 -*-

from datetime import datetime
from flask import render_template, request
import pandas as pd
import plotly.express as px

from AIPscan.Data import data
from AIPscan.Reporter import reporter, translate_headers


def get_aip_data_and_params_from_request(request):
    """Return data and formatted params for use in views from request.

    :param request: Flask request object

    :returns: Report data (dict), formatted params (dict)
    """
    storage_service_id = request.args.get("amss_id")
    file_format = request.args.get("file_format")

    start_date = request.args.get("start_date")
    if start_date is not None:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            # TODO: Log error for invalid start_date value
            start_date = None

    end_date = request.args.get("end_date")
    if end_date is not None:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            # TODO: Log error for invalid end_date value
            end_date = None

    aip_data = data.aips_by_file_format(
        storage_service_id=storage_service_id,
        file_format=file_format,
        start_date=start_date,
        end_date=end_date,
    )
    params = {
        "storage_service_id": storage_service_id,
        "file_format": file_format,
        "start_date": start_date,
        "end_date": end_date,
    }
    return aip_data, params


@reporter.route("/aips_by_file_format/table/", methods=["GET"])
def aips_by_format():
    """Return AIPs containing file format, sorted by count and total size."""
    aip_data, params = get_aip_data_and_params_from_request(request)
    storage_service_name = aip_data[data.FIELD_STORAGE_NAME]
    headers = [data.FIELD_AIP_NAME, data.FIELD_UUID, data.FIELD_COUNT, data.FIELD_SIZE]
    return render_template(
        "report_aips_by_format.html",
        storage_service_id=params.get("storage_service_id"),
        storage_service_name=storage_service_name,
        file_format=params.get("file_format"),
        columns=translate_headers(headers),
        aips=aip_data[data.FIELD_AIPS],
        start_date=params.get("start_date"),
        end_date=params.get("end_date"),
    )


@reporter.route("/aips_by_file_format/chart/", methods=["GET"])
def aips_by_format_chart():
    aip_data, params = get_aip_data_and_params_from_request(request)
    storage_service_name = aip_data[data.FIELD_STORAGE_NAME]

    df = pd.DataFrame(aip_data[data.FIELD_AIPS])
    fig = px.pie(
        df,
        values=data.FIELD_COUNT,
        names=data.FIELD_AIP_NAME_WITH_UUID,
        hover_data={data.FIELD_SIZE},
        labels={
            data.FIELD_SIZE: "Total size (bytes)",
            data.FIELD_AIP_NAME_WITH_UUID: "AIP",
        },
    )
    fig.update_traces(hoverinfo="label+name", textinfo="value")
    div = fig.to_html(full_html=False)

    return render_template(
        "chart_aips_by_format.html",
        storage_service_id=params.get("storage_service_id"),
        storage_service_name=storage_service_name,
        file_format=params.get("file_format"),
        start_date=params.get("start_date"),
        end_date=params.get("end_date"),
        chart_div=div,
    )
