"""HTTP acceptance test, run inside Dagger's isolated services."""

import base64
import csv
import io
import json
import time
from collections import deque

import requests
from charts import check_charts
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


def main():
    # A listening HTTP port alone does not mean ambox's bootstrap has finished.
    def ready():
        response = requests.get(
            "http://ambox:64080/api/processing-configuration/automated/",
            headers=AUTH,
            timeout=30,
        )
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
    for name, uuid in [
        ("easy_1488911181", legacy_uuid),
        ("unidentified-transfer", unknown_uuid),
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
                "size": 4,
                "events": [
                    PREMISEvent(
                        event_identifier_type="UUID",
                        event_identifier_value=uuid,
                        event_type="compression",
                        event_date_time="2017-03-07T18:24:38",
                        event_detail="program=7z; version=16.02; algorithm=lzma",
                        event_outcome="0",
                    ).data
                ],
            },
        ).json()
        assert legacy["status"] == "UPLOADED", legacy

    job = request("POST", "http://aipscan:5000/aggregator/new_fetch_job/1").json()

    def listed():
        result = request(
            "GET",
            f"http://aipscan:5000/aggregator/package_list_task_status/{job['taskId']}",
        ).json()
        assert result["state"] != "FAILURE", result
        return result if result["state"] == "SUCCESS" else None

    wait_for("package listing", listed)

    def exported(uuid):
        response = request(
            "GET",
            "http://aipscan:5000/reporter/aip_contents/",
            params={
                "amss_id": 1,
                "start_date": "2000-01-01",
                "end_date": "2100-01-01",
                "csv": "true",
            },
        )
        rows = list(csv.DictReader(io.StringIO(response.text)))
        matches = [row for row in rows if row["UUID"] == uuid]
        if matches and matches[0]["Formats"]:
            return matches[0]
        return None

    row = wait_for("AIP contents", lambda: exported(sip), timeout=120)
    assert row["AIP Name"] == "aipscan-e2e", row
    assert int(row["Size (bytes)"]) == len(b"AIPscan end-to-end test.\n"), row
    assert row["Formats"] == "x-fmt/111 (Plain Text): 1 file", row
    print(json.dumps(row, indent=2))
    legacy_row = wait_for(
        "legacy AIP contents", lambda: exported(legacy_uuid), timeout=120
    )
    assert legacy_row["AIP Name"] == "easy_1488911181", legacy_row
    assert int(legacy_row["Size (bytes)"]) == 4, legacy_row
    assert legacy_row["Formats"] == "x-fmt/111 (Plain Text): 1 file", legacy_row
    print(json.dumps(legacy_row, indent=2))
    unknown_row = wait_for(
        "unidentified AIP contents", lambda: exported(unknown_uuid), timeout=120
    )
    assert unknown_row["AIP Name"] == "unidentified-transfer", unknown_row
    assert int(unknown_row["Size (bytes)"]) == 4, unknown_row
    assert unknown_row["Formats"] == "Unknown (Unknown): 1 file", unknown_row
    print(json.dumps(unknown_row, indent=2))
    formats_csv = request(
        "GET",
        "http://aipscan:5000/reporter/report_formats_count/",
        params={
            "amss_id": 1,
            "start_date": "2000-01-01",
            "end_date": "2100-01-01",
            "csv": "true",
        },
    )
    formats = {
        row["Format"]: (int(row["Count"]), int(row["Size (bytes)"]))
        for row in csv.DictReader(io.StringIO(formats_csv.text))
    }
    assert formats == {
        "Plain Text": (2, len(b"AIPscan end-to-end test.\n") + 4),
        "Unknown": (1, 4),
    }, formats
    check_charts()
    print("End-to-end reports passed")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Recent HTTP responses:", json.dumps(list(HISTORY), indent=2))
        raise
