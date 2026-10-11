"""An HTTP Storage Service boundary fixture for updates and failed requests.

The main acceptance corpus still uses real ambox ingest and stored archives.
This service provides controlled responses through the same application paths.
"""

import json
from copy import deepcopy
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

UUID = "33333333-3333-4333-8333-333333333333"
STATE = {"mode": "normal", "name": "boundary-original", "lists": 0}
LOCK = Lock()
NS = {"m": "http://www.loc.gov/METS/", "p": "info:lc/xmlns/premis-v2"}


def expand_originals(mets):
    """Keep the legacy layout but supply 1,200 originals with varied sizes."""
    file_sec = mets.find("m:fileSec", NS)
    original = deepcopy(file_sec.find("m:fileGrp[@USE='original']/m:file", NS))
    amd = deepcopy(mets.find("m:amdSec", NS))
    for section in list(amd):
        if section.tag != f"{{{NS['m']}}}techMD":
            amd.remove(section)
    for section in mets.findall("m:amdSec", NS):
        mets.remove(section)
    for group in list(file_sec):
        file_sec.remove(group)
    group = ET.SubElement(file_sec, f"{{{NS['m']}}}fileGrp", USE="original")
    objects = mets.find(
        "m:structMap[@TYPE='physical']/m:div/m:div[@LABEL='objects']", NS
    )
    for child in list(objects):
        objects.remove(child)
    for index in range(1200):
        uuid = f"00000000-0000-4000-8000-{index:012d}"
        metadata = deepcopy(amd)
        metadata.set("ID", f"amdSec_many_{index}")
        metadata.find("m:techMD", NS).set("ID", f"techMD_many_{index}")
        metadata.find(".//p:objectIdentifierValue", NS).text = uuid
        metadata.find(".//p:size", NS).text = str(index % 7 + 1)
        mets.append(metadata)
        file = deepcopy(original)
        file.set("ID", f"file-{uuid}")
        file.set("GROUPID", f"Group-{uuid}")
        file.set("ADMID", metadata.get("ID"))
        file.find("m:FLocat", NS).set(
            "{http://www.w3.org/1999/xlink}href", f"objects/file-{index}.txt"
        )
        group.append(file)
        item = ET.SubElement(
            objects, f"{{{NS['m']}}}div", TYPE="Item", LABEL=f"file-{index}.txt"
        )
        ET.SubElement(item, f"{{{NS['m']}}}fptr", FILEID=file.get("ID"))


class Handler(BaseHTTPRequestHandler):
    def respond(self, body, status=200, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/control":
            return self.respond({}, 404)
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with LOCK:
            STATE.update(data, lists=0)
        self.respond({"state": "configured"})

    def do_GET(self):
        path = urlsplit(self.path).path.rstrip("/")
        with LOCK:
            if path == "/api/v2/file":
                STATE["lists"] += 1
            state = STATE.copy()
        if path == "/api/v2/file":
            # Allow the initial connection probe, then fail the worker request.
            if state["mode"] == "listing-failure" and state["lists"] > 1:
                return self.respond({"error": "Storage unavailable"}, 503)
            return self.respond(
                {
                    "meta": {"total_count": 1, "next": None},
                    "objects": [
                        {
                            "uuid": UUID,
                            "package_type": "AIP",
                            "status": "DELETED"
                            if state["mode"] == "deleted"
                            else "UPLOADED",
                            "current_location": "/api/v2/location/boundary/",
                            "origin_pipeline": "/api/v2/pipeline/boundary/",
                            "current_path": f"{UUID}/boundary-{UUID}.7z",
                            "size": 1000,
                            "replicas": [],
                        }
                    ],
                }
            )
        if path == "/api/v2/location/boundary":
            return self.respond({"description": "Boundary fixture location"})
        if path == "/api/v2/pipeline/boundary":
            return self.respond({"remote_name": "http://fault-storage:8000"})
        if path == f"/api/v2/file/{UUID}/extract_file":
            if state["mode"] == "invalid-mets":
                return self.respond(b"<invalid>", content_type="application/xml")
            if state["mode"] == "missing-mets":
                return self.respond({"error": "METS unavailable"}, 404)
            if state["mode"] == "images":
                mets = (
                    Path("/images.xml")
                    .read_bytes()
                    .replace(b"2d718ecf-828a-4487-83ce-873cf9edca1a", UUID.encode())
                )
                return self.respond(mets, content_type="application/xml")
            mets = ET.fromstring(Path("/legacy.xml").read_bytes())
            if state["mode"] == "many-files":
                expand_originals(mets)
            if state["mode"] == "missing-sizes":
                for parent in mets.iter():
                    for child in list(parent):
                        if child.tag.endswith("}size"):
                            parent.remove(child)
            if state["mode"] == "missing-event-agent":
                mets.find(".//p:linkingAgentIdentifierValue", NS).text = "missing-agent"
            mets.find(
                "{http://www.loc.gov/METS/}structMap[@TYPE='physical']/{http://www.loc.gov/METS/}div"
            ).set("LABEL", f"{state['name']}-{UUID}")
            return self.respond(ET.tostring(mets), content_type="application/xml")
        self.respond({}, 404)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
