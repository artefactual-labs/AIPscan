from AIPscan import db


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
    originals = db.Column(db.Integer())
    preservation_copies = db.Column(db.Integer())
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_services.id"), nullable=False
    )
    fetch_job_id = db.Column(
        db.Integer(), db.ForeignKey("fetch_jobs.id"), nullable=False
    )
    files = db.relationship("files", cascade="all,delete", backref="aips", lazy=True)

    def __init__(
        self,
        uuid,
        transfer_name,
        create_date,
        originals,
        preservation_copies,
        storage_service_id,
        fetch_job_id,
    ):
        self.uuid = uuid
        self.transfer_name = transfer_name
        self.create_date = create_date
        self.originals = originals
        self.preservation_copies = preservation_copies
        self.storage_service_id = storage_service_id
        self.fetch_job_id = fetch_job_id

    def __repr__(self):
        return "<AIPs '{}'>".format(self.transfer_name)


class files(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True)
    uuid = db.Column(db.String(255), index=True)
    type = db.Column(db.String(255), index=True)
    size = db.Column(db.Integer())
    puid = db.Column(db.String(255), index=True)
    format = db.Column(db.String(255))
    format_version = db.Column(db.String(255))
    related_uuid = db.Column(db.String(255), index=True)
    ingestion_date = db.Column(db.DateTime())
    normalization_date = db.Column(db.DateTime())
    aip_id = db.Column(db.Integer(), db.ForeignKey("aips.id"), nullable=False)

    def __init__(
        self,
        name,
        uuid,
        type,
        size,
        puid,
        format,
        format_version,
        related_uuid,
        ingestion_date,
        normalization_date,
        aip_id,
    ):
        self.name = name
        self.uuid = uuid
        self.type = type
        self.size = size
        self.puid = puid
        self.format = format
        self.format_version = format_version
        self.related_uuid = related_uuid
        self.ingestion_date = ingestion_date
        self.normalization_date = normalization_date
        self.aip_id = aip_id

    def __repr__(self):
        return "<Files '{}'>".format(self.name)
