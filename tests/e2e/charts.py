"""Browser checks are separate cases so a failure has one clear subject."""

import json
from urllib.parse import urlencode

from playwright.sync_api import expect

PARAMS = {"amss_id": 1, "start_date": "2000-01-01", "end_date": "2100-01-01"}


def visit(page, errors, report, **params):
    url = f"http://aipscan:5000/reporter/{report}/?{urlencode(PARAMS | params)}"
    response = page.goto(url, wait_until="networkidle")
    assert response.ok, f"{url}: HTTP {response.status}"
    assert not errors, errors


def plotly_figure(page, errors):
    plot = page.locator(".js-plotly-plot")
    expect(plot).to_be_visible()
    page.wait_for_function(
        """() => {
            const plot = document.querySelector('.js-plotly-plot');
            return plot?._fullData?.length && plot.querySelector('.main-svg');
        }"""
    )
    expect(page.locator('[data-title*="Share chart"]')).to_have_count(0)
    assert not errors, errors
    return plot


def pie(page, errors):
    visit(page, errors, "chart_formats_count")
    canvas = page.locator("#chart")
    expect(canvas).to_be_visible()
    page.wait_for_function(
        "() => window.Chart?.getChart('chart')?.getDatasetMeta(0).data.length === 2"
    )
    pie = page.evaluate(
        """() => {
            const chart = Chart.getChart('chart');
            // Finish animations before checking the rendered arcs.
            chart.update('none');
            return {labels: chart.data.labels, values: chart.data.datasets[0].data,
                arcs: chart.getDatasetMeta(0).data.map(arc => arc.circumference)};
        }"""
    )
    assert dict(zip(pie["labels"], pie["values"], strict=True)) == {
        "Plain Text": 2,
        "Unknown": 1,
    }, pie
    assert all(arc > 0 for arc in pie["arcs"]), pie
    print("Chart.js pie:", json.dumps(pie))


def scatter(page, errors):
    visit(page, errors, "plot_formats_count")
    scatter = plotly_figure(page, errors)
    expect(scatter.locator(".scatterlayer .point")).to_have_count(2)
    values = scatter.evaluate("plot => ({x: plot.data[0].x, y: plot.data[0].y})")
    assert sorted(zip(values["x"], values["y"], strict=True)) == [
        (4, 1),
        (len(b"AIPscan end-to-end test.\n") + 4, 2),
    ], values
    expect(scatter.locator(".xtitle")).to_have_text("total size in bytes")
    expect(scatter.locator(".ytitle")).to_have_text("format occurrence count")
    # Plotly handles pointer events on an overlay above the SVG points.
    point = scatter.locator(".scatterlayer .point").first.bounding_box()
    assert point is not None
    page.mouse.move(point["x"] + point["width"] / 2, point["y"] + point["height"] / 2)
    expect(scatter.locator(".hoverlayer .hovertext")).to_be_visible()


def timeline(page, errors):
    visit(page, errors, "ingest_log_gantt")
    timeline = plotly_figure(page, errors)
    assert timeline.locator(".barlayer .point").count() > 0
    assert timeline.evaluate("plot => plot._context.showSendToCloud === false")


def time_series(page, errors):
    visit(page, errors, "storage_locations_usage_over_time")
    timeseries = plotly_figure(page, errors)
    # Plotly Express uses WebGL for larger series, including this date range.
    expect(
        timeseries.locator(".scatterlayer .js-line, .gl-container canvas").first
    ).to_be_visible()
    assert timeseries.evaluate("plot => plot._context.showSendToCloud === false")
    # _fullData contains decoded arrays even when Plotly.py uses binary encoding.
    total = timeseries.evaluate(
        "plot => plot._fullData.reduce((sum, trace) => "
        "sum + Array.from(trace.y).reduce((a, b) => a + b, 0), 0)"
    )
    assert total == 3, total
    page.locator("#metricSelector").select_option("files")
    page.wait_for_url("**/*metric=files*")
    plotly_figure(page, errors)
    page.locator("#cumulativeSelector").select_option("true")
    page.wait_for_url("**/*cumulative=true*")
    cumulative = plotly_figure(page, errors)
    total = cumulative.evaluate(
        "plot => plot._fullData.reduce((sum, trace) => sum + Array.from(trace.y).at(-1), 0)"
    )
    assert total == 3, total
    assert not errors, errors
