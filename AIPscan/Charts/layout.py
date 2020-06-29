# -*- coding: utf-8 -*-

from itertools import chain
import requests

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
from pandas.io import json as pd_json
import plotly.graph_objs as go
import plotly.express as px

from .sample_data import aip_density, aip_formats
from .create_menus import get_aip_opts, create_traces
from .callbacks import prepare_aip_formats

report_title_md = """
# AM test report...

Using dash to create reports for Archivematica. This text is written in
Markdown!
"""

density_report_title = """
## AIP density report
"""

density_report_summary = """
**Summary:** The density report helps us to identify the trend in AIP profile
with regards to size on disk, and number of formats.
"""

scatter_report_title = """
## AIP scatter graph summary
"""

scatter_report_summary = """
**Summary:** The scatter graph report shows us the format breakdown and volume
per AIP and can be filtered by AIP.
"""

stacked_report_title = """
## A stacked bar-chart of file formats
"""

stacked_report_summary = """
**Summary:** The stacked bar graph summary again shows us the breakdown of
file formats per AIP but can be filtered by FMT.
"""

# AIP density data.
df_aip_density = pd_json.read_json(aip_density)

# AIP scatter graph data.
df_scatter = prepare_aip_formats()

# Format stacked bar chart data.
format_stack_data = create_traces()


layout = html.Div(
    [
        dcc.Markdown(children=report_title_md),
        html.Div(
            [
                dcc.Markdown(children=density_report_title, className="report_title"),
                html.P(children=density_report_summary, className="test_style"),
                dcc.Graph(
                    id="density-report",
                    figure=px.density_heatmap(df_aip_density, x="Size", y="No_files"),
                ),
            ]
        ),
        html.Div(
            [
                dcc.Markdown(children=scatter_report_title, className="report_title"),
                html.P(children=scatter_report_summary, className="test_style"),
                dcc.Dropdown(id="aip-dropdown", options=get_aip_opts(), value="All"),
                dcc.Graph(id="aip-scatter-report"),
            ]
        ),
        html.Div(
            [
                dcc.Markdown(children=stacked_report_title, className="report_title"),
                html.P(children=stacked_report_summary, className="test_style"),
                dcc.Graph(
                    id="stacked-formats-report",
                    figure={
                        "data": format_stack_data,
                        "layout": go.Layout(barmode="stack"),
                    },
                ),
            ]
        ),
    ],
    className="page",
)
