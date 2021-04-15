# -*- coding: utf-8 -*-

"""Data endpoints optimized for reports in the Reporter blueprint."""

from AIPscan import db
from AIPscan.Data import _get_storage_service, fields
from AIPscan.models import AIP, Event, File, FileType, StorageService

VALID_FILE_TYPES = set(item.value for item in FileType)


def _get_username(agent_string):
    """Retrieve username from the standard agent string stored in the
    database, normally formatted as:

        * username="test", first_name="", last_name=""
    """
    USERNAME = "username="
    return agent_string.split(",", 1)[0].replace(USERNAME, "").replace('"', "")


def _formats_count_query(storage_service_id, start_date, end_date):
    """Fetch information from database on file formats.

    :param storage_service_id: Storage Service ID (int)
    :start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :end_date: Inclusive AIP creation end date
        (datetime.datetime object)

    :returns: SQLAlchemy query results
    """
    FILE_FORMAT = "file_format"
    FILE_COUNT = "file_count"
    FILE_SIZE = "total_size"

    return (
        db.session.query(
            File.file_format.label(FILE_FORMAT),
            db.func.count(File.id).label(FILE_COUNT),
            db.func.sum(File.size).label(FILE_SIZE),
        )
        .join(AIP)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.original.value)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .group_by(File.file_format)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )


def formats_count(storage_service_id, start_date, end_date):
    """Return a summary of file formats in Storage Service.

    :param storage_service_id: Storage Service ID (int)
    :start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :end_date: Inclusive AIP creation end date
        (datetime.datetime object)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Formats"]: List of results ordered desc by count and size
    """
    report = {}
    report[fields.FIELD_FORMATS] = []
    report[fields.FIELD_STORAGE_NAME] = None

    storage_service = _get_storage_service(storage_service_id)
    if storage_service is not None:
        report[fields.FIELD_STORAGE_NAME] = storage_service.name

    formats = _formats_count_query(storage_service_id, start_date, end_date)

    for format_ in formats:
        format_info = {}

        format_info[fields.FIELD_FORMAT] = format_.file_format
        format_info[fields.FIELD_COUNT] = format_.file_count
        format_info[fields.FIELD_SIZE] = 0
        if format_.total_size is not None:
            format_info[fields.FIELD_SIZE] = format_.total_size

        report[fields.FIELD_FORMATS].append(format_info)

    return report


def _format_versions_count_query(storage_service_id, start_date, end_date):
    """Fetch information from database on format versions.

    :param storage_service_id: Storage Service ID (int)
    :start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :end_date: Inclusive AIP creation end date
        (datetime.datetime object)

    :returns: SQLAlchemy query results
    """
    PUID = "puid"
    FILE_FORMAT = "file_format"
    FORMAT_VERSION = "format_version"
    FILE_COUNT = "file_count"
    FILE_SIZE = "total_size"

    return (
        db.session.query(
            File.puid.label(PUID),
            File.file_format.label(FILE_FORMAT),
            File.format_version.label(FORMAT_VERSION),
            db.func.count(File.id).label(FILE_COUNT),
            db.func.sum(File.size).label(FILE_SIZE),
        )
        .join(AIP)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.original.value)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .group_by(File.puid)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )


def format_versions_count(storage_service_id, start_date, end_date):
    """Return a summary of format versions in Storage Service.

    :param storage_service_id: Storage Service ID (int)
    :start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :end_date: Inclusive AIP creation end date
        (datetime.datetime object)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["FormatVersions"]: List of result files ordered desc by size
    """
    report = {}
    report[fields.FIELD_FORMAT_VERSIONS] = []
    report[fields.FIELD_STORAGE_NAME] = None

    storage_service = _get_storage_service(storage_service_id)
    if storage_service is not None:
        report[fields.FIELD_STORAGE_NAME] = storage_service.name

    versions = _format_versions_count_query(storage_service_id, start_date, end_date)

    for version in versions:
        version_info = {}

        version_info[fields.FIELD_PUID] = version.puid
        version_info[fields.FIELD_FORMAT] = version.file_format
        try:
            version_info[fields.FIELD_VERSION] = version.format_version
        except AttributeError:
            pass
        version_info[fields.FIELD_COUNT] = version.file_count
        version_info[fields.FIELD_SIZE] = 0
        if version.total_size is not None:
            version_info[fields.FIELD_SIZE] = version.total_size

        report[fields.FIELD_FORMAT_VERSIONS].append(version_info)

    return report


def _largest_files_query(storage_service_id, file_type, limit):
    """Fetch file information from database for largest files query

    This is separated into its own helper function to aid in testing.
    """
    if file_type is not None and file_type in VALID_FILE_TYPES:
        files = (
            File.query.join(AIP)
            .join(StorageService)
            .filter(StorageService.id == storage_service_id)
            .filter(File.file_type == file_type)
            .order_by(File.size.desc())
            .limit(limit)
        )
    else:
        files = (
            File.query.join(AIP)
            .join(StorageService)
            .filter(StorageService.id == storage_service_id)
            .order_by(File.size.desc())
            .limit(limit)
        )
    return files


def largest_files(storage_service_id, file_type=None, limit=20):
    """Return a summary of the largest files in a given Storage Service

    :param storage_service_id: Storage Service ID
    :param file_type: Optional filter for type of file to return
        (acceptable values are "original" or "preservation")
    :param limit: Upper limit of number of results to return

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Files"]: List of result files ordered desc by size
    """
    report = {}
    report[fields.FIELD_FILES] = []
    storage_service = _get_storage_service(storage_service_id)
    report[fields.FIELD_STORAGE_NAME] = storage_service.name

    files = _largest_files_query(storage_service_id, file_type, limit)

    for file_ in files:
        file_info = {}

        file_info[fields.FIELD_ID] = file_.id
        file_info[fields.FIELD_UUID] = file_.uuid
        file_info[fields.FIELD_NAME] = file_.name
        file_info[fields.FIELD_SIZE] = int(file_.size)
        file_info[fields.FIELD_AIP_ID] = file_.aip_id
        file_info[fields.FIELD_FILE_TYPE] = file_.file_type.value

        try:
            file_info[fields.FIELD_FORMAT] = file_.file_format
        except AttributeError:
            pass
        try:
            file_info[fields.FIELD_VERSION] = file_.format_version
        except AttributeError:
            pass
        try:
            file_info[fields.FIELD_PUID] = file_.puid
        except AttributeError:
            pass

        matching_aip = AIP.query.get(file_.aip_id)
        if matching_aip is not None:
            file_info[fields.FIELD_AIP_NAME] = matching_aip.transfer_name
            file_info[fields.FIELD_AIP_UUID] = matching_aip.uuid

        report[fields.FIELD_FILES].append(file_info)

    return report


def _query_aips_by_file_format_or_puid(
    storage_service_id, search_string, original_files=True, file_format=True
):
    """Fetch information on all AIPs with given format or PUID from db.

    :param storage_service_id: Storage Service ID (int)
    :param search_string: File format or PUID (str)
    :param original_files: Flag indicating whether returned data
        describes original (default) or preservation files (bool)
    :param file_format: Flag indicating whether to filter on file
        format (default) or PUID (bool)

    :returns: SQLAlchemy query results
    """
    AIP_ID = "id"
    TRANSFER_NAME = "name"
    AIP_UUID = "uuid"
    FILE_COUNT = "file_count"
    FILE_SIZE = "total_size"
    aips = (
        db.session.query(
            AIP.id.label(AIP_ID),
            AIP.transfer_name.label(TRANSFER_NAME),
            AIP.uuid.label(AIP_UUID),
            db.func.count(File.id).label(FILE_COUNT),
            db.func.sum(File.size).label(FILE_SIZE),
        )
        .join(File)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .group_by(AIP.id)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )

    if original_files is False:
        aips = aips.filter(File.file_type == FileType.preservation.value)
    else:
        aips = aips.filter(File.file_type == FileType.original.value)

    if file_format:
        return aips.filter(File.file_format == search_string)
    return aips.filter(File.puid == search_string)


def _aips_by_file_format_or_puid(
    storage_service_id, search_string, original_files=True, file_format=True
):
    """Return overview of all AIPs containing original files in format

    :param storage_service_id: Storage Service ID (int)
    :param search_string: File format name or PUID (str)
    :param original_files: Flag indicating whether returned data
        data describes original (default) or preservation files (bool)
    :param file_format: Flag indicating whether to filter on file
        file format (default) or PUID (bool)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["AIPs"]: List of result AIPs ordered desc by count
    """
    report = {}

    storage_service = _get_storage_service(storage_service_id)
    report[fields.FIELD_STORAGE_NAME] = storage_service.name

    if file_format:
        report[fields.FIELD_FORMAT] = search_string
    else:
        report[fields.FIELD_PUID] = search_string

    report[fields.FIELD_AIPS] = []
    results = _query_aips_by_file_format_or_puid(
        storage_service_id, search_string, original_files, file_format
    )
    for result in results:
        aip_info = {}

        aip_info[fields.FIELD_ID] = result.id
        aip_info[fields.FIELD_AIP_NAME] = result.name
        aip_info[fields.FIELD_UUID] = result.uuid
        aip_info[fields.FIELD_COUNT] = result.file_count
        aip_info[fields.FIELD_SIZE] = result.total_size

        report[fields.FIELD_AIPS].append(aip_info)

    return report


def aips_by_file_format(storage_service_id, file_format, original_files=True):
    """Return overview of AIPs containing original files in format.

    :param storage_service_id: Storage Service ID (int)
    :param file_format: File format name (str)
    :param original_files: Flag indicating whether returned data
        describes original (default) or preservation files (bool)

    :returns: Report dict provided by _aips_by_file_format_or_puid
    """
    return _aips_by_file_format_or_puid(
        storage_service_id=storage_service_id,
        search_string=file_format,
        original_files=original_files,
    )


def aips_by_puid(storage_service_id, puid, original_files=True):
    """Return overview of AIPs containing original files in format.

    :param storage_service_id: Storage Service ID (int)
    :param puid: PUID (str)
    :param original_files: Flag indicating whether returned data
        describes original (default) or preservation files (bool)

    :returns: Report dict provided by _aips_by_file_format_or_puid
    """
    return _aips_by_file_format_or_puid(
        storage_service_id=storage_service_id,
        search_string=puid,
        original_files=original_files,
        file_format=False,
    )


def agents_transfers(storage_service_id):
    """Return information about agents involved in creating a transfer
    and provide some simple statistics, e.g. ingest start time and
    ingest finish time.
    """
    report = {}
    ingests = []

    storage_service = _get_storage_service(storage_service_id)

    try:
        report[fields.FIELD_STORAGE_NAME] = storage_service.name
    except AttributeError:
        # No storage service has been returned and so we have nothing
        # to return.
        report[fields.FIELD_STORAGE_NAME] = None
        report[fields.FIELD_INGESTS] = ingests
        return report

    aips = AIP.query.filter_by(storage_service_id=storage_service.id).all()

    EVENT_TYPE = "ingestion"
    AGENT_TYPE = "Archivematica user"

    for aip in aips:
        event = (
            db.session.query(Event)
            .join(File)
            .filter(File.aip_id == aip.id, Event.type == EVENT_TYPE)
            .first()
        )
        # This defensive check is necessary for now because of packages that
        # are deleted after extraction. See issue #104 for details.
        if event is None:
            continue
        log_line = {}
        log_line[fields.FIELD_AIP_UUID] = aip.uuid
        log_line[fields.FIELD_AIP_NAME] = aip.transfer_name
        log_line[fields.FIELD_INGEST_START_DATE] = str(event.date)
        log_line[fields.FIELD_INGEST_FINISH_DATE] = str(aip.create_date)
        for agent in event.event_agents:
            if agent.agent_type == AGENT_TYPE:
                log_line[fields.FIELD_USER] = _get_username(agent.agent_value)
        ingests.append(log_line)
    report[fields.FIELD_INGESTS] = ingests
    return report
