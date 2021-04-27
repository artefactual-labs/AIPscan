# -*- coding: utf-8 -*-

"""This module tests models."""

from AIPscan import test_helpers
from AIPscan.conftest import AIP_CREATION_TIME


def test_new_storage_service(app_with_populated_files):
    """Test that a new storage service is created."""
    storage_service = test_helpers.create_test_storage_service(name="storage")
    assert storage_service.name == "storage"
    assert storage_service.url == "storage"
    assert storage_service.user_name == "test"
    assert storage_service.api_key == "test"
    assert storage_service.download_limit == 0
    assert storage_service.download_offset == 10
    assert storage_service.default is True

def test_storage_service_earliest_aip_created(app_with_populated_files):
    """Test that """
    storage_service = test_helpers.create_test_storage_service(name="storage2")
    assert storage_service.earliest_aip_created == AIP_CREATION_TIME