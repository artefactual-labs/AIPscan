# -*- coding: utf-8 -*-

import json

import pytest

from AIPscan.Reporter.report_bayesian_modeling import save_rug_plots

format_report = """
{
    "AllAIPs": [
        {
            "CreatedDates": [
                "2020-02-11",
                "2020-02-11",
                "2019-09-16",
                "2019-09-16"
            ],
            "PUID": "fmt/199",
            "Format": "MPEG-4 Media File None"
        },
        {
            "CreatedDates": [
                "2020-01-15",
                "2020-03-04",
                "2020-01-08",
                "2018-08-09",
                "1987-07-27",
                "2018-08-09"
            ],
            "PUID": "x-fmt/111",
            "Format": "Plain Text None"
        },
        {
            "CreatedDates": [
                "2018-08-02",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2020-01-08",
                "2018-08-09",
                "2018-01-22",
                "2018-01-31",
                "2019-02-25",
                "2018-08-02",
                "2020-11-19",
                "1986-03-11",
                "2018-08-09",
                "2020-01-08",
                "2020-01-08"
            ],
            "PUID": "fmt/43",
            "Format": "JPEG 1.01"
        }
    ]
}
"""


@pytest.mark.parametrize(
    "number_of_significant_results, length_of_results, keys_to_test",
    [
        # Threshold for significant results means that all results are
        # returned.
        (0, 3, ["fmt/199", "x-fmt/111", "fmt/43"]),
        # Threshold for significant results means that two results are
        # returned.
        (5, 2, ["x-fmt/111", "fmt/43"]),
        # Threshold for significant results means that one result is
        # returned.
        (10, 1, ["fmt/43"]),
        # Threshold for significant results means zero results are
        # returned.
        (24, 0, []),
    ],
)
def test_save_rug_plots(
    mocker, number_of_significant_results, length_of_results, keys_to_test
):
    """Ensure that we retrieve the correctly shaped data for the rug
    plot report.
    """
    format_report_json = json.loads(format_report)

    ENCODED_DATA = "encoded data"

    mocker.patch("base64.b64encode", return_value=ENCODED_DATA.encode("utf8"))
    result = save_rug_plots(format_report_json, number_of_significant_results)

    if length_of_results == 0 and len(result) == 0:
        # Output is as was expected, we can happily return from here.
        return

    assert len(result) == length_of_results

    puids = []
    for res in result:
        puids.extend(res.keys())
        assert [*res.values()][0] == ENCODED_DATA

    assert set(puids) == set(keys_to_test)
