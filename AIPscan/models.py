from AIPscan import db


class storage_services(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True, unique=True)
    url = db.Column(db.String(255))
    user_name = db.Column(db.String(255))
    api_key = db.Column(db.String(255))
    default = db.Column(db.Boolean)
    fetch_jobs = db.relationship(
        "fetch_jobs", cascade="all,delete", backref="storage_services", lazy=True
    )

    def __init__(self, name, url, user_name, api_key, default):
        self.name = name
        self.url = url
        self.user_name = user_name
        self.api_key = api_key
        self.default = default

    def __repr__(self):
        return "<Storage Services '{}'>".format(self.name)


class fetch_jobs(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    total_packages = db.Column(db.Integer())
    total_aips = db.Column(db.Integer())
    download_start = db.Column(db.DateTime())
    download_end = db.Column(db.DateTime())
    download_directory = db.Column(db.String(255))
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_services.id"), nullable=False
    )

    def __init__(
        self,
        total_packages,
        total_aips,
        download_start,
        download_end,
        storage_service_id,
    ):
        self.total_packages = total_packages
        self.total_aips = total_aips
        self.download_start = download_start
        self.download_end = download_end
        self.storage_service_id = storage_service_id

    def __repr__(self):
        return "<Fetch Jobs '{}'>".format(self.download_end)
