from AIPscope import db
from .models import fetch_jobs, storage_services
from datetime import datetime


def adddata():
    ss1 = storage_services(
        name="Artefactual AMdemo 1.11",
        url="https://amdemo.artefactual.com:8000",
        user_name="test",
        api_key="cfbb2ae9677d80eac64c40f10ec84b865b4b4bc2",
    )
    ss2 = storage_services(
        name="AM Bionic 1.11 QA",
        url="http://am111bionic.qa.archivematica.net:8000",
        user_name="test",
        api_key="test110x",
    )
    fetch1 = fetch_jobs(
        total_packages="3",
        total_aips="1",
        download_start=datetime(2020, 4, 7, 16, 10, 51),
        download_end=datetime(2020, 4, 7, 16, 10, 54),
        storage_service_id="1",
    )
    fetch2 = fetch_jobs(
        total_packages="75",
        total_aips="42",
        download_start=datetime(2020, 4, 5, 20, 2, 45),
        download_end=datetime(2020, 4, 5, 20, 3, 34),
        storage_service_id="2",
    )
    fetch3 = fetch_jobs(
        total_packages="4",
        total_aips="2",
        download_start=datetime(2020, 4, 7, 20, 35, 6),
        download_end=datetime(2020, 4, 7, 20, 35, 11),
        storage_service_id="1",
    )
    db.session.add(ss1)
    db.session.add(ss2)
    db.session.add(fetch1)
    db.session.add(fetch2)
    db.session.add(fetch3)
    db.session.commit()
    return ()
