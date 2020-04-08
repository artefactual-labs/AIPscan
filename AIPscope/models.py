from AIPscope import db


class storage_service(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True, unique=True)
    url = db.Column(db.String(255))
    user_name = db.Column(db.String(255))
    api_key = db.Column(db.String(255))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Storage Service '{}'>".format(self.name)


class fetch_job(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    total_packages = db.Column(db.Integer())
    total_aips = db.Column(db.Integer())
    download_start = db.Column(db.DateTime())
    download_end = db.Column(db.DateTime())
    storage_service_id = db.Column(db.Integer(), db.ForeignKey("storage_service.id"))

    def __init__(self, download_end):
        self.download_end = download_end

        def __repr__(self):
            return "<Fetch Job '{}'>".format(self.download_end)
