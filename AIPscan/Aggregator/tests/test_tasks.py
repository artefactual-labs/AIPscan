# -*- coding: utf-8 -*-

import json
import os
import pytest

from AIPscan.Aggregator import tasks

FIXTURES_DIR = "fixtures"


@pytest.mark.parametrize(
    "fixture_path, aip_count, deleted_count, dip_count, replicated_count",
    [(os.path.join("package_json", "packages.json"), 5, 1, 1, 1)],
)
def test_parse_packages_and_load_mets(
    fixture_path, aip_count, deleted_count, dip_count, replicated_count, mocker
):
    """Test the parse packages function and ensure it retrieves the
    correct counts from the storage service package list.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    packages_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    mocked_start_mets = mocker.patch("AIPscan.Aggregator.tasks.start_mets_task")
    deleted, dips, replicated, aips = tasks.parse_packages_and_load_mets(
        packages_file, "", "", "", "", ""
    )
    assert mocked_start_mets.call_count == aip_count
    assert deleted == deleted_count
    assert dips == dip_count
    assert replicated == replicated_count
    assert aips == aip_count


PARSE_RESULTS = [
    {
        "package_uuid": "91940daf-5c33-4670-bfc8-9108f32bca7b",
        "relative_path": "repl-91940daf-5c33-4670-bfc8-9108f32bca7b/data/METS.91940daf-5c33-4670-bfc8-9108f32bca7b.xml",
    },
    {
        "package_uuid": "902192d9-6232-4d5f-b6c4-dfa7b8733960",
        "relative_path": "repl-902192d9-6232-4d5f-b6c4-dfa7b8733960/data/METS.902192d9-6232-4d5f-b6c4-dfa7b8733960.xml",
    },
    {
        "package_uuid": "594a03f3-d8eb-4c83-affd-aefaf75d53cc",
        "relative_path": "delete_me-594a03f3-d8eb-4c83-affd-aefaf75d53cc/data/METS.594a03f3-d8eb-4c83-affd-aefaf75d53cc.xml",
    },
    {
        "package_uuid": "e422c724-834c-4164-a7be-4c881043a531",
        "relative_path": "normalize-e422c724-834c-4164-a7be-4c881043a531/data/METS.e422c724-834c-4164-a7be-4c881043a531.xml",
    },
    {
        "package_uuid": "583c009c-4255-44b9-8868-f57e4bade93c",
        "relative_path": "normal_aip-583c009c-4255-44b9-8868-f57e4bade93c/data/METS.583c009c-4255-44b9-8868-f57e4bade93c.xml",
    },
    {
        "package_uuid": "846fca2b-0919-4673-804c-0f626a30cabd",
        "relative_path": "uncomp-846fca2b-0919-4673-804c-0f626a30cabd/data/METS.846fca2b-0919-4673-804c-0f626a30cabd.xml",
    },
    {
        "package_uuid": "155504f5-98dd-48d1-9e97-83bcf0a5efa2",
        "relative_path": "normcore-59f70134-eeca-4886-888e-b2013a08571e/data/METS.155504f5-98dd-48d1-9e97-83bcf0a5efa2.xml",
    },
    {
        "package_uuid": "59f70134-eeca-4886-888e-b2013a08571e",
        "relative_path": "normcore-59f70134-eeca-4886-888e-b2013a08571e/data/METS.59f70134-eeca-4886-888e-b2013a08571e.xml",
    },
]


@pytest.mark.parametrize(
    "fixture_path, parse_results",
    [(os.path.join("package_json", "packages.json"), PARSE_RESULTS)],
)
def test__retrieve_uuid_and_path_from_package_object(fixture_path, parse_results):
    """Test our ability to retrieve the correct UUID and relative path
    in the AIP to a storage service package object.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    packages_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    with open(packages_file, "r") as package_json:
        package_list = json.load(package_json)
    for idx, package_obj in enumerate(package_list.get("objects", [])):
        package_uuid, relative_path = tasks._retrieve_uuid_and_path_from_package_object(
            package_obj
        )
        assert package_uuid == parse_results[idx].get("package_uuid")
        assert relative_path == parse_results[idx].get("relative_path")
    assert idx == len(parse_results) - 1
