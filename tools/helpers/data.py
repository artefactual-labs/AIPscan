import os
from datetime import date

from faker import Faker

from AIPscan import db
from AIPscan.models import (
    AIP,
    FetchJob,
    File,
    Pipeline,
    StorageLocation,
    StorageService,
)

# Initialize Faker instance
fake = Faker()


def seed(seed):
    fake.seed_instance(seed)


def randint(start, end):
    return fake.random.randint(start, end)


def create_or_fetch_fake_pipeline():
    pipeline = db.session.query(Pipeline).first()

    if pipeline is None:
        pipeline = Pipeline(origin_pipeline=fake.uuid4(), dashboard_url=fake.url())

        db.session.add(pipeline)
        db.session.commit()

    return pipeline


def create_fake_storage_service(default):
    ss = StorageService(
        name=fake.text(20)[:-1],
        url=fake.url(),
        user_name=fake.profile()["username"],
        api_key=fake.password(),
        download_limit=0,
        download_offset=0,
        default=default,
    )

    db.session.add(ss)
    db.session.commit()

    return ss


def create_fake_fetch_job(storage_service_id):
    fetch_job = FetchJob(
        total_packages=0,
        total_aips=0,
        total_deleted_aips=0,
        download_start=date.today(),
        download_end=date.today(),
        download_directory=fake.file_path(),
        storage_service_id=storage_service_id,
    )
    fetch_job.total_dips = 0
    fetch_job.total_sips = 0
    fetch_job.total_replicas = 0

    db.session.add(fetch_job)
    db.session.commit()

    return fetch_job


def create_fake_location(storage_service_id):
    current_location = os.path.join(os.path.dirname(fake.file_path(3)), fake.uuid4())

    location = StorageLocation(
        current_location=current_location,
        description=fake.text(20)[:-1],
        storage_service_id=storage_service_id,
    )

    db.session.add(location)
    db.session.commit()

    return location


def create_fake_aip(pipeline_id, storage_service_id, storage_location_id, fetch_job_id):
    aip = AIP(
        uuid=fake.uuid4(),
        transfer_name=fake.text(20)[:-1],
        create_date=date.today(),
        mets_sha256=fake.sha256(),
        size=randint(10000, 100_000_000),
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        fetch_job_id=fetch_job_id,
        origin_pipeline_id=pipeline_id,
    )

    db.session.add(aip)
    db.session.commit()

    return aip


def create_fake_aip_files(min, max, aip_id):
    for _ in range(1, randint(min, max)):
        aipfile = File(
            aip_id=aip_id,
            name=fake.text(20)[:-1],
            filepath=fake.file_path(),
            uuid=fake.uuid4(),
            file_type="original",
            size=randint(1000, 1_000_000),
            date_created=date.today(),
            puid=fake.text(20)[:-1],
            file_format=fake.text(20)[:-1],
            format_version=fake.text(20)[:-1],
            checksum_type=fake.text(20)[:-1],
            checksum_value=fake.text(20)[:-1],
            premis_object="",
        )

        db.session.add(aipfile)
        db.session.commit()
