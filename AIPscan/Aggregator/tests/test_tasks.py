# -*- coding: utf-8 -*-

from datetime import datetime

import pytest

from AIPscan.Aggregator import tasks


@pytest.mark.parametrize(
    "input_date,output_date,now_year",
    [
        ("2020-05-19T08:04:16+00:00", "2020-05-19T08:04:16", False),
        ("2020-07-30T13:27:45.757482+00:00", "2020-07-30T13:27:45", False),
        ("2020-07-30", "2020-07-30T00:00:00", False),
        ("T13:27:45", "", True),
        ("こんにちは世界", "1970-01-01T00:00:01", False),
    ],
)
def test_tz_neutral_dates(input_date, output_date, now_year):
    result_date = tasks._tz_neutral_date(input_date)
    if now_year is True:
        year = datetime.now().strftime("%Y-%m-%d")
        output_date = "{}{}".format(year, input_date)
        output_date = datetime.strptime(output_date, "%Y-%m-%dT%H:%M:%S")
        assert result_date == output_date
    else:
        output_date = datetime.strptime(output_date, "%Y-%m-%dT%H:%M:%S")
        assert result_date == output_date
