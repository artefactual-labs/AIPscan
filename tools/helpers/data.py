import pathlib
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

from AIPscan import db
from AIPscan.models import (
    AIP,
    Agent,
    Event,
    EventAgent,
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


def format_types_from_csv(filepath):
    df = pd.read_csv(filepath)
    return df.to_dict(orient="records")


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
        download_start=datetime.today(),
        download_end=datetime.today(),
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
    current_location = str(pathlib.Path(fake.file_path(3)).parent / fake.uuid4())

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
        create_date=fake.date_time_between(start_date="-5y"),
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


def create_fake_aip_files(min_files, max_files, agents, aip, format_types):
    for _ in range(1, randint(min_files, max_files)):
        # Pick a format type and use it to create a fake filepath
        format_type = random.choice(format_types)
        filepath = fake.file_path()
        filepath_obj = pathlib.Path(fake.file_path())

        extension = str(format_type["extensions"]).split(",")[0]
        filepath = str(filepath_obj.with_suffix("." + extension))
        filename = filepath_obj.name

        aipfile = File(
            aip_id=aip.id,
            name=filename,
            filepath=filepath,
            uuid=fake.uuid4(),
            file_type="original",
            size=randint(1000, 1_000_000),
            date_created=aip.create_date,
            puid=format_type["puid"],
            file_format=format_type["name"],
            format_version=format_type["version"],
            checksum_type=fake.text(20)[:-1],
            checksum_value=fake.text(20)[:-1],
            premis_object="",
        )

        db.session.add(aipfile)
        db.session.commit()

        create_fake_ingestion_events_for_file(aipfile.id, aip.create_date, agents)


def create_fake_agents_for_storage_service(storage_service_id):
    software_agent = Agent(
        linking_type_value="preservation system-Archivematica-1.15.1",
        agent_type="software",
        agent_value="Archivematica",
        storage_service_id=storage_service_id,
    )

    db.session.add(software_agent)

    organization_agent = Agent(
        linking_type_value="repository code-test id",
        agent_type="organization",
        agent_value="Test Org",
        storage_service_id=storage_service_id,
    )

    db.session.add(organization_agent)

    fake_archivematica_usernames = ["admin", "alice", "bob"]
    user_agents = []

    for fake_username in fake_archivematica_usernames:
        user_agent = Agent(
            linking_type_value="Archivematica user pk-1",
            agent_type="Archivematica user",
            agent_value=f'username="{fake_username}", first_name="", last_name=""',
            storage_service_id=storage_service_id,
        )
        user_agents.append(user_agent)

        db.session.add(user_agent)
        db.session.commit()

    return {
        "software": software_agent,
        "organization": organization_agent,
        "agent": user_agents,
    }


def create_fake_ingestion_events_for_file(file_id, aip_start_date, agents):
    start_datetime = aip_start_date - timedelta(minutes=30)
    event_datetime = fake.date_time_between(
        start_date=start_datetime, end_date=aip_start_date
    )

    event = Event(
        event_type="ingestion",
        uuid=fake.uuid4(),
        date=event_datetime,
        detail="",
        outcome="",
        outcome_detail="",
        file_id=file_id,
    )

    db.session.add(event)
    db.session.commit()

    for agent_type in agents.keys():
        if type(agents[agent_type]) is list:
            # Pick random agent if type has multiple agents
            agent = random.choice(agents[agent_type])
        else:
            agent = agents[agent_type]

        event_agent = EventAgent.insert().values(event_id=event.id, agent_id=agent.id)

        db.session.execute(event_agent)
        db.session.commit()
