import json
import os
from datetime import datetime

import pytest

from AIPscan import models
from AIPscan.Aggregator import task_helpers
from AIPscan.Aggregator.types import StorageServicePackage

FIXTURES_DIR = "fixtures"

LOCATION_UUID = "1b60c346-85a0-4a3c-a88b-0c1b3255e2ec"


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
    """Ensure datetime values are handled sensibly across regions."""
    result_date = task_helpers._tz_neutral_date(input_date)
    if now_year is True:
        year = datetime.now().strftime("%Y-%m-%d")
        output_date = f"{year}{input_date}"
        output_date = datetime.strptime(output_date, "%Y-%m-%dT%H:%M:%S")
        assert result_date == output_date
    else:
        output_date = datetime.strptime(output_date, "%Y-%m-%dT%H:%M:%S")
        assert result_date == output_date


@pytest.mark.parametrize(
    "ss_args, base_url, url_without_api_key, url_with_api_key",
    [
        (
            {
                "name": "Test",
                "url": "http://example.com:9000/",
                "user_name": "test",
                "api_key": "mykey",
                "download_limit": "23",
                "download_offset": "13",
                "default": False,
            },
            "http://example.com:9000",
            "http://example.com:9000/api/v2/file/?limit=23&offset=13",
            "http://example.com:9000/api/v2/file/?limit=23&offset=13&username=test&api_key=mykey",
        ),
        (
            {
                "name": "Test",
                "url": "http://subdomain.example.com:8000/",
                "user_name": "anothertest",
                "api_key": "myotherkey",
                "download_limit": "10",
                "download_offset": "99",
                "default": False,
            },
            "http://subdomain.example.com:8000",
            "http://subdomain.example.com:8000/api/v2/file/?limit=10&offset=99",
            "http://subdomain.example.com:8000/api/v2/file/?limit=10&offset=99&username=anothertest&api_key=myotherkey",
        ),
    ],
)
def test_format_api_url(ss_args, base_url, url_without_api_key, url_with_api_key):
    storage_service = models.StorageService(**ss_args)
    res1, res2, res3 = task_helpers.format_api_url_with_limit_offset(storage_service)
    assert res1 == base_url
    assert res2 == url_without_api_key
    assert res3 == url_with_api_key


@pytest.mark.parametrize(
    "ss_args, package_uuid, path_to_mets, result",
    [
        (
            {
                "name": "Test",
                "url": "http://example.com",
                "user_name": "1234",
                "api_key": "1234",
                "download_limit": 0,
                "download_offset": 0,
                "default": False,
            },
            "1234",
            "1234",
            "http://example.com/api/v2/file/1234/extract_file/?relative_path_to_file=1234&username=1234&api_key=1234",
        ),
        (
            {
                "name": "Test",
                "url": "http://example.com",
                "user_name": "1234",
                "api_key": "1234",
                "download_limit": 0,
                "download_offset": 0,
                "default": False,
            },
            "1234",
            "1234",
            "http://example.com/api/v2/file/1234/extract_file/?relative_path_to_file=1234&username=1234&api_key=1234",
        ),
    ],
)
def test_get_mets_url(ss_args, package_uuid, path_to_mets, result):
    """Ensure that the URL for retrieving METS is constructed properly."""
    ss = models.StorageService(**ss_args)
    mets_url = task_helpers.get_mets_url(ss, package_uuid, path_to_mets)
    assert mets_url == result


@pytest.mark.parametrize(
    "ss_args, current_location, expected_url, expected_url_without_api_key",
    [
        (
            {
                "name": "Test",
                "url": "http://example.com",
                "user_name": "1234",
                "api_key": "12345",
                "download_limit": 0,
                "download_offset": 0,
                "default": False,
            },
            f"/api/v2/location/{LOCATION_UUID}",
            "http://example.com/api/v2/location/1b60c346-85a0-4a3c-a88b-0c1b3255e2ec?username=1234&api_key=12345",
            "http://example.com/api/v2/location/1b60c346-85a0-4a3c-a88b-0c1b3255e2ec",
        )
    ],
)
def test_get_storage_service_api_url(
    ss_args, current_location, expected_url, expected_url_without_api_key
):
    """Ensure construction of URL to fetch Resource information."""
    storage_service = models.StorageService(**ss_args)

    url, url_without_secrets = task_helpers.get_storage_service_api_url(
        storage_service, current_location
    )
    assert url == expected_url
    assert url_without_secrets == expected_url_without_api_key


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
    with open(packages_file) as package_json:
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
                current_location="/api/v2/location/a083fd8c-8b5a-4ece-acc4-c6388ade3d56/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            1,
            StorageServicePackage(
                replica=True,
                aip=True,
                current_path="9021/92d9/6232/4d5f/b6c4/dfa7/b873/3960/repl-902192d9-6232-4d5f-b6c4-dfa7b8733960.7z",
                uuid="902192d9-6232-4d5f-b6c4-dfa7b8733960",
                current_location="/api/v2/location/a82c7f40-34f5-4442-a408-cbcf16f0c1cf/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            2,
            StorageServicePackage(
                deleted=True,
                aip=True,
                current_path="594a/03f3/d8eb/4c83/affd/aefa/f75d/53cc/delete_me-594a03f3-d8eb-4c83-affd-aefaf75d53cc.7z",
                uuid="594a03f3-d8eb-4c83-affd-aefaf75d53cc",
                current_location="/api/v2/location/a083fd8c-8b5a-4ece-acc4-c6388ade3d56/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            3,
            StorageServicePackage(
                aip=True,
                current_path="e422/c724/834c/4164/a7be/4c88/1043/a531/normalize-e422c724-834c-4164-a7be-4c881043a531.7z",
                uuid="e422c724-834c-4164-a7be-4c881043a531",
                current_location="/api/v2/location/a083fd8c-8b5a-4ece-acc4-c6388ade3d56/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            4,
            StorageServicePackage(
                aip=True,
                current_path="583c/009c/4255/44b9/8868/f57e/4bad/e93c/normal_aip-583c009c-4255-44b9-8868-f57e4bade93c.7z",
                uuid="583c009c-4255-44b9-8868-f57e4bade93c",
                current_location="/api/v2/location/a083fd8c-8b5a-4ece-acc4-c6388ade3d56/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            5,
            StorageServicePackage(
                aip=True,
                current_path="846f/ca2b/0919/4673/804c/0f62/6a30/cabd/uncomp-846fca2b-0919-4673-804c-0f626a30cabd",
                uuid="846fca2b-0919-4673-804c-0f626a30cabd",
                current_location="/api/v2/location/a083fd8c-8b5a-4ece-acc4-c6388ade3d56/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            6,
            StorageServicePackage(
                dip=True,
                current_path="1555/04f5/98dd/48d1/9e97/83bc/f0a5/efa2/normcore-59f70134-eeca-4886-888e-b2013a08571e",
                uuid="155504f5-98dd-48d1-9e97-83bcf0a5efa2",
                current_location="/api/v2/location/7e99c7b0-bd30-4d49-b173-3cb59a32f0c5/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            7,
            StorageServicePackage(
                aip=True,
                current_path="59f7/0134/eeca/4886/888e/b201/3a08/571e/normcore-59f70134-eeca-4886-888e-b2013a08571e",
                uuid="59f70134-eeca-4886-888e-b2013a08571e",
                current_location="/api/v2/location/a083fd8c-8b5a-4ece-acc4-c6388ade3d56/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
            ),
        ),
        (
            8,
            StorageServicePackage(
                sip=True,
                current_path="originals/backlog-fbdcd607-270e-4dff-9a01-d11b7c2a0200",
                uuid="fbdcd607-270e-4dff-9a01-d11b7c2a0200",
                current_location="/api/v2/location/7fe31789-90e0-4ad3-a669-18517737fc25/",
                origin_pipeline="/api/v2/pipeline/dbb92514-1572-4a81-87ee-06408672e7a6/",
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


def test_summarize_fetch_job_results():
    fetch_job = models.FetchJob(
        total_packages=15,
        total_aips=1,
        total_deleted_aips=4,
        download_start=None,
        download_end=None,
        download_directory=None,
        storage_service_id=None,
    )
    fetch_job.total_sips = 2
    fetch_job.total_dips = 3
    fetch_job.total_replicas = 5

    assert (
        "aips: '1'; sips: '2'; dips: '3'; deleted: '4'; replicated: '5'"
        == task_helpers.summarize_fetch_job_results(fetch_job)
    )
