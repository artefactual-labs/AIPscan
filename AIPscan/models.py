# -*- coding: utf-8 -*-

from AIPscan import db


class package_tasks(db.Model):
    __bind_key__ = "celery"
    package_task_id = db.Column(db.String(36), primary_key=True)
    workflow_coordinator_id = db.Column(db.String(36))


class get_mets_tasks(db.Model):
    __bind_key__ = "celery"
    get_mets_task_id = db.Column(db.String(36), primary_key=True)
    workflow_coordinator_id = db.Column(db.String(36))
    package_uuid = db.Column(db.String(36))
    status = db.Column(db.String())


class storage_services(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True, unique=True)
    url = db.Column(db.String(255))
    user_name = db.Column(db.String(255))
    api_key = db.Column(db.String(255))
    download_limit = db.Column(db.Integer())
    download_offset = db.Column(db.Integer())
    default = db.Column(db.Boolean)
    fetch_jobs = db.relationship(
        "fetch_jobs", cascade="all,delete", backref="storage_services", lazy=True
    )

    def __init__(
        self, name, url, user_name, api_key, download_limit, download_offset, default
    ):
        self.name = name
        self.url = url
        self.user_name = user_name
        self.api_key = api_key
        self.download_limit = download_limit
        self.download_offset = download_offset
        self.default = default

    def __repr__(self):
        return "<Storage Services '{}'>".format(self.name)


class fetch_jobs(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    total_packages = db.Column(db.Integer())
    total_aips = db.Column(db.Integer())
    total_deleted_aips = db.Column(db.Integer())
    download_start = db.Column(db.DateTime())
    download_end = db.Column(db.DateTime())
    download_directory = db.Column(db.String(255))
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_services.id"), nullable=False
    )
    aips = db.relationship(
        "aips", cascade="all,delete", backref="fetch_jobs", lazy=True
    )

    def __init__(
        self,
        total_packages,
        total_aips,
        total_deleted_aips,
        download_start,
        download_end,
        download_directory,
        storage_service_id,
    ):
        self.total_packages = total_packages
        self.total_aips = total_aips
        self.total_deleted_aips = total_deleted_aips
        self.download_start = download_start
        self.download_end = download_end
        self.download_directory = download_directory
        self.storage_service_id = storage_service_id

    def __repr__(self):
        return "<Fetch Jobs '{}'>".format(self.download_start)


class aips(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    uuid = db.Column(db.String(255), index=True)
    transfer_name = db.Column(db.String(255))
    create_date = db.Column(db.DateTime())
    originals_count = db.Column(db.Integer())
    copies_count = db.Column(db.Integer())
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_services.id"), nullable=False
    )
    fetch_job_id = db.Column(
        db.Integer(), db.ForeignKey("fetch_jobs.id"), nullable=False
    )
    originals = db.relationship(
        "originals", cascade="all,delete", backref="aips", lazy=True
    )
    copies = db.relationship("copies", cascade="all,delete", backref="aips", lazy=True)

    def __init__(
        self,
        uuid,
        transfer_name,
        create_date,
        originals_count,
        copies_count,
        storage_service_id,
        fetch_job_id,
    ):
        self.uuid = uuid
        self.transfer_name = transfer_name
        self.create_date = create_date
        self.originals_count = originals_count
        self.copies_count = copies_count
        self.storage_service_id = storage_service_id
        self.fetch_job_id = fetch_job_id

    def __repr__(self):
        return "<AIPs '{}'>".format(self.transfer_name)


class originals(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True)
    uuid = db.Column(db.String(255), index=True)
    size = db.Column(db.Integer())
    puid = db.Column(db.String(255), index=True)
    format = db.Column(db.String(255))
    format_version = db.Column(db.String(255))
    checksum_type = db.Column(db.String(255))
    checksum_value = db.Column(db.String(255))
    related_uuid = db.Column(db.String(255), index=True)
    aip_id = db.Column(db.Integer(), db.ForeignKey("aips.id"), nullable=False)
    events = db.relationship(
        "events", cascade="all,delete", backref="originals", lazy=True
    )

    def __init__(
        self,
        name,
        uuid,
        size,
        puid,
        format,
        format_version,
        checksum_type,
        checksum_value,
        related_uuid,
        aip_id,
    ):
        self.name = name
        self.uuid = uuid
        self.size = size
        self.puid = puid
        self.format = format
        self.format_version = format_version
        self.checksum_type = checksum_type
        self.checksum_value = checksum_value
        self.related_uuid = related_uuid
        self.aip_id = aip_id

    def __repr__(self):
        return "<Originals '{}'>".format(self.name)


class copies(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True)
    uuid = db.Column(db.String(255), index=True)
    size = db.Column(db.Integer())
    format = db.Column(db.String(255))
    checksum_type = db.Column(db.String(255))
    checksum_value = db.Column(db.String(255))
    related_uuid = db.Column(db.String(255), index=True)
    normalization_date = db.Column(db.DateTime())
    aip_id = db.Column(db.Integer(), db.ForeignKey("aips.id"), nullable=False)

    def __init__(
        self,
        name,
        uuid,
        size,
        format,
        checksum_type,
        checksum_value,
        related_uuid,
        normalization_date,
        aip_id,
    ):
        self.name = name
        self.uuid = uuid
        self.size = size
        self.format = format
        self.checksum_type = checksum_type
        self.checksum_value = checksum_value
        self.related_uuid = related_uuid
        self.normalization_date = normalization_date
        self.aip_id = aip_id

    def __repr__(self):
        return "<Copies '{}'>".format(self.name)


event_agents = db.Table(
    "event_agents",
    db.Column("event_id", db.Integer, db.ForeignKey("events.id")),
    db.Column("agent_id", db.Integer, db.ForeignKey("agents.id")),
)


class events(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    type = db.Column(db.String(255), index=True)
    uuid = db.Column(db.String(255), index=True)
    date = db.Column(db.DateTime())
    detail = db.Column(db.String(255))
    outcome = db.Column(db.String(255))
    outcome_detail = db.Column(db.String(255))
    original_id = db.Column(db.Integer(), db.ForeignKey("originals.id"), nullable=False)
    event_agents = db.relationship(
        "agents", secondary=event_agents, backref=db.backref("events", lazy="dynamic")
    )

    def __init__(self, type, uuid, date, detail, outcome, outcome_detail, original_id):
        self.type = type
        self.uuid = uuid
        self.date = date
        self.detail = detail
        self.outcome = outcome
        self.outcome_detail = outcome_detail
        self.original_id = original_id

    def __repr__(self):
        return "<Events '{}'>".format(self.type)


class agents(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    type = db.Column(db.String(255), index=True)
    value = db.Column(db.String(255), index=True)

    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __repr__(self):
        return "<Agents '{}'>".format(self.value)
