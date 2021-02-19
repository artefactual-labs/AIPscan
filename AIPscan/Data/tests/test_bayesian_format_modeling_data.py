# -*- coding: utf-8 -*-

from AIPscan.Data import fields, report_data
from AIPscan.Data.tests import MOCK_STORAGE_SERVICE_ID

TEST_STORAGE_SERVICE = "test storage service"


def test_bayesian_modeling_data_one(app_with_populated_files,):
    """Ensure that the data returned fro the Bayesian format modeling
    endpoint is returned as expected for our first application fixture
    with just one format recorded.
    """
    report = report_data.bayesian_format_modeling(
        storage_service_id=MOCK_STORAGE_SERVICE_ID
    )

    assert report[fields.FIELD_STORAGE_NAME] == TEST_STORAGE_SERVICE
    assert len(report[fields.FIELD_ALL_AIPS]) == 1
    assert (
        report[fields.FIELD_ALL_AIPS][0][fields.FIELD_FORMAT]
        == "Tagged Image File Format 0.0.0"
    )
    assert report[fields.FIELD_ALL_AIPS][0][fields.FIELD_PUID] == "fmt/353"
    assert len(report[fields.FIELD_ALL_AIPS][0][fields.FIELD_CREATED_DATES]) == 2


def test_bayesian_modeling_data_two(app_with_populated_format_versions,):
    """Ensure that the data returned fro the Bayesian format modeling
    endpoint is returned as expected for our second application fixture
    with three formats recorded.
    """
    report = report_data.bayesian_format_modeling(
        storage_service_id=MOCK_STORAGE_SERVICE_ID
    )

    assert report[fields.FIELD_STORAGE_NAME] == TEST_STORAGE_SERVICE
    assert len(report[fields.FIELD_ALL_AIPS]) == 3

    formats = ["JPEG 1.01", "JPEG 1.02", "ISO Disk Image File"]
    puids = ["fmt/43", "fmt/44", "fmt/468"]
    dates = [["1970-01-03", "1970-01-03"], ["1970-01-04"], ["1970-01-05"]]

    result_formats = [
        item[fields.FIELD_FORMAT] for item in report[fields.FIELD_ALL_AIPS]
    ]
    result_puids = [item[fields.FIELD_PUID] for item in report[fields.FIELD_ALL_AIPS]]
    result_dates = [
        item[fields.FIELD_CREATED_DATES] for item in report[fields.FIELD_ALL_AIPS]
    ]

    assert set(formats) == set(result_formats)
    assert set(puids) == set(result_puids)

    assert dates[0] in result_dates
    assert dates[1] in result_dates
    assert dates[2] in result_dates
