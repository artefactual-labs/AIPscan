# -*- coding: utf-8 -*-

from AIPscan import db
from AIPscan.helpers import _simplify_datetime
from AIPscan.models import AIP, Event, File, FileType, StorageService

VALID_FILE_TYPES = set(item.value for item in FileType)

FIELD_AIP_ID = "AIPID"
FIELD_AIP_NAME = "AIPName"
FIELD_AIP_SIZE = "AIPSize"
FIELD_AIP_UUID = "AIPUUID"
FIELD_AIPS = "AIPs"
FIELD_ALL_AIPS = "AllAIPs"

FIELD_COUNT = "Count"
FIELD_CREATED_DATE = "CreatedDate"

FIELD_DERIVATIVE_COUNT = "DerivativeCount"
FIELD_DERIVATIVE_FORMAT = "DerivativeFormat"
FIELD_DERIVATIVE_UUID = "DerivativeUUID"

FIELD_EVENT = "Event"

FIELD_FILES = "Files"
FIELD_FILE_COUNT = "FileCount"
FIELD_FILE_TYPE = "FileType"
FIELD_FILENAME = "Filename"
FIELD_FORMAT = "Format"
FIELD_FORMATS = "Formats"

FIELD_INGESTS = "Ingests"
FIELD_INGEST_START_DATE = "IngestStartDate"
FIELD_INGEST_FINISH_DATE = "IngestFinishDate"

FIELD_NAME = "Name"

FIELD_ORIGINAL_UUID = "OriginalUUID"
FIELD_ORIGINAL_FORMAT = "OriginalFormat"

FIELD_PUID = "PUID"

FIELD_RELATED_PAIRING = "RelatedPairing"

FIELD_SIZE = "Size"
FIELD_STORAGE_NAME = "StorageName"

FIELD_TRANSFER_NAME = "TransferName"

FIELD_USER = "User"
FIELD_UUID = "UUID"

FIELD_VERSION = "Version"


def _get_storage_service(storage_service_id):
    """Return Storage Service with ID or None.

    Unlike elsewhere in our application, here we do not fall back to
    a different StorageService if the user-supplied ID is invalid to
    prevent inaccurate information from being returned.

    :param storage_service_id: Storage Service ID

    :returns: StorageService object or None
    """
    return StorageService.query.get(storage_service_id)


def _get_username(agent_string):
    """Retrieve username from the standard agent string stored in the
    database, normally formatted as:

        * username="test", first_name="", last_name=""
    """
    USERNAME = "username="
    return agent_string.split(",", 1)[0].replace(USERNAME, "").replace('"', "")


def aip_overview(storage_service_id, original_files=True):
    """Return a summary overview of all AIPs in a given storage service"""
    report = {}
    storage_service = _get_storage_service(storage_service_id)
    aips = AIP.query.filter_by(storage_service_id=storage_service.id).all()
    for aip in aips:
        files = None
        if original_files is True:
            files = File.query.filter_by(aip_id=aip.id, file_type=FileType.original)
        else:
            files = File.query.filter_by(aip_id=aip.id, file_type=FileType.preservation)
        for file_ in files:
            # Originals have PUIDs but Preservation Masters don't.
            # Return a key (PUID or Format Name) for our report based on that.
            try:
                format_key = file_.puid
            except AttributeError:
                format_key = file_.file_format
            if format_key in report:
                report[format_key][FIELD_COUNT] = report[format_key][FIELD_COUNT] + 1
                if aip.uuid not in report[format_key][FIELD_AIPS]:
                    report[format_key][FIELD_AIPS].append(aip.uuid)
            else:
                report[format_key] = {}
                report[format_key][FIELD_COUNT] = 1
                try:
                    report[format_key][FIELD_VERSION] = file_.format_version
                    report[format_key][FIELD_NAME] = file_.file_format
                except AttributeError:
                    pass
                if report[format_key].get(FIELD_AIPS) is None:
                    report[format_key][FIELD_AIPS] = []
                report[format_key][FIELD_AIPS].append(aip.uuid)
    return report


def aip_overview_two(storage_service_id, original_files=True):
    """Return a summary overview of all AIPs in a given storage service.
    With a special focus on file formats and their counts organized by
    AIP UUID and then PUID.
    """
    report = {}
    formats = {}
    storage_service = _get_storage_service(storage_service_id)
    aips = AIP.query.filter_by(storage_service_id=storage_service.id).all()
    for aip in aips:
        report[aip.uuid] = {}
        report[aip.uuid][FIELD_AIP_NAME] = aip.transfer_name
        report[aip.uuid][FIELD_CREATED_DATE] = _simplify_datetime(
            aip.create_date, False
        )
        report[aip.uuid][FIELD_AIP_SIZE] = 0
        report[aip.uuid][FIELD_FORMATS] = {}
        files = None
        format_key = None
        if original_files is True:
            files = File.query.filter_by(aip_id=aip.id, file_type=FileType.original)
        else:
            files = File.query.filter_by(aip_id=aip.id, file_type=FileType.preservation)
        for file_ in files:
            try:
                format_key = file_.puid
            except AttributeError:
                format_key = file_.file_format
            if format_key is None:
                continue
            try:
                formats[format_key] = "{} {}".format(
                    file_.file_format, file_.format_version
                )
            except AttributeError:
                formats[format_key] = "{}".format(file_.file_format)
            size = report[aip.uuid][FIELD_AIP_SIZE]
            try:
                report[aip.uuid][FIELD_AIP_SIZE] = size + file_.size
            # TODO: Find out why size is sometimes None.
            except TypeError:
                report[aip.uuid][FIELD_AIP_SIZE] = size
                pass
            if format_key not in report[aip.uuid][FIELD_FORMATS]:
                report[aip.uuid][FIELD_FORMATS][format_key] = {}
                report[aip.uuid][FIELD_FORMATS][format_key][FIELD_COUNT] = 1
                try:
                    report[aip.uuid][FIELD_FORMATS][format_key][
                        FIELD_VERSION
                    ] = file_.format_version
                    report[aip.uuid][FIELD_FORMATS][format_key][
                        FIELD_NAME
                    ] = file_.file_format
                except AttributeError:
                    pass
            else:
                count = report[aip.uuid][FIELD_FORMATS][format_key][FIELD_COUNT]
                report[aip.uuid][FIELD_FORMATS][format_key][FIELD_COUNT] = count + 1

    report[FIELD_FORMATS] = formats
    report[FIELD_STORAGE_NAME] = storage_service.name
    return report


def derivative_overview(storage_service_id):
    """Return a summary of derivatives across AIPs with a mapping
    created between the original format and the preservation copy.
    """
    report = {}
    storage_service = _get_storage_service(storage_service_id)
    aips = AIP.query.filter_by(storage_service_id=storage_service.id).all()
    all_aips = []
    for aip in aips:
        if not aip.preservation_file_count > 0:
            continue

        aip_report = {}
        aip_report[FIELD_TRANSFER_NAME] = aip.transfer_name
        aip_report[FIELD_UUID] = aip.uuid
        aip_report[FIELD_FILE_COUNT] = aip.original_file_count
        aip_report[FIELD_DERIVATIVE_COUNT] = aip.preservation_file_count
        aip_report[FIELD_RELATED_PAIRING] = []

        original_files = File.query.filter_by(
            aip_id=aip.id, file_type=FileType.original
        )
        for original_file in original_files:
            preservation_derivative = File.query.filter_by(
                file_type=FileType.preservation, original_file_id=original_file.id
            ).first()

            if preservation_derivative is None:
                continue

            file_derivative_pair = {}
            file_derivative_pair[FIELD_DERIVATIVE_UUID] = preservation_derivative.uuid
            file_derivative_pair[FIELD_ORIGINAL_UUID] = original_file.uuid
            original_format_version = original_file.format_version
            if original_format_version is None:
                original_format_version = ""
            file_derivative_pair[FIELD_ORIGINAL_FORMAT] = "{} {} ({})".format(
                original_file.file_format, original_format_version, original_file.puid
            )
            file_derivative_pair[FIELD_DERIVATIVE_FORMAT] = "{}".format(
                preservation_derivative.file_format
            )
            aip_report[FIELD_RELATED_PAIRING].append(file_derivative_pair)

        all_aips.append(aip_report)

    report[FIELD_ALL_AIPS] = all_aips
    report[FIELD_STORAGE_NAME] = storage_service.name

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

    :param storage_service_id: Storage Service ID.
    :param file_type: Optional filter for type of file to return
    (acceptable values are "original" or "preservation").
    :param limit: Upper limit of number of results to return.

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Files"]: List of result files ordered desc by size
    """
    report = {}
    report[FIELD_FILES] = []
    storage_service = _get_storage_service(storage_service_id)
    report[FIELD_STORAGE_NAME] = storage_service.name

    files = _largest_files_query(storage_service_id, file_type, limit)

    for file_ in files:
        file_info = {}

        file_info["id"] = file_.id
        file_info[FIELD_UUID] = file_.uuid
        file_info[FIELD_NAME] = file_.name
        file_info[FIELD_SIZE] = int(file_.size)
        file_info[FIELD_AIP_ID] = file_.aip_id
        file_info[FIELD_FILE_TYPE] = file_.file_type.value

        try:
            file_info[FIELD_FORMAT] = file_.file_format
        except AttributeError:
            pass
        try:
            file_info[FIELD_VERSION] = file_.format_version
        except AttributeError:
            pass
        try:
            file_info[FIELD_PUID] = file_.puid
        except AttributeError:
            pass

        matching_aip = AIP.query.get(file_.aip_id)
        if matching_aip is not None:
            file_info[FIELD_AIP_NAME] = matching_aip.transfer_name
            file_info[FIELD_AIP_UUID] = matching_aip.uuid

        report[FIELD_FILES].append(file_info)

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
    describes original (default) or preservation files (bool)
    :param file_format: Flag indicating whether to filter on file
    format (default) or PUID (bool)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["AIPs"]: List of result AIPs ordered desc by count
    """
    report = {}

    storage_service = _get_storage_service(storage_service_id)
    report[FIELD_STORAGE_NAME] = storage_service.name

    if file_format:
        report[FIELD_FORMAT] = search_string
    else:
        report[FIELD_PUID] = search_string

    report[FIELD_AIPS] = []
    results = _query_aips_by_file_format_or_puid(
        storage_service_id, search_string, original_files, file_format
    )
    for result in results:
        aip_info = {}

        aip_info["id"] = result.id
        aip_info[FIELD_AIP_NAME] = result.name
        aip_info[FIELD_UUID] = result.uuid
        aip_info[FIELD_COUNT] = result.file_count
        aip_info[FIELD_SIZE] = result.total_size

        report[FIELD_AIPS].append(aip_info)

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
        report[FIELD_STORAGE_NAME] = storage_service.name
    except AttributeError:
        # No storage service has been returned and so we have nothing
        # to return.
        report[FIELD_STORAGE_NAME] = None
        report[FIELD_INGESTS] = ingests
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
        log_line = {}
        log_line[FIELD_AIP_UUID] = aip.uuid
        log_line[FIELD_AIP_NAME] = aip.transfer_name
        log_line[FIELD_INGEST_START_DATE] = str(event.date)
        log_line[FIELD_INGEST_FINISH_DATE] = str(aip.create_date)
        for agent in event.event_agents:
            if agent.agent_type == AGENT_TYPE:
                log_line[FIELD_USER] = _get_username(agent.agent_value)
        ingests.append(log_line)
    report[FIELD_INGESTS] = ingests
    return report
