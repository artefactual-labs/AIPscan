# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime

import pytest

from AIPscan.Aggregator import task_helpers
from AIPscan.Aggregator.types import StorageServicePackage

FIXTURES_DIR = "fixtures"


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
    """Ensure datetime values are handled sensibly across regions.
    """
    result_date = task_helpers._tz_neutral_date(input_date)
    if now_year is True:
        year = datetime.now().strftime("%Y-%m-%d")
        output_date = "{}{}".format(year, input_date)
        output_date = datetime.strptime(output_date, "%Y-%m-%dT%H:%M:%S")
        assert result_date == output_date
    else:
        output_date = datetime.strptime(output_date, "%Y-%m-%dT%H:%M:%S")
        assert result_date == output_date


@pytest.mark.parametrize(
    "url_api_dict, base_url, url_without_api_key, url_with_api_key",
    [
        (
            {
                "baseUrl": "http://example.com:9000/",
                "limit": "23",
                "offset": "13",
                "userName": "test",
                "apiKey": "mykey",
            },
            "http://example.com:9000",
            "http://example.com:9000/api/v2/file/?limit=23&offset=13",
            "http://example.com:9000/api/v2/file/?limit=23&offset=13&username=test&api_key=mykey",
        ),
        (
            {
                "baseUrl": "http://subdomain.example.com:8000/",
                "limit": "10",
                "offset": "99",
                "userName": "anothertest",
                "apiKey": "myotherkey",
            },
            "http://subdomain.example.com:8000",
            "http://subdomain.example.com:8000/api/v2/file/?limit=10&offset=99",
            "http://subdomain.example.com:8000/api/v2/file/?limit=10&offset=99&username=anothertest&api_key=myotherkey",
        ),
    ],
)
def test_format_api_url(url_api_dict, base_url, url_without_api_key, url_with_api_key):
    res1, res2, res3 = task_helpers.format_api_url_with_limit_offset(url_api_dict)
    assert res1 == base_url
    assert res2 == url_without_api_key
    assert res3 == url_with_api_key


@pytest.mark.parametrize(
    "api_url, package_uuid, path_to_mets, result",
    [
        (
            {"baseUrl": "http://example.com", "userName": "1234", "apiKey": "1234"},
            "1234",
            "1234",
            "http://example.com/api/v2/file/1234/extract_file/?relative_path_to_file=1234&username=1234&api_key=1234",
        ),
        (
            {"baseUrl": "http://example.com/", "userName": "1234", "apiKey": "1234"},
            "1234",
            "1234",
            "http://example.com/api/v2/file/1234/extract_file/?relative_path_to_file=1234&username=1234&api_key=1234",
        ),
    ],
)
def test_get_mets_url(api_url, package_uuid, path_to_mets, result):
    """Ensure that the URL for retrieving METS is constructed properly.
    """
    mets_url = task_helpers.get_mets_url(api_url, package_uuid, path_to_mets)
    assert mets_url == result


@pytest.mark.parametrize(
    "timestamp, package_list_number, result",
    [("1234", 1, "AIPscan/Aggregator/downloads/1234/mets/1")],
)
def test_create_numbered_subdirs(timestamp, package_list_number, result, mocker):
    """Ensure that the logic that we use to create sub-directories for
    storing METS is sound.
    """

    # Test that an unknown directory is created first time around and
    # that the correct result is returned.
    mocked_makedirs = mocker.patch("os.makedirs")
    subdir_string = task_helpers.create_numbered_subdirs(timestamp, package_list_number)
    assert mocked_makedirs.call_count == 1
    assert subdir_string == result

    # Test that if the path exists, we don't create the directory, and
    # that the correct result is returned.
    mocker.patch("os.path.exists", result=True)
    mocked_makedirs = mocker.patch("os.makedirs")
    subdir_string = task_helpers.create_numbered_subdirs(timestamp, package_list_number)
    assert mocked_makedirs.call_count == 0
    assert subdir_string == result


@pytest.fixture()
def packages():
    fixtures_path = os.path.join("package_json", "packages.json")
    script_dir = os.path.dirname(os.path.realpath(__file__))
    packages_file = os.path.join(script_dir, FIXTURES_DIR, fixtures_path)
    with open(packages_file, "r") as package_json:
        packages = json.load(package_json)
        return packages.get("objects")


@pytest.mark.parametrize(
    "idx, storage_service_package",
    [
        (
            0,
            StorageServicePackage(
                aip=True,
                current_path="9194/0daf/5c33/4670/bfc8/9108/f32b/ca7b/repl-91940daf-5c33-4670-bfc8-9108f32bca7b.7z",
                uuid="91940daf-5c33-4670-bfc8-9108f32bca7b",
            ),
        ),
        (
            1,
            StorageServicePackage(
                replica=True,
                aip=True,
                current_path="9021/92d9/6232/4d5f/b6c4/dfa7/b873/3960/repl-902192d9-6232-4d5f-b6c4-dfa7b8733960.7z",
                uuid="902192d9-6232-4d5f-b6c4-dfa7b8733960",
            ),
        ),
        (
            2,
            StorageServicePackage(
                deleted=True,
                aip=True,
                current_path="594a/03f3/d8eb/4c83/affd/aefa/f75d/53cc/delete_me-594a03f3-d8eb-4c83-affd-aefaf75d53cc.7z",
                uuid="594a03f3-d8eb-4c83-affd-aefaf75d53cc",
            ),
        ),
        (
            3,
            StorageServicePackage(
                aip=True,
                current_path="e422/c724/834c/4164/a7be/4c88/1043/a531/normalize-e422c724-834c-4164-a7be-4c881043a531.7z",
                uuid="e422c724-834c-4164-a7be-4c881043a531",
            ),
        ),
        (
            4,
            StorageServicePackage(
                aip=True,
                current_path="583c/009c/4255/44b9/8868/f57e/4bad/e93c/normal_aip-583c009c-4255-44b9-8868-f57e4bade93c.7z",
                uuid="583c009c-4255-44b9-8868-f57e4bade93c",
            ),
        ),
        (
            5,
            StorageServicePackage(
                aip=True,
                current_path="846f/ca2b/0919/4673/804c/0f62/6a30/cabd/uncomp-846fca2b-0919-4673-804c-0f626a30cabd",
                uuid="846fca2b-0919-4673-804c-0f626a30cabd",
            ),
        ),
        (
            6,
            StorageServicePackage(
                dip=True,
                current_path="1555/04f5/98dd/48d1/9e97/83bc/f0a5/efa2/normcore-59f70134-eeca-4886-888e-b2013a08571e",
                uuid="155504f5-98dd-48d1-9e97-83bcf0a5efa2",
            ),
        ),
        (
            7,
            StorageServicePackage(
                aip=True,
                current_path="59f7/0134/eeca/4886/888e/b201/3a08/571e/normcore-59f70134-eeca-4886-888e-b2013a08571e",
                uuid="59f70134-eeca-4886-888e-b2013a08571e",
            ),
        ),
        (
            8,
            StorageServicePackage(
                sip=True,
                current_path="originals/backlog-fbdcd607-270e-4dff-9a01-d11b7c2a0200",
                uuid="fbdcd607-270e-4dff-9a01-d11b7c2a0200",
            ),
        ),
    ],
)
def test_process_package_object(packages, idx, storage_service_package):
    """Test our ability to collect information from a package list
    object and parse it into a storage service package type for
    further use.
    """
    package_obj = task_helpers.process_package_object(packages[idx])
    assert package_obj == storage_service_package, idx
