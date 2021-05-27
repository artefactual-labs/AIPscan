# -*- coding: utf-8 -*-
"""This module tests models."""
from datetime import date

import pytest

from AIPscan import test_helpers
from AIPscan.conftest import (
    AIP_CREATION_TIME,
    JPEG_1_01_PUID,
    JPEG_1_02_PUID,
    PRESERVATION_FORMAT,
    PRESERVATION_PUID,
    STORAGE_LOCATION_1_CURRENT_LOCATION,
    STORAGE_LOCATION_2_CURRENT_LOCATION,
    TIFF_PUID,
)
from AIPscan.models import StorageLocation, StorageService

VALID_UUID = "3ce6fbcb-cdfc-4cca-97e4-d19a469ca043"
VALID_CURRENT_LOCATION = "/api/v2/location/{}/".format(VALID_UUID)

INVALID_UUID = "not-a-uuid"
INVALID_CURRENT_LOCATION = "/api/v2/location/{}/".format(INVALID_UUID)


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
    """Test Storage Service earliest_aip_created property with AIPs."""
    storage_service = test_helpers.create_test_storage_service(name="storage2")
    assert storage_service.earliest_aip_created == AIP_CREATION_TIME


def test_storage_service_earliest_aip_created_with_no_aips(app_instance):
    """Test Storage Service earliest_aip_created property without AIPs"""
    storage_service = test_helpers.create_test_storage_service(name="storage3")
    assert storage_service.earliest_aip_created == date.today()


@pytest.mark.parametrize(
    "storage_service_id, original_formats, preservation_formats",
    [
        # Test with populated Storage Service.
        (
            1,
            ["ACME File Format", "JPEG", "txt", "yet another format"],
            ["Tagged Image File Format", PRESERVATION_FORMAT],
        ),
        # Test with new Storage Service (no files).
        (None, [], []),
    ],
)
def test_storage_service_unique_file_formats(
    storage_locations, storage_service_id, original_formats, preservation_formats
):
    """Test Storage Service unique file format properties."""
    if storage_service_id:
        storage_service = StorageService.query.get(storage_service_id)
    else:
        storage_service = test_helpers.create_test_storage_service(
            name="empty storage service"
        )

    assert storage_service.unique_original_file_formats == original_formats
    assert storage_service.unique_preservation_file_formats == preservation_formats


@pytest.mark.parametrize(
    "storage_service_id, original_puids, preservation_puids",
    [
        # Test with populated Storage Service.
        (
            1,
            [JPEG_1_01_PUID, JPEG_1_02_PUID, "fmt/test-1"],
            [PRESERVATION_PUID, TIFF_PUID],
        ),
        # Test with new Storage Service (no files).
        (None, [], []),
    ],
)
def test_storage_service_unique_puids(
    storage_locations, storage_service_id, original_puids, preservation_puids
):
    """Test Storage Service unique PUID properties."""
    if storage_service_id:
        storage_service = StorageService.query.get(storage_service_id)
    else:
        storage_service = test_helpers.create_test_storage_service(
            name="empty storage service"
        )

    assert storage_service.unique_original_puids == original_puids
    assert storage_service.unique_preservation_puids == preservation_puids


@pytest.mark.parametrize(
    "current_location, expected_uuid",
    [
        # Test that UUID is returned for valid current location.
        (VALID_CURRENT_LOCATION, VALID_UUID),
        # Test that None is returned for invalid current location.
        (INVALID_CURRENT_LOCATION, None),
    ],
)
def test_storage_location_uuid(app_instance, current_location, expected_uuid):
    """Test Storage Location uuid property."""
    storage_location = test_helpers.create_test_storage_location(
        current_location=current_location
    )
    assert storage_location.uuid == expected_uuid


@pytest.mark.parametrize(
    "current_location, expected_aip_count",
    [
        # Test Storage Location populated with AIPs.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, 2),
        # Test new Storage Location (no AIPs).
        (None, 0),
    ],
)
def test_storage_location_aip_count(
    storage_locations, current_location, expected_aip_count
):
    """Test Storage Location aip_count property."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()
    assert storage_location.aip_count == expected_aip_count


@pytest.mark.parametrize(
    "current_location, expected_total_size",
    [
        # Test Storage Location populated with AIPs and files.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, 1600),
        # Test new Storage Location (no AIPs or files).
        (None, 0),
    ],
)
def test_storage_location_aip_total_size(
    storage_locations, current_location, expected_total_size
):
    """Test Storage Location aip_total_size property."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()
    assert storage_location.aip_total_size == expected_total_size


@pytest.mark.parametrize(
    "current_location, original_formats, preservation_formats",
    [
        # Test with first Storage Location.
        (
            STORAGE_LOCATION_1_CURRENT_LOCATION,
            ["JPEG", "txt"],
            ["Tagged Image File Format"],
        ),
        # Test with second Storage Location.
        (
            STORAGE_LOCATION_2_CURRENT_LOCATION,
            ["ACME File Format", "yet another format"],
            [PRESERVATION_FORMAT],
        ),
        # Test with new Storage Location (no files).
        (None, [], []),
    ],
)
def test_storage_location_unique_file_formats(
    storage_locations, current_location, original_formats, preservation_formats
):
    """Test Storage Location unique file format properties."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()

    assert storage_location.unique_original_file_formats == original_formats
    assert storage_location.unique_preservation_file_formats == preservation_formats


@pytest.mark.parametrize(
    "current_location, original_puids, preservation_puids",
    [
        # Test with first Storage Location.
        (
            STORAGE_LOCATION_1_CURRENT_LOCATION,
            [JPEG_1_01_PUID, JPEG_1_02_PUID, "fmt/test-1"],
            [TIFF_PUID],
        ),
        # Test with second Storage Location.
        (STORAGE_LOCATION_2_CURRENT_LOCATION, ["fmt/test-1"], [PRESERVATION_PUID]),
        # Test with new Storage Location (no files).
        (None, [], []),
    ],
)
def test_storage_location_unique_puids(
    storage_locations, current_location, original_puids, preservation_puids
):
    """Test Storage Location unique PUID properties."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()

    assert storage_location.unique_original_puids == original_puids
    assert storage_location.unique_preservation_puids == preservation_puids
