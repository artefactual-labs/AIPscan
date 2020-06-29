# -*- coding: utf-8 -*-

from datetime import datetime as dt

from itertools import chain

from dash.dependencies import Input
from dash.dependencies import Output

import numpy as np

import pandas as pd
import pandas_datareader as pdr
from pandas.io import json as pd_json

import plotly.express as px
import plotly.graph_objs as go

from .sample_data import aip_formats


def prepare_aip_formats():
    df = pd_json.read_json(aip_formats)
    df = pd.DataFrame(
        {
            "AIP": np.repeat(df.AIP.values, df.Formats.str.len()),
            "Frequency": list(chain.from_iterable(df.Frequency)),
            "Format": list(chain.from_iterable(df.Formats)),
        }
    )
    return df


df_scatter_two = prepare_aip_formats()


def register_callbacks(aipscan):
    @aipscan.callback(
        Output("aip-scatter-report", "figure"), [Input("aip-dropdown", "value")]
    )
    def make_figure(selected_dropdown_value):
        # TODO: This filter can be better placed more globally for used by
        # more functions. This could also be driven by the API endpoint.
        df_scatter = df_scatter_two
        if selected_dropdown_value.lower() != "all":
            filter_ = df_scatter_two["AIP"] == selected_dropdown_value
            df_scatter = df_scatter_two[filter_]
        return px.scatter(
            data_frame=df_scatter,
            x="Format",
            y="Frequency",
            size="Frequency",
            color="Frequency",
            hover_name="AIP",
            size_max=60,
            log_y=True,
        )
