import datetime

import pytest

from tools.helpers import data


@pytest.fixture
def mock_db_add(mocker):
    mocker.patch("AIPscan.db.session.add")
    mocker.patch("AIPscan.db.session.commit")


def test_create_fake_storage_service(mock_db_add):
    ss = data.create_fake_storage_service(True)

    assert ss.name
    assert type(ss.name) is str

    assert ss.url
    assert type(ss.url) is str

    assert ss.user_name
    assert type(ss.user_name) is str

    assert ss.api_key
    assert type(ss.api_key) is str

    assert ss.default
    assert type(ss.default) is bool

    ss = data.create_fake_storage_service(False)
    assert not ss.default


def test_create_fake_fetch_job(mock_db_add):
    ss = data.create_fake_storage_service(True)
    ss.id = 1

    fetch_job = data.create_fake_fetch_job(ss.id)

    assert fetch_job.download_start
    assert type(fetch_job.download_start) is datetime.datetime

    assert fetch_job.download_end
    assert type(fetch_job.download_end) is datetime.datetime

    assert fetch_job.download_directory
    assert type(fetch_job.download_directory) is str

    assert fetch_job.storage_service_id == ss.id


def test_create_fake_location(mock_db_add):
    location = data.create_fake_location(1)

    assert location.current_location
    assert type(location.current_location) is str

    assert location.description
    assert type(location.description) is str

    assert location.storage_service_id == 1


def test_create_fake_aip(mock_db_add):
    aip = data.create_fake_aip(1, 2, 3, 4, 100, 100)

    assert aip.uuid
    assert type(aip.uuid) is str

    assert aip.transfer_name
    assert type(aip.transfer_name) is str

    assert aip.create_date
    assert type(aip.create_date) is datetime.datetime

    assert aip.mets_sha256
    assert type(aip.mets_sha256) is str

    assert aip.size
    assert type(aip.size) is int

    assert aip.origin_pipeline_id == 1
    assert aip.storage_service_id == 2
    assert aip.storage_location_id == 3
    assert aip.fetch_job_id == 4
    assert aip.origin_pipeline_id == 1
    assert aip.size == 100
