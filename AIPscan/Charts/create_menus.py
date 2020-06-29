# -*- coding: utf-8 -*-

import json

import pandas as pd

import plotly.graph_objs as go

from .sample_data import aip_density, aip_formats
from .callbacks import prepare_aip_formats


def get_aip_opts():
    """Return the AIP options for the AIP callbacks."""
    AIPIDX = "AIP"
    aip_fmts = json.loads(aip_formats)
    aips = aip_fmts[AIPIDX].values()
    opts = []
    opts.append({"label": "All", "value": "All"}),
    for aip in aips:
        opts.append({"label": aip[:8], "value": aip})
    return opts


def create_traces():
    """Return buckets for stacked bar charts."""
    af = prepare_aip_formats()
    pv = pd.pivot_table(
        af[:-1],
        index=["AIP"],
        columns=["Format"],
        values=["Frequency"],
        aggfunc=sum,
        fill_value=0,
    )
    unique_formats = af[:-1].Format.unique()
    traces = []
    for u in unique_formats:
        traces.append(go.Bar(x=pv.index, y=pv[("Frequency", u)], name=u))
    return traces
