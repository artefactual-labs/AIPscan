from AIPscan.conftest import AIP_1_NAME
from AIPscan.conftest import AIP_1_UUID
from AIPscan.conftest import AIP_2_NAME
from AIPscan.conftest import AIP_2_UUID
from AIPscan.conftest import JPEG_1_01_FORMAT_VERSION
from AIPscan.conftest import JPEG_1_01_PUID
from AIPscan.conftest import JPEG_1_02_FORMAT_VERSION
from AIPscan.conftest import JPEG_1_02_PUID
from AIPscan.conftest import JPEG_FILE_FORMAT
from AIPscan.conftest import ORIGINAL_FILE_1_NAME
from AIPscan.conftest import ORIGINAL_FILE_1_UUID
from AIPscan.conftest import ORIGINAL_FILE_2_NAME
from AIPscan.conftest import ORIGINAL_FILE_2_UUID
from AIPscan.conftest import PRESERVATION_FILE_1_NAME
from AIPscan.conftest import PRESERVATION_FILE_1_UUID
from AIPscan.conftest import PRESERVATION_FILE_2_NAME
from AIPscan.conftest import PRESERVATION_FILE_2_UUID
from AIPscan.conftest import STORAGE_SERVICE_NAME
from AIPscan.conftest import TIFF_FILE_FORMAT
from AIPscan.Data import fields
from AIPscan.Data import report_data

# Two preservation files are created in fixture.
EXPECTED_RESULTS_COUNT = 2

STORAGE_LOCATION_DESCRIPTION = "test storage location"


def test_preservation_derivatives(preservation_derivatives):
    """Test preservation derivatives report_data endpoint."""
    report = report_data.preservation_derivatives(
        storage_service_id=1, storage_location_id=1
    )
    file_data = report[fields.FIELD_FILES]

    assert report[fields.FIELD_STORAGE_NAME] == STORAGE_SERVICE_NAME
    assert report[fields.FIELD_STORAGE_LOCATION] == STORAGE_LOCATION_DESCRIPTION
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
