"""A synchronous CLI fetch persists completion without browser polling."""

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import pytest

from AIPscan import db
from AIPscan import test_helpers
from AIPscan.models import AIP
from AIPscan.models import FetchJob

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_UUID = "80f077d8-2a6f-49e2-9327-903c36d6d92d"
METS = Path(__file__).parent / "fixtures/legacy_mets/production-aip-mets-file.xml"


@pytest.mark.parametrize("package_type", ["AIP", "DIP"])
def test_fetch_cli_records_completion(app_instance, tmp_path, package_type):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path.rstrip("/")
            if path.endswith("extract_file"):
                body = METS.read_bytes()
            elif path == "/api/v2/location/cli":
                body = json.dumps({"description": "CLI storage"}).encode()
            elif path == "/api/v2/pipeline/cli":
                body = json.dumps({"remote_name": "localhost"}).encode()
            elif path == "/api/v2/file":
                body = json.dumps(
                    {
                        "meta": {"total_count": 1, "next": None},
                        "objects": [
                            {
                                "uuid": PACKAGE_UUID,
                                "package_type": package_type,
                                "status": "UPLOADED",
                                "current_location": "/api/v2/location/cli/",
                                "origin_pipeline": "/api/v2/pipeline/cli/",
                                "current_path": f"0000-0000-0000-0000-0000-0000-0000-0000-/cli-{PACKAGE_UUID}.7z",
                                "size": 1000,
                            }
                        ],
                    }
                ).encode()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    storage = test_helpers.create_test_storage_service(
        url=f"http://127.0.0.1:{server.server_port}"
    )
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/fetch_aips"),
                "--ss-id",
                str(storage.id),
                "--session-id",
                "cli-fetch",
            ],
            cwd=ROOT,
            env=os.environ
            | {
                "PYTHONPATH": str(ROOT),
                "SQLALCHEMY_DATABASE_URI": app_instance.config[
                    "SQLALCHEMY_DATABASE_URI"
                ],
                "AGGREGATOR_DOWNLOAD_ROOT": str(tmp_path),
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert "Processing complete." in result.stderr
        # Read a fresh transaction after the separate CLI process commits.
        db.session.remove()
        job = FetchJob.query.filter_by(storage_service_id=storage.id).one()
        assert job.total_packages == 1
        assert job.download_end is not None
        assert job.download_end >= job.download_start
        if package_type == "AIP":
            aip = AIP.query.filter_by(uuid=PACKAGE_UUID).one()
            assert aip.fetch_job_id == job.id
            assert aip.original_file_count > 0
        else:
            assert job.total_dips == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
