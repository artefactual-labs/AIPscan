from AIPscan.Data import fields, report_data
from AIPscan.Data.tests.conftest import (
    AIP_1_NAME,
    AIP_1_UUID,
    AIP_2_NAME,
    AIP_2_UUID,
    JPEG_1_01_FORMAT_VERSION,
    JPEG_1_01_PUID,
    JPEG_1_02_FORMAT_VERSION,
    JPEG_1_02_PUID,
    JPEG_FILE_FORMAT,
    ORIGINAL_FILE_1_NAME,
    ORIGINAL_FILE_1_UUID,
    ORIGINAL_FILE_2_NAME,
    ORIGINAL_FILE_2_UUID,
    PRESERVATION_FILE_1_NAME,
    PRESERVATION_FILE_1_UUID,
    PRESERVATION_FILE_2_NAME,
    PRESERVATION_FILE_2_UUID,
    STORAGE_SERVICE_NAME,
    TIFF_FILE_FORMAT,
)

# Two preservation files are created in fixture.
EXPECTED_RESULTS_COUNT = 2


def test_preservation_derivatives(app_with_populated_preservation_derivatives):
    """Test preservation derivatives report_data endpoint."""
    report = report_data.preservation_derivatives(storage_service_id=1)
    file_data = report[fields.FIELD_FILES]

    assert report[fields.FIELD_STORAGE_NAME] == STORAGE_SERVICE_NAME
    assert len(file_data) == EXPECTED_RESULTS_COUNT

    preservation_file_1 = [
        file_
        for file_ in file_data
        if file_[fields.FIELD_UUID] == PRESERVATION_FILE_1_UUID
    ][0]
    preservation_file_2 = [
        file_
        for file_ in file_data
        if file_[fields.FIELD_UUID] == PRESERVATION_FILE_2_UUID
    ][0]

    # Test first preservation file data.
    assert preservation_file_1.get(fields.FIELD_AIP_UUID) == AIP_1_UUID
    assert preservation_file_1.get(fields.FIELD_AIP_NAME) == AIP_1_NAME

    assert preservation_file_1.get(fields.FIELD_UUID) == PRESERVATION_FILE_1_UUID
    assert preservation_file_1.get(fields.FIELD_NAME) == PRESERVATION_FILE_1_NAME
    assert preservation_file_1.get(fields.FIELD_FORMAT) == TIFF_FILE_FORMAT

    assert preservation_file_1.get(fields.FIELD_ORIGINAL_UUID) == ORIGINAL_FILE_1_UUID
    assert preservation_file_1.get(fields.FIELD_ORIGINAL_NAME) == ORIGINAL_FILE_1_NAME
    assert preservation_file_1.get(fields.FIELD_ORIGINAL_FORMAT) == JPEG_FILE_FORMAT
    assert (
        preservation_file_1.get(fields.FIELD_ORIGINAL_VERSION)
        == JPEG_1_01_FORMAT_VERSION
    )
    assert preservation_file_1.get(fields.FIELD_ORIGINAL_PUID) == JPEG_1_01_PUID

    # Test second preservation file data.
    assert preservation_file_2.get(fields.FIELD_AIP_UUID) == AIP_2_UUID
    assert preservation_file_2.get(fields.FIELD_AIP_NAME) == AIP_2_NAME

    assert preservation_file_2.get(fields.FIELD_UUID) == PRESERVATION_FILE_2_UUID
    assert preservation_file_2.get(fields.FIELD_NAME) == PRESERVATION_FILE_2_NAME
    assert preservation_file_2.get(fields.FIELD_FORMAT) == TIFF_FILE_FORMAT

    assert preservation_file_2.get(fields.FIELD_ORIGINAL_UUID) == ORIGINAL_FILE_2_UUID
    assert preservation_file_2.get(fields.FIELD_ORIGINAL_NAME) == ORIGINAL_FILE_2_NAME
    assert preservation_file_2.get(fields.FIELD_ORIGINAL_FORMAT) == JPEG_FILE_FORMAT
    assert (
        preservation_file_2.get(fields.FIELD_ORIGINAL_VERSION)
        == JPEG_1_02_FORMAT_VERSION
    )
    assert preservation_file_2.get(fields.FIELD_ORIGINAL_PUID) == JPEG_1_02_PUID
