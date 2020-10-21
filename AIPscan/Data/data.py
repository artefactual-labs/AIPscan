# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from AIPscan import db
from AIPscan.models import AIP, File, FileType, StorageService


FIELD_AIP = "AIP"
FIELD_AIP_ID = "AIPID"
FIELD_AIP_NAME = "AIPName"
FIELD_AIP_NAME_WITH_UUID = "AIPNameWithUUID"
FIELD_AIP_SIZE = "AIPSize"
FIELD_AIP_UUID = "AIPUUID"
FIELD_AIPS = "AIPs"
FIELD_ALL_AIPS = "AllAIPs"

FIELD_COUNT = "Count"
FIELD_CREATED_DATE = "CreatedDate"

FIELD_DERIVATIVE_COUNT = "DerivativeCount"
FIELD_DERIVATIVE_FORMAT = "DerivativeFormat"
FIELD_DERIVATIVE_UUID = "DerivativeUUID"

FIELD_FILES = "Files"
FIELD_FILE_COUNT = "FileCount"
FIELD_FILE_TYPE = "FileType"
FIELD_FILENAME = "Filename"
FIELD_FORMAT = "Format"
FIELD_FORMATS = "Formats"

FIELD_NAME = "Name"

FIELD_ORIGINAL_UUID = "OriginalUUID"
FIELD_ORIGINAL_FORMAT = "OriginalFormat"

FIELD_PUID = "PUID"

FIELD_RELATED_PAIRING = "RelatedPairing"

FIELD_SIZE = "Size"
FIELD_STORAGE_NAME = "StorageName"

FIELD_TRANSFER_NAME = "TransferName"

FIELD_UUID = "UUID"

FIELD_VERSION = "Version"


def _get_storage_service(storage_service_id):
    DEFAULT_STORAGE_SERVICE_ID = 1
    if storage_service_id == 0 or storage_service_id is None:
        storage_service_id = DEFAULT_STORAGE_SERVICE_ID
    storage_service = StorageService.query.get(storage_service_id)
    return StorageService.query.first() if not storage_service else storage_service


def _split_ms(date_string):
    """Remove microseconds from the given date string."""
    return str(date_string).split(".")[0]


def _format_date(date_string):
    """Format date to something nicer that can played back in reports"""
    DATE_FORMAT_FULL = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT_PARTIAL = "%Y-%m-%d"
    formatted_date = datetime.strptime(_split_ms(date_string), DATE_FORMAT_FULL)
    return formatted_date.strftime(DATE_FORMAT_PARTIAL)


def aip_overview(storage_service_id, original_files=True):
    """Return a summary overview of all AIPs in a given storage service
    """
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
    """Return a summary overview of all AIPs in a given storage service
    """
    report = {}
    formats = {}
    storage_service = _get_storage_service(storage_service_id)
    aips = AIP.query.filter_by(storage_service_id=storage_service.id).all()
    for aip in aips:
        report[aip.uuid] = {}
        report[aip.uuid][FIELD_AIP_NAME] = aip.transfer_name
        report[aip.uuid][FIELD_CREATED_DATE] = _format_date(aip.create_date)
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
    VALID_FILE_TYPES = set(item.value for item in FileType)
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


def prepare_datetimes_for_query(start_date, end_date):
    """Prepare start_date and end_date parameters for use in queries."""
    if start_date is None:
        start_date = datetime.min

    if end_date is None:
        end_date = datetime.max
    else:
        # Since our date parameters will come in as dates but AIP
        # timestamps are more granular, add one day to end_date and
        # compare using less than (not less than or equal to) in the
        # query to ensure date is inclusive.
        end_date = end_date + timedelta(days=1)

    return start_date, end_date


def _aips_by_format_query(storage_service_id, file_format):
    """Fetch information on all AIPs with given format from database

    This is separated into its own helper function to aid in testing.

    :param storage_service_id: Storage Service ID (int)
    :param file_format: File format (str)

    :returns: SQLAlchemy query results
    """
    aips = (
        db.session.query(
            AIP.id.label("id"),
            AIP.transfer_name.label("name"),
            AIP.uuid.label("uuid"),
            db.func.count(File.id).label("file_count"),
            db.func.sum(File.size).label("total_size"),
        )
        .join(File)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_format == file_format)
        .group_by(AIP.id)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )
    return aips


def aips_by_file_format(
    storage_service_id, file_format, start_date=None, end_date=None
):
    """Return overview of all AIPs containing original files in format

    :param storage_service_id: Storage Service ID (int)
    :param file_format: File format name (str)
    :start_date: Optional inclusive start date (datetime object)
    :end_date: Optional inclusive end date (datetime object)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["AIPs"]: List of result AIPs ordered desc by count
    """
    start_date, end_date = prepare_datetimes_for_query(start_date, end_date)

    report = {}
    storage_service = _get_storage_service(storage_service_id)
    report[FIELD_STORAGE_NAME] = storage_service.name
    report[FIELD_FORMAT] = file_format
    report[FIELD_AIPS] = []

    results = _aips_by_format_query(storage_service_id, file_format)

    for result in results:
        aip_info = {}

        aip_info["id"] = result.id
        aip_info[FIELD_AIP_NAME_WITH_UUID] = "{}-{}".format(result.name, result.uuid)
        aip_info[FIELD_AIP_NAME] = result.name
        aip_info[FIELD_UUID] = result.uuid
        aip_info[FIELD_COUNT] = result.file_count
        aip_info[FIELD_SIZE] = result.total_size

        report[FIELD_AIPS].append(aip_info)

    return report


def _aips_by_puid_query(storage_service_id, puid, start_date=None, end_date=None):
    """Fetch information on all AIPs with given PUID from database

    This is separated into its own helper function to aid in testing.

    :param storage_service_id: Storage Service ID (int)
    :param puid: PRONOM ID (str)
    :start_date: Optional inclusive start date (datetime object)
    :end_date: Optional inclusive end date (datetime object)

    :returns: SQLAlchemy query results
    """
    start_date, end_date = prepare_datetimes_for_query(start_date, end_date)

    aips = (
        db.session.query(
            AIP.id.label("id"),
            AIP.transfer_name.label("name"),
            AIP.uuid.label("uuid"),
            db.func.count(File.id).label("file_count"),
            db.func.sum(File.size).label("total_size"),
        )
        .join(File)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.puid == puid)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .group_by(AIP.id)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )

    return aips


def aips_by_puid(storage_service_id, puid, start_date=None, end_date=None):
    """Return overview of all AIPs containing original files with PUID

    :param storage_service_id: Storage Service ID.
    :param puid: PRONOM ID used to specify file format.
    :start_date: Optional inclusive start date (datetime object)
    :end_date: Optional inclusive end date (datetime object)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["AIPs"]: List of result AIPs ordered desc by count
    """
    report = {}
    storage_service = _get_storage_service(storage_service_id)
    report[FIELD_STORAGE_NAME] = storage_service.name
    report[FIELD_PUID] = puid
    report[FIELD_AIPS] = []

    results = _aips_by_puid_query(storage_service_id, puid, start_date, end_date)

    for result in results:
        aip_info = {}

        aip_info["id"] = result.id
        aip_info[FIELD_AIP_NAME] = result.name
        aip_info[FIELD_UUID] = result.uuid
        aip_info[FIELD_COUNT] = result.file_count
        aip_info[FIELD_SIZE] = result.total_size

        report[FIELD_AIPS].append(aip_info)

    return report
