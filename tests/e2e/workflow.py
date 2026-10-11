"""HTTP acceptance test, run inside Dagger's isolated services."""

import base64
import csv
import io
import json
import os
import time
from collections import deque
from pathlib import Path

import requests
from lxml import html
from metsrw.plugins.premisrw import PREMISAgent
from metsrw.plugins.premisrw import PREMISEvent

HISTORY = deque(maxlen=20)
AUTH = {"Authorization": "ApiKey test:test"}


def request(method, url, **kwargs):
    response = requests.request(method, url, timeout=120, **kwargs)
    HISTORY.append((method, url, response.status_code, response.text[:4000]))
    response.raise_for_status()
    return response


def wait_for(description, check, timeout=600):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(2)
    raise AssertionError(f"Timed out waiting for {description}")


def unit_complete(kind, uuid):
    response = requests.get(
        f"http://ambox:64080/api/{kind}/status/{uuid}/", headers=AUTH, timeout=30
    )
    HISTORY.append((kind, uuid, response.status_code, response.text))
    if response.status_code == 400:
        return None  # The API may not know the unit immediately after submission.
    response.raise_for_status()
    result = response.json()
    assert result["status"] not in {"FAILED", "REJECTED", "USER_INPUT"}, result
    return result if result["status"] == "COMPLETE" else None


def seed_repository():
    # A listening HTTP port alone does not mean ambox's bootstrap has finished.
    def ready():
        try:
            response = requests.get(
                "http://ambox:64080/api/processing-configuration/automated/",
                headers=AUTH,
                timeout=30,
            )
        except requests.ConnectionError:
            return False
        HISTORY.append(("ready", response.status_code, response.text[:1000]))
        return response.status_code == 200

    wait_for("ambox configuration", ready, timeout=180)
    transfer = request(
        "POST",
        "http://ambox:64080/api/v2beta/package/",
        headers=AUTH,
        json={
            "name": "aipscan-e2e",
            "type": "standard",
            "path": base64.b64encode(
                b"/home/archivematica/transfers/aipscan-e2e"
            ).decode(),
            "processing_config": "automated",
            "auto_approve": True,
        },
    ).json()["id"]
    print(f"Transfer: {transfer}")
    sip = wait_for("transfer", lambda: unit_complete("transfer", transfer))["sip_uuid"]
    wait_for("ingest", lambda: unit_complete("ingest", sip))
    package = request(
        "GET", f"http://ambox:64081/api/v2/file/{sip}/", headers=AUTH
    ).json()
    assert package["status"] == "UPLOADED", package
    print(f"Stored AIP: {sip}")

    # Store the production METS and its unidentified-format variant without
    # regenerating their metadata in a new ingest.
    legacy_uuid = "80f077d8-2a6f-49e2-9327-903c36d6d92d"
    unknown_uuid = "11111111-1111-4111-8111-111111111111"
    locations = request(
        "GET", "http://ambox:64081/api/v2/location/?limit=100", headers=AUTH
    ).json()["objects"]
    source = next(
        location
        for location in locations
        if location["purpose"] == "TS" and location["path"].rstrip("/") == "/home"
    )
    archive_metadata = json.loads(
        Path(__file__).with_name("legacy-packages.json").read_text()
    )
    for kind, name, uuid in [
        ("legacy", "easy_1488911181", legacy_uuid),
        ("unknown", "unidentified-transfer", unknown_uuid),
    ]:
        archive = f"{name}-{uuid}.7z"
        legacy = request(
            "POST",
            "http://ambox:64081/api/v2/file/",
            headers=AUTH,
            json={
                "uuid": uuid,
                "package_type": "AIP",
                "origin_pipeline": package["origin_pipeline"],
                "origin_location": source["resource_uri"],
                "origin_path": f"archivematica/transfers/{archive}",
                "current_location": package["current_location"],
                "current_path": archive,
                "size": archive_metadata["sizes"][kind],
                "events": [
                    PREMISEvent(
                        event_identifier_type="UUID",
                        event_identifier_value=uuid,
                        event_type="compression",
                        event_date_time="2017-03-07T18:24:38",
                        event_detail=f"program=7z; version={archive_metadata['version']}; algorithm=lzma",
                        event_outcome="0",
                        linking_agent_identifier_type="local",
                        linking_agent_identifier_value="aipscan-e2e-packager",
                    ).data
                ],
                "agents": [
                    PREMISAgent(
                        agent_identifier_type="local",
                        agent_identifier_value="aipscan-e2e-packager",
                        agent_name="AIPscan acceptance fixture packager",
                        agent_type="software",
                    ).data
                ],
            },
        ).json()
        assert legacy["status"] == "UPLOADED", legacy

    return {"modern": sip, "legacy": legacy_uuid, "unknown": unknown_uuid}


def configure_storage_service(storage_service_id=1, **changes):
    """Use the normal form and its session-bound CSRF token."""
    url = f"http://aipscan:5000/aggregator/edit_storage_service/{storage_service_id}"
    with requests.Session() as session:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        form = html.fromstring(response.text).forms[0]
        response = session.post(
            url, data=dict(form.form_values()) | changes, timeout=30
        )
        response.raise_for_status()
        assert response.url.endswith("/aggregator/storage_services"), response.text


def fetch_repository(storage_service_id=1):
    job = request(
        "POST", f"http://aipscan:5000/aggregator/new_fetch_job/{storage_service_id}"
    ).json()

    def listed():
        result = request(
            "GET",
            f"http://aipscan:5000/aggregator/package_list_task_status/{job['taskId']}",
        ).json()
        assert result["state"] != "FAILURE", result
        return result if result["state"] == "SUCCESS" else None

    coordinator = wait_for("package listing", listed)["coordinatorId"]
    states = []

    def imported():
        result = request(
            "GET",
            f"http://aipscan:5000/aggregator/get_mets_task_status/{coordinator}",
            params={"totalAIPs": len(states), "fetchJobId": job["fetchJobId"]},
        ).json()
        if isinstance(result, list):
            states.extend(result)
            assert all(row["state"] == "SUCCESS" for row in result), result
            return False
        assert result["state"] != "FAILURE", result
        return result["state"] == "COMPLETED"

    wait_for("fetch completion", imported, timeout=180)
    job["imports"] = states
    if os.getenv("AIPSCAN_INDEXED") == "1":
        request(
            "GET", f"http://aipscan:5000/aggregator/index_refresh/{job['fetchJobId']}"
        )

        def indexed():
            result = request(
                "GET",
                f"http://aipscan:5000/aggregator/indexing_status/{job['fetchJobId']}",
            ).json()
            return result["state"] == "COMPLETED"

        wait_for("index completion", indexed, timeout=120)

    return job


PARAMS = {"amss_id": 1, "start_date": "2000-01-01", "end_date": "2100-01-01"}


def report_rows(report, prefix="", **params):
    response = request(
        "GET",
        f"http://aipscan:5000{prefix}/reporter/{report}/",
        params=PARAMS | params | {"csv": "true"},
    )
    return list(csv.DictReader(io.StringIO(response.text)))


def aip_row(uuid):
    matches = [row for row in report_rows("aip_contents") if row["UUID"] == uuid]
    return matches[0] if matches and matches[0]["Formats"] else None
