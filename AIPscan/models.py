import enum
import re
from datetime import date
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from AIPscan import db

UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class package_tasks(db.Model):
    __bind_key__ = "celery"
    package_task_id = db.Column(db.String(36), primary_key=True)
    workflow_coordinator_id = db.Column(db.String(36))


class get_mets_tasks(db.Model):
    __bind_key__ = "celery"
    get_mets_task_id = db.Column(db.String(36), primary_key=True)
    workflow_coordinator_id = db.Column(db.String(36))
    package_uuid = db.Column(db.String(36))
    status = db.Column(db.String(36))


class index_tasks(db.Model):
    __tablename__ = "index_tasks"
    index_task_id = db.Column(db.String(36), primary_key=True)
    fetch_job_id = db.Column(
        db.Integer(), db.ForeignKey("fetch_job.id"), nullable=False
    )
    indexing_start = db.Column(db.DateTime())
    indexing_progress = db.Column(db.String(255))
    indexing_end = db.Column(db.DateTime())


class StorageService(db.Model):
    __tablename__ = "storage_service"
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True, unique=True)
    url = db.Column(db.String(255))
    user_name = db.Column(db.String(255))
    api_key = db.Column(db.String(255))
    download_limit = db.Column(db.Integer())
    download_offset = db.Column(db.Integer())
    default = db.Column(db.Boolean)
    fetch_jobs = db.relationship(
        "FetchJob", cascade="all,delete", backref="storage_service", lazy=True
    )
    storage_locations = db.relationship(
        "StorageLocation", cascade="all,delete", backref="storage_service", lazy=True
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
        return f"<Storage Service '{self.name}'>"

    @property
    def earliest_aip_created(self):
        results = (
            db.session.query(AIP.create_date).order_by(AIP.create_date.asc()).first()
        )
        try:
            return results[0]
        except TypeError:
            return date.today()

    @property
    def unique_file_formats(self):
        return (
            db.session.query(File.file_format.distinct().label("name"))
            .join(AIP)
            .join(StorageService)
            .filter(StorageService.id == self.id)
            .order_by(File.file_format)
        )

    @property
    def unique_original_file_formats(self):
        formats = self.unique_file_formats
        original_formats = formats.filter(File.file_type == FileType.original)
        return [format_.name for format_ in original_formats]

    @property
    def unique_preservation_file_formats(self):
        formats = self.unique_file_formats
        preservation_formats = formats.filter(File.file_type == FileType.preservation)
        return [format_.name for format_ in preservation_formats]

    @property
    def unique_puids(self):
        return (
            db.session.query(File.puid.distinct().label("puid"))
            .join(AIP)
            .join(StorageService)
            .filter(StorageService.id == self.id)
            .order_by(File.puid)
        )

    @property
    def unique_original_puids(self):
        puids = self.unique_puids
        original_puids = puids.filter(File.file_type == FileType.original)
        return [puid.puid for puid in original_puids if puid.puid is not None]

    @property
    def unique_preservation_puids(self):
        puids = self.unique_puids
        preservation_puids = puids.filter(File.file_type == FileType.preservation)
        return [puid.puid for puid in preservation_puids if puid.puid is not None]


class StorageLocation(db.Model):
    __tablename__ = "storage_location"
    id = db.Column(db.Integer(), primary_key=True)
    current_location = db.Column(db.String(255), unique=True, index=True)
    description = db.Column(db.String(255))
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_service.id"), nullable=False
    )
    aips = db.relationship(
        "AIP", cascade="all,delete", backref="storage_location", lazy=True
    )

    def __init__(self, current_location, description, storage_service_id):
        self.current_location = current_location
        self.description = description
        self.storage_service_id = storage_service_id

    def __repr__(self):
        return f"<StorageLocation '{self.current_location}'>"

    @property
    def uuid(self):
        match = re.search(UUID_REGEX, self.current_location)
        if match:
            return match.group(0)
        return None

    @property
    def unique_file_formats(self):
        return (
            db.session.query(File.file_format.distinct().label("name"))
            .join(AIP)
            .join(StorageLocation)
            .filter(StorageLocation.id == self.id)
            .order_by(File.file_format)
        )

    @property
    def unique_original_file_formats(self):
        formats = self.unique_file_formats
        original_formats = formats.filter(File.file_type == FileType.original)
        return [format_.name for format_ in original_formats]

    @property
    def unique_preservation_file_formats(self):
        formats = self.unique_file_formats
        preservation_formats = formats.filter(File.file_type == FileType.preservation)
        return [format_.name for format_ in preservation_formats]

    @property
    def unique_puids(self):
        return (
            db.session.query(File.puid.distinct().label("puid"))
            .join(AIP)
            .join(StorageLocation)
            .filter(StorageLocation.id == self.id)
            .order_by(File.puid)
        )

    @property
    def unique_original_puids(self):
        puids = self.unique_puids
        original_puids = puids.filter(File.file_type == FileType.original)
        return [puid.puid for puid in original_puids if puid.puid is not None]

    @property
    def unique_preservation_puids(self):
        puids = self.unique_puids
        preservation_puids = puids.filter(File.file_type == FileType.preservation)
        return [puid.puid for puid in preservation_puids if puid.puid is not None]

    def aip_count(self, start_date=None, end_date=None):
        """Return count of AIPs in this location."""
        DEFAULT = 0
        if not start_date:
            start_date = datetime.min
        if not end_date:
            end_date = datetime.max
        results = (
            db.session.query(db.func.count(AIP.id))
            .join(StorageLocation)
            .filter(AIP.storage_location_id == self.id)
            .filter(AIP.create_date >= start_date)
            .filter(AIP.create_date < end_date)
            .first()
        )
        try:
            return results[0]
        except (IndexError, TypeError):
            return DEFAULT

    def aip_total_size(self, start_date=None, end_date=None):
        """Return size in bytes of all AIPs in this location."""
        DEFAULT = 0
        if not start_date:
            start_date = datetime.min
        if not end_date:
            end_date = datetime.max
        results = (
            db.session.query(db.func.sum(File.size))
            .join(AIP)
            .join(StorageLocation)
            .filter(AIP.storage_location_id == self.id)
            .filter(AIP.create_date >= start_date)
            .filter(AIP.create_date < end_date)
            .first()
        )
        if results[0]:
            try:
                return results[0]
            except (IndexError, TypeError):
                pass
        return DEFAULT

    def file_count(self, start_date=None, end_date=None, originals=True):
        """Return number of files in this location. Defaults to originals only."""
        if not start_date:
            start_date = datetime.min
        if not end_date:
            end_date = datetime.max
        files = (
            db.session.query(File)
            .join(AIP)
            .join(StorageLocation)
            .filter(AIP.storage_location_id == self.id)
            .filter(AIP.create_date >= start_date)
            .filter(AIP.create_date < end_date)
        )
        if originals:
            files = files.filter(File.file_type == FileType.original)
        return files.count()


class FetchJob(db.Model):
    __tablename__ = "fetch_job"
    id = db.Column(db.Integer(), primary_key=True)
    total_packages = db.Column(db.Integer())
    total_aips = db.Column(db.Integer())
    total_dips = db.Column(db.Integer())
    total_sips = db.Column(db.Integer())
    total_replicas = db.Column(db.Integer())
    total_deleted_aips = db.Column(db.Integer())
    download_start = db.Column(db.DateTime())
    download_end = db.Column(db.DateTime())
    download_directory = db.Column(db.String(255))
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_service.id"), nullable=False
    )
    aips = db.relationship("AIP", cascade="all,delete", backref="fetch_job", lazy=True)
    index_tasks = db.relationship(
        "index_tasks", cascade="all,delete", backref="fetch_job", lazy=True
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
        return f"<Fetch Job '{self.download_start}'>"


class Pipeline(db.Model):
    __tablename__ = "pipeline"
    id = db.Column(db.Integer(), primary_key=True)
    origin_pipeline = db.Column(db.String(255), unique=True, index=True)
    dashboard_url = db.Column(db.Text())
    aips = db.relationship(
        "AIP", cascade="all,delete", backref="origin_pipeline", lazy=True
    )

    def __init__(self, origin_pipeline, dashboard_url):
        self.origin_pipeline = origin_pipeline
        self.dashboard_url = dashboard_url

    def __repr__(self):
        return f"<Pipeline '{self.origin_pipeline}'>"

    @property
    def uuid(self):
        match = re.search(UUID_REGEX, self.origin_pipeline)
        if match:
            return match.group(0)
        return None


class AIP(db.Model):
    __tablename__ = "aip"
    id = db.Column(db.Integer(), primary_key=True)
    uuid = db.Column(db.String(255), index=True)
    transfer_name = db.Column(db.String(255))
    create_date = db.Column(db.DateTime(), index=True)
    mets_sha256 = db.Column(db.String(64))
    size = db.Column(db.BigInteger())
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_service.id"), nullable=False
    )
    storage_location_id = db.Column(
        db.Integer(), db.ForeignKey("storage_location.id"), nullable=False
    )
    fetch_job_id = db.Column(
        db.Integer(), db.ForeignKey("fetch_job.id"), nullable=False
    )
    origin_pipeline_id = db.Column(
        db.Integer(), db.ForeignKey("pipeline.id"), nullable=False
    )
    files = db.relationship("File", cascade="all,delete", backref="aip", lazy=True)

    def __init__(
        self,
        uuid,
        transfer_name,
        create_date,
        mets_sha256,
        size,
        storage_service_id,
        storage_location_id,
        fetch_job_id,
        origin_pipeline_id,
    ):
        self.uuid = uuid
        self.transfer_name = transfer_name
        self.create_date = create_date
        self.mets_sha256 = mets_sha256
        self.size = size
        self.storage_service_id = storage_service_id
        self.storage_location_id = storage_location_id
        self.fetch_job_id = fetch_job_id
        self.origin_pipeline_id = origin_pipeline_id

    def __repr__(self):
        return f"<AIP '{self.transfer_name}'>"

    @property
    def original_file_count(self):
        return File.query.filter_by(aip_id=self.id, file_type=FileType.original).count()

    @property
    def preservation_file_count(self):
        return File.query.filter_by(
            aip_id=self.id, file_type=FileType.preservation
        ).count()


class FileType(enum.Enum):
    original = "original"
    preservation = "preservation"


class File(db.Model):
    __tablename__ = "file"
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), index=True)
    filepath = db.Column(db.Text(), nullable=True)  # Accommodate long filepaths.
    uuid = db.Column(db.String(255), index=True)
    file_type = db.Column(db.Enum(FileType))
    size = db.Column(db.BigInteger())
    # Date created maps to PREMIS dateCreatedByApplication for original
    # files, which in practice is almost always date last modified, and
    # to normalization date for preservation files.
    date_created = db.Column(db.DateTime(), index=True)
    puid = db.Column(db.String(255), index=True)
    file_format = db.Column(db.String(255))
    format_version = db.Column(db.String(255))
    checksum_type = db.Column(db.String(255))
    checksum_value = db.Column(db.String(255), index=True)
    premis_object = db.Column(sa.Text().with_variant(mysql.LONGTEXT, "mysql"))

    original_file_id = db.Column(db.Integer(), db.ForeignKey("file.id"))
    original_file = db.relationship(
        "File", remote_side=[id], backref=db.backref("derivatives")
    )

    aip_id = db.Column(db.Integer(), db.ForeignKey("aip.id"), nullable=False)
    events = db.relationship("Event", cascade="all,delete", backref="file", lazy=True)

    def __init__(
        self,
        name,
        filepath,
        uuid,
        size,
        date_created,
        file_format,
        checksum_type,
        checksum_value,
        aip_id,
        file_type=FileType.original,
        premis_object=None,
        format_version=None,
        puid=None,
        original_file_id=None,
    ):
        self.name = name
        self.filepath = filepath
        self.uuid = uuid
        self.file_type = file_type
        self.size = size
        self.date_created = date_created
        self.puid = puid
        self.file_format = file_format
        self.format_version = format_version
        self.checksum_type = checksum_type
        self.checksum_value = checksum_value
        self.premis_object = premis_object
        self.original_file_id = original_file_id
        self.aip_id = aip_id

    def __repr__(self):
        return f"<File '{self.id}' - '{self.name}'"

    # Safe accessors for PREMIS object XML, normalizing backend-specific types.
    def get_premis_object_text(self):
        """Return PREMIS object XML as a text string or None.

        Some backends/dialects may return variant-backed values such as
        bytes, bytearray, or memoryview for long text columns. This getter
        normalizes to a UTF-8 string (with replacement on decode errors)
        so callers can safely consume the value without worrying about
        the underlying SQLAlchemy variant type.
        """
        value = self.premis_object
        if value is None:
            return None
        # Normalize variant-backed binary-like values
        if isinstance(value, memoryview):
            try:
                return value.tobytes().decode("utf-8", errors="replace")
            except Exception:
                return str(value.tobytes())
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode("utf-8", errors="replace")
            except Exception:
                return str(bytes(value))
        # Fallback to string representation
        return str(value)

    def get_premis_xml_lines(self):
        """Return PREMIS object XML split into lines (list of str)."""
        text = self.get_premis_object_text()
        return text.splitlines() if text else []


EventAgent = db.Table(
    "event_agents",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id")),
    db.Column("agent_id", db.Integer, db.ForeignKey("agent.id")),
)


class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer(), primary_key=True)
    type = db.Column(db.String(255), index=True)
    uuid = db.Column(db.String(255), index=True)
    date = db.Column(db.DateTime())
    detail = db.Column(db.String(255))
    outcome = db.Column(db.String(255))
    outcome_detail = db.Column(db.Text())
    file_id = db.Column(db.Integer(), db.ForeignKey("file.id"), nullable=False)
    event_agents = db.relationship(
        "Agent", secondary=EventAgent, backref=db.backref("Event", lazy="dynamic")
    )

    def __init__(
        self, event_type, uuid, date, detail, outcome, outcome_detail, file_id
    ):
        self.type = event_type
        self.uuid = uuid
        self.date = date
        self.detail = detail
        self.outcome = outcome
        self.outcome_detail = outcome_detail
        self.file_id = file_id

    def __repr__(self):
        return f"<Event '{self.type}'>"


class Agent(db.Model):
    __tablename__ = "agent"
    id = db.Column(db.Integer(), primary_key=True)
    linking_type_value = db.Column(db.String(255), index=True)
    agent_type = db.Column(db.String(255), index=True)
    agent_value = db.Column(db.String(255), index=True)
    storage_service_id = db.Column(
        db.Integer(), db.ForeignKey("storage_service.id"), nullable=False
    )

    def __init__(self, linking_type_value, agent_type, agent_value, storage_service_id):
        self.linking_type_value = linking_type_value
        self.agent_type = agent_type
        self.agent_value = agent_value
        self.storage_service_id = storage_service_id

    def __repr__(self):
        return f"<Agent '{self.agent_type}: {self.agent_value}'>"
