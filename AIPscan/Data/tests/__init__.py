import datetime
import uuid

from AIPscan.models import AIP
from AIPscan.models import StorageService


class MockAIPsByFormatOrPUIDResult:
    """Fixture for mocking AIPs by format/PUID results with labels."""

    def __init__(self, mock_id, name, uuid, file_count, total_size):
        self.id = mock_id
        self.name = name
        self.uuid = uuid
        self.file_count = file_count
        self.total_size = total_size


MOCK_AIPS_BY_FORMAT_OR_PUID_QUERY_RESULTS = [
    MockAIPsByFormatOrPUIDResult(
        mock_id=1,
        name="aip0",
        uuid="11111111-1111-1111-1111-111111111111",
        file_count=5,
        total_size=12345678,
    ),
    MockAIPsByFormatOrPUIDResult(
        mock_id=2,
        name="aip1",
        uuid="22222222-2222-2222-2222-222222222222",
        file_count=3,
        total_size=123456,
    ),
    MockAIPsByFormatOrPUIDResult(
        mock_id=5,
        name="aip2",
        uuid="33333333-3333-3333-3333-333333333333",
        file_count=2,
        total_size=12345,
    ),
    MockAIPsByFormatOrPUIDResult(
        mock_id=10,
        name="aip3",
        uuid="44444444-4444-4444-4444-444444444444",
        file_count=1,
        total_size=123,
    ),
]

MOCK_STORAGE_SERVICE_ID = 1
MOCK_STORAGE_SERVICE_NAME = "some name"
MOCK_STORAGE_SERVICE = StorageService(
    name=MOCK_STORAGE_SERVICE_NAME,
    url="http://example.com",
    user_name="test",
    api_key="test",
    download_limit=20,
    download_offset=10,
    default=False,
)
MOCK_STORAGE_SERVICE.id = MOCK_STORAGE_SERVICE_ID

MOCK_STORAGE_SERVICE_ID_2 = 2
MOCK_STORAGE_SERVICE_2 = StorageService(
    name="another name",
    url="http://anotherexample.com",
    user_name="test2",
    api_key="test_api_2",
    download_limit=30,
    download_offset=40,
    default=False,
)
MOCK_STORAGE_SERVICE_2.id = MOCK_STORAGE_SERVICE_ID_2

MOCK_STORAGE_SERVICES = [MOCK_STORAGE_SERVICE, MOCK_STORAGE_SERVICE_2]

MOCK_STORAGE_LOCATION_ID = 1

MOCK_AIP_NAME = "Test transfer"
MOCK_AIP_UUID = str(uuid.uuid4())
MOCK_AIP = AIP(
    uuid=MOCK_AIP_UUID,
    transfer_name=MOCK_AIP_NAME,
    create_date=datetime.datetime.now(),
    mets_sha256="test",
    size=0,
    storage_service_id=MOCK_STORAGE_SERVICE_ID,
    storage_location_id=MOCK_STORAGE_LOCATION_ID,
    fetch_job_id=1,
    origin_pipeline_id=1,
)
