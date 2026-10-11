"""Import failures remain visible and retain documents for diagnosis."""

from hashlib import sha256
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from xml.etree import ElementTree as ET

import pytest

from AIPscan import test_helpers
from AIPscan.Aggregator.tasks import TaskError
from AIPscan.Aggregator.tasks import get_mets
from AIPscan.models import AIP
from AIPscan.models import File

METS = Path(__file__).parent / "fixtures/legacy_mets/production-aip-mets-file.xml"
PACKAGE_UUID = "80f077d8-2a6f-49e2-9327-903c36d6d92d"


@pytest.fixture
def mets_import(app_instance, tmp_path, monkeypatch):
    response = {"body": METS.read_bytes(), "status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(response["status"])
            self.end_headers()
            self.wfile.write(response["body"])

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    storage = test_helpers.create_test_storage_service(
        url=f"http://127.0.0.1:{server.server_port}"
    )
    location = test_helpers.create_test_storage_location(storage_service_id=storage.id)
    pipeline = test_helpers.create_test_pipeline()
    job = test_helpers.create_test_fetch_job(storage_service_id=storage.id)
    monkeypatch.setitem(app_instance.config, "AGGREGATOR_DOWNLOAD_ROOT", str(tmp_path))

    arguments = [
        PACKAGE_UUID,
        1000,
        "data/METS.xml",
        "diagnostic",
        1,
        storage.id,
        location.id,
        pipeline.id,
        job.id,
    ]

    def run():
        return get_mets.apply(args=arguments, throw=False)

    try:
        yield response, run
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_failed_parse_preserves_existing_metadata(mets_import, tmp_path):
    response, run = mets_import
    assert run().state == "SUCCESS"
    previous = AIP.query.filter_by(uuid=PACKAGE_UUID).one()
    previous_id, previous_hash = previous.id, previous.mets_sha256
    previous_files = [(file.uuid, file.name) for file in previous.files]
    response["body"] = b"<invalid>"

    result = run()

    assert result.state == "FAILURE"
    assert isinstance(result.result, TaskError)
    assert f"Cannot parse METS for AIP {PACKAGE_UUID}" in str(result.result)
    previous = AIP.query.filter_by(uuid=PACKAGE_UUID).one()
    assert (previous.id, previous.mets_sha256) == (previous_id, previous_hash)
    assert [(file.uuid, file.name) for file in previous.files] == previous_files
    document = tmp_path / f"diagnostic/mets/1/METS.{PACKAGE_UUID}.xml"
    assert document.read_bytes() == response["body"]


@pytest.mark.parametrize("replacing", [False, True])
def test_failed_persistence_reports_failure_and_allows_retry(
    mets_import, tmp_path, replacing
):
    response, run = mets_import
    original = response["body"]
    if replacing:
        assert run().state == "SUCCESS"
    invalid = ET.fromstring(original)
    invalid.find(
        ".//{info:lc/xmlns/premis-v2}linkingAgentIdentifierValue"
    ).text = "missing-agent"
    response["body"] = ET.tostring(invalid)

    result = run()

    assert result.state == "FAILURE"
    assert isinstance(result.result, TaskError)
    assert f"Cannot import METS for AIP {PACKAGE_UUID}" in str(result.result)
    document = tmp_path / f"diagnostic/mets/1/METS.{PACKAGE_UUID}.xml"
    assert document.read_bytes() == response["body"]

    response["body"] = original.replace(b"abc.txt", b"retry.txt")
    assert run().state == "SUCCESS"
    aip = AIP.query.filter_by(uuid=PACKAGE_UUID).one()
    assert aip.mets_sha256 == sha256(response["body"]).hexdigest()
    assert any(file.name == "retry.txt" for file in aip.files)
    assert not document.exists()
