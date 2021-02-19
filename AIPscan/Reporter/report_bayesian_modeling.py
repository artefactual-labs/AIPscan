# -*- coding: utf-8 -*-

"""Report Bayesian formats provides the user with information on the
distribution of a specific file format (PUID) over time. Through the
lens of this distribution we might understand more about when a format
first came into existence - when a format was abundant - and signs that
the format is on its way to becoming obsolete.

Based on Nick Krabbenhoeft's "Bayesian Modeling of File Format
Obsolescence"
"""

import base64
from datetime import datetime
from io import BytesIO

import seaborn as sns
from flask import render_template, request
from matplotlib import pyplot as plt

from AIPscan.Data import fields, report_data
from AIPscan.Reporter import reporter, request_params

sns.set_theme()


def retrieve_year(date):
    """Retrieve year from date."""
    return datetime.strptime(date, "%Y-%m-%d").strftime("%Y")


SIGNIFICANT_RESULTS = 10


def save_rug_plots(format_report, significant_results=SIGNIFICANT_RESULTS):
    """Return Base64 encoded figures to caller

    :param format_report: Bayesian format modeling report.
    :param significant_results: Number of results worth returning in
        these reports, e.g. 1 does not tell us a lot of information.

    :returns: Empty array or array of Base64 encoded images to be
        rendered.
    """

    # Seaborn setup.
    sns.set(rc={"figure.figsize": (30, 8)})
    sns.set_theme(style="ticks", palette="icefire")

    # Process AIP format data.
    all_aips = format_report.get(fields.FIELD_ALL_AIPS, [])
    plot_output = []
    dates = []
    idx = 0
    for idx, aip in enumerate(all_aips):
        dates = []
        PUID = aip.get(fields.FIELD_PUID)
        format_dates = aip.get(fields.FIELD_CREATED_DATES)
        if len(format_dates) <= significant_results:
            continue
        year = [int(retrieve_year(date)) for date in format_dates]
        dates.extend(year)
        fig, axes = plt.subplots()

        # Setup axes to be useful to the reader.
        min_date = min(dates) - 10
        max_date = max(dates) + 10
        axes.set_xlim(min_date, max_date)
        axes.set_xticks(range(min_date, max_date, 5))

        # Plot our chart.
        plot = sns.rugplot(data=dates, height=1, y=None, x=dates, legend=True, ax=axes)
        plot.set(yticklabels=[])

        # Save the chart image to memory.
        img = BytesIO()
        fig.savefig(img, bbox_inches="tight", pad_inches=0.3, transparent=True)
        fig.clf()
        img.seek(0)

        # Convert bytes to Base64 encoding for rendering later.
        plot = base64.b64encode(img.getvalue()).decode("utf8")
        plot_output.append({PUID: plot})

    return plot_output


@reporter.route("/bayesian_rug_plot/", methods=["GET"])
def report_bayesian_modeling_rug():
    """Bayesian format modeling rug plot."""

    storage_service_id = request.args.get(request_params["storage_service_id"])

    format_report = report_data.bayesian_format_modeling(storage_service_id)
    figures = save_rug_plots(format_report)

    return render_template(
        "bayesian_rug_plot.html",
        storage_service_id=storage_service_id,
        storage_service_name=format_report.get(fields.FIELD_STORAGE_NAME),
        figures=figures,
    )
