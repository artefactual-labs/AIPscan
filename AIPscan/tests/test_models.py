"""This module tests models."""

from datetime import date

import pytest

from AIPscan import db
from AIPscan import test_helpers
from AIPscan.conftest import AIP_CREATION_TIME
from AIPscan.conftest import JPEG_1_01_PUID
from AIPscan.conftest import JPEG_1_02_PUID
from AIPscan.conftest import PRESERVATION_FORMAT
from AIPscan.conftest import PRESERVATION_PUID
from AIPscan.conftest import STORAGE_LOCATION_1_CURRENT_LOCATION
from AIPscan.conftest import STORAGE_LOCATION_2_CURRENT_LOCATION
from AIPscan.conftest import TIFF_PUID
from AIPscan.helpers import parse_datetime_bound
from AIPscan.models import StorageLocation
from AIPscan.models import StorageService

VALID_UUID = "3ce6fbcb-cdfc-4cca-97e4-d19a469ca043"
VALID_CURRENT_LOCATION = f"/api/v2/location/{VALID_UUID}/"
VALID_ORIGIN_PIPELINE = f"/api/v2/pipeline/{VALID_UUID}/"

INVALID_UUID = "not-a-uuid"
INVALID_CURRENT_LOCATION = f"/api/v2/location/{INVALID_UUID}/"
INVALID_ORIGIN_PIPELINE = f"/api/v2/pipeline/{INVALID_UUID}/"


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
        storage_service = db.session.get(StorageService, storage_service_id)
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
        storage_service = db.session.get(StorageService, storage_service_id)
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
    "current_location, start_date, end_date, expected_aip_count",
    [
        # Test Storage Location populated with AIPs.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, None, 2),
        # Test date parameters in populated Storage Location.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", None, 1),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, "2020-05-31", 1),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", "2020-05-31", 0),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-01", "2020-06-01", 2),
        # Test new Storage Location (no AIPs).
        (None, None, None, 0),
    ],
)
def test_storage_location_aip_count(
    storage_locations, current_location, start_date, end_date, expected_aip_count
):
    """Test Storage Location aip_count property."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()
    start_date = parse_datetime_bound(start_date)
    end_date = parse_datetime_bound(end_date, upper=True)
    assert storage_location.aip_count(start_date, end_date) == expected_aip_count


@pytest.mark.parametrize(
    "current_location, start_date, end_date, expected_total_size",
    [
        # Test Storage Location populated with AIPs and files.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, None, 1600),
        # Test data parameters in populated Storage Location.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", None, 1000),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, "2020-05-31", 600),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", "2020-05-31", 0),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-01", "2020-06-01", 1600),
        # Test new Storage Location (no AIPs or files).
        (None, None, None, 0),
    ],
)
def test_storage_location_aip_total_size(
    storage_locations, current_location, start_date, end_date, expected_total_size
):
    """Test Storage Location aip_total_size property."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()
    start_date = parse_datetime_bound(start_date)
    end_date = parse_datetime_bound(end_date, upper=True)
    assert storage_location.aip_total_size(start_date, end_date) == expected_total_size


@pytest.mark.parametrize(
    "current_location, start_date, end_date, originals_only, expected_file_count",
    [
        # Test Storage Location populated with AIPs.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, None, True, 3),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, None, False, 4),
        # Test date parameters in populated Storage Location.
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", None, True, 1),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", None, False, 1),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, "2020-05-31", True, 2),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, None, "2020-05-31", False, 3),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", "2020-05-31", True, 0),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-02", "2020-05-31", False, 0),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-01", "2020-06-01", True, 3),
        (STORAGE_LOCATION_1_CURRENT_LOCATION, "2020-01-01", "2020-06-01", False, 4),
        # Test new Storage Location (no AIPs).
        (None, None, None, True, 0),
        (None, None, None, False, 0),
    ],
)
def test_storage_location_file_count(
    storage_locations,
    current_location,
    start_date,
    end_date,
    originals_only,
    expected_file_count,
):
    """Test Storage Location file_count property."""
    if current_location:
        storage_location = StorageLocation.query.filter_by(
            current_location=current_location
        ).first()
    else:
        storage_location = test_helpers.create_test_storage_location()
    start_date = parse_datetime_bound(start_date)
    end_date = parse_datetime_bound(end_date, upper=True)
    assert (
        storage_location.file_count(start_date, end_date, originals=originals_only)
        == expected_file_count
    )


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


@pytest.mark.parametrize(
    "origin_pipeline, expected_uuid",
    [
        # Test that UUID is returned for valid current location.
        (VALID_ORIGIN_PIPELINE, VALID_UUID),
        # Test that None is returned for invalid current location.
        (INVALID_ORIGIN_PIPELINE, None),
    ],
)
def test_pipeline_uuid(app_instance, origin_pipeline, expected_uuid):
    """Test Storage Location uuid property."""
    pipeline = test_helpers.create_test_pipeline(origin_pipeline=origin_pipeline)
    assert pipeline.uuid == expected_uuid
