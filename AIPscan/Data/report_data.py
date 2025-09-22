"""Data endpoints optimized for reports in the Reporter blueprint."""

from datetime import datetime
from datetime import timedelta
from operator import itemgetter

from dateutil.rrule import DAILY
from dateutil.rrule import rrule

from AIPscan import db
from AIPscan.Data import fields
from AIPscan.Data import get_storage_service_name
from AIPscan.Data import report_dict
from AIPscan.models import AIP
from AIPscan.models import Event
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.models import StorageLocation
from AIPscan.models import StorageService

VALID_FILE_TYPES = set(item.value for item in FileType)


def _get_username(agent_string):
    """Retrieve username from the standard agent string stored in the
    database, normally formatted as:

        * username="test", first_name="", last_name=""
    """
    USERNAME = "username="
    return agent_string.split(",", 1)[0].replace(USERNAME, "").replace('"', "")


def _formats_count_query(
    storage_service_id, start_date, end_date, storage_location_id=None
):
    """Fetch information from database on file formats.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: SQLAlchemy query results
    """
    FILE_FORMAT = "file_format"
    FILE_COUNT = "file_count"
    FILE_SIZE = "total_size"

    results = (
        db.session.query(
            File.file_format.label(FILE_FORMAT),
            db.func.count(File.id).label(FILE_COUNT),
            db.func.sum(File.size).label(FILE_SIZE),
        )
        .join(AIP)
        .join(StorageLocation)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.original.value)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .group_by(File.file_format)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )
    if storage_location_id:
        results = results.filter(StorageLocation.id == storage_location_id)
    return results


def formats_count(storage_service_id, start_date, end_date, storage_location_id=None):
    """Return a summary of file formats in Storage Service.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Formats"]: List of results ordered desc by count and size
    """
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMATS] = []

    formats = _formats_count_query(
        storage_service_id, start_date, end_date, storage_location_id
    )

    for format_ in formats:
        format_info = {}

        format_info[fields.FIELD_FORMAT] = format_.file_format
        format_info[fields.FIELD_COUNT] = format_.file_count
        format_info[fields.FIELD_SIZE] = 0
        if format_.total_size is not None:
            format_info[fields.FIELD_SIZE] = format_.total_size

        report[fields.FIELD_FORMATS].append(format_info)

    return report


def _format_versions_count_query(
    storage_service_id, start_date, end_date, storage_location_id
):
    """Fetch information from database on format versions.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: SQLAlchemy query results
    """
    PUID = "puid"
    FILE_FORMAT = "file_format"
    FORMAT_VERSION = "format_version"
    FILE_COUNT = "file_count"
    FILE_SIZE = "total_size"

    results = (
        db.session.query(
            File.puid.label(PUID),
            File.file_format.label(FILE_FORMAT),
            File.format_version.label(FORMAT_VERSION),
            db.func.count(File.id).label(FILE_COUNT),
            db.func.sum(File.size).label(FILE_SIZE),
        )
        .join(AIP)
        .join(StorageLocation)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.original.value)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .group_by(File.puid)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )
    if storage_location_id:
        results = results.filter(StorageLocation.id == storage_location_id)
    return results


def format_versions_count(
    storage_service_id, start_date, end_date, storage_location_id=None
):
    """Return a summary of format versions in Storage Service.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["FormatVersions"]: List of result files ordered desc by size
    """
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FORMAT_VERSIONS] = []

    versions = _format_versions_count_query(
        storage_service_id, start_date, end_date, storage_location_id
    )

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


def _largest_files_query(
    storage_service_id, start_date, end_date, storage_location_id, file_type, limit
):
    """Fetch file information from database for largest files query

    This is separated into its own helper function to aid in testing.
    """
    files = (
        File.query.join(AIP)
        .join(StorageLocation)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .order_by(File.size.desc())
    )
    if file_type is not None and file_type in VALID_FILE_TYPES:
        files = files.filter(File.file_type == file_type)
    if storage_location_id:
        files = files.filter(StorageLocation.id == storage_location_id)
    return files.limit(limit)


def largest_files(
    storage_service_id,
    start_date,
    end_date,
    storage_location_id=None,
    file_type=None,
    limit=20,
):
    """Return a summary of the largest files in a given Storage Service

    :param storage_service_id: Storage Service ID
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)
    :param file_type: Optional filter for type of file to return
        (acceptable values are "original" or "preservation")
    :param limit: Upper limit of number of results to return

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Files"]: List of result files ordered desc by size
    """
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FILES] = []

    files = _largest_files_query(
        storage_service_id, start_date, end_date, storage_location_id, file_type, limit
    )

    for file_ in files:
        file_info = {}

        file_info[fields.FIELD_ID] = file_.id
        file_info[fields.FIELD_UUID] = file_.uuid
        file_info[fields.FIELD_NAME] = file_.name
        try:
            file_info[fields.FIELD_SIZE] = int(file_.size)
        except TypeError:
            file_info[fields.FIELD_SIZE] = 0
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

        matching_aip = db.session.get(AIP, file_.aip_id)
        if matching_aip is not None:
            file_info[fields.FIELD_AIP_NAME] = matching_aip.transfer_name
            file_info[fields.FIELD_AIP_UUID] = matching_aip.uuid

        report[fields.FIELD_FILES].append(file_info)

    return report


def _largest_aips_query(
    storage_service_id, start_date, end_date, storage_location_id, limit
):
    """Fetch information from database for largest AIPs query."""
    aips = (
        AIP.query.join(StorageLocation)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
    )
    if storage_location_id:
        aips = aips.filter(StorageLocation.id == storage_location_id)
    return aips.order_by(AIP.size.desc()).limit(limit)


def largest_aips(
    storage_service_id, start_date, end_date, storage_location_id=None, limit=20
):
    """Return a summary of the largest AIPs in a given Storage Service

    :param storage_service_id: Storage Service ID
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)
    :param limit: Upper limit of number of results to return

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["AIPs"]: List of result AIPs ordered desc by size
    """
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_AIPS] = []

    aips = _largest_aips_query(
        storage_service_id, start_date, end_date, storage_location_id, limit
    )

    for aip in aips:
        aip_info = {}

        aip_info[fields.FIELD_NAME] = aip.transfer_name
        aip_info[fields.FIELD_UUID] = aip.uuid
        aip_info[fields.FIELD_SIZE] = aip.size
        aip_info[fields.FIELD_FILE_COUNT] = aip.original_file_count

        report[fields.FIELD_AIPS].append(aip_info)

    return report


def _query_aips_by_file_format_or_puid(
    storage_service_id,
    storage_location_id,
    search_string,
    original_files=True,
    file_format=True,
):
    """Fetch information on all AIPs with given format or PUID from db.

    :param storage_service_id: Storage Service ID (int)
    :param storage_location_id: Storage Location ID (int)
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
    if storage_location_id:
        aips = aips.filter(AIP.storage_location_id == storage_location_id)

    if original_files is False:
        aips = aips.filter(File.file_type == FileType.preservation.value)
    else:
        aips = aips.filter(File.file_type == FileType.original.value)

    if file_format:
        return aips.filter(File.file_format == search_string)
    return aips.filter(File.puid == search_string)


def _aips_by_file_format_or_puid(
    storage_service_id,
    storage_location_id,
    search_string,
    original_files=True,
    file_format=True,
):
    """Return overview of all AIPs containing original files in format

    :param storage_service_id: Storage Service ID (int)
    :param storage_location_id: Storage Location ID (int)
    :param search_string: File format name or PUID (str)
    :param original_files: Flag indicating whether returned data
        data describes original (default) or preservation files (bool)
    :param file_format: Flag indicating whether to filter on file
        file format (default) or PUID (bool)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["AIPs"]: List of result AIPs ordered desc by count
    """
    report = report_dict(storage_service_id, storage_location_id)

    if file_format:
        report[fields.FIELD_FORMAT] = search_string
    else:
        report[fields.FIELD_PUID] = search_string

    report[fields.FIELD_AIPS] = []
    results = _query_aips_by_file_format_or_puid(
        storage_service_id,
        storage_location_id,
        search_string,
        original_files,
        file_format,
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


def aips_by_file_format(
    storage_service_id, file_format, original_files=True, storage_location_id=None
):
    """Return overview of AIPs containing original files in format.

    :param storage_service_id: Storage Service ID (int)
    :param file_format: File format name (str)
    :param original_files: Flag indicating whether returned data
        describes original (default) or preservation files (bool)
    :param storage_location_id: Storage Location ID (int)

    :returns: Report dict provided by _aips_by_file_format_or_puid
    """
    return _aips_by_file_format_or_puid(
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        search_string=file_format,
        original_files=original_files,
    )


def aips_by_puid(
    storage_service_id, puid, original_files=True, storage_location_id=None
):
    """Return overview of AIPs containing original files in format.

    :param storage_service_id: Storage Service ID (int)
    :param puid: PUID (str)
    :param original_files: Flag indicating whether returned data
        describes original (default) or preservation files (bool)
    :param storage_location_id: Storage Location ID (int)

    :returns: Report dict provided by _aips_by_file_format_or_puid
    """
    return _aips_by_file_format_or_puid(
        storage_service_id=storage_service_id,
        storage_location_id=storage_location_id,
        search_string=puid,
        original_files=original_files,
        file_format=False,
    )


def agents_transfers(
    storage_service_id, start_date, end_date, storage_location_id=None
):
    """Return overview of transfers and their agents.

    Includes simple statistics such as ingest start and finish times.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["StorageLocation"]: Name of storage location, if applicable
        report["Ingest"]: List of ingest event dictionaries
    """
    report = report_dict(storage_service_id, storage_location_id)

    ingests = []

    if not report[fields.FIELD_STORAGE_NAME]:
        # No storage service has been returned and so we have nothing
        # to return.
        report[fields.FIELD_INGESTS] = ingests
        return report

    aips = (
        AIP.query.filter_by(storage_service_id=storage_service_id)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
    )
    if storage_location_id:
        aips = aips.filter(AIP.storage_location_id == storage_location_id)
    aips = aips.all()

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


def _preservation_derivatives_query(storage_service_id, storage_location_id, aip_uuid):
    """Fetch information on preservation derivatives from db.

    :param storage_service_id: Storage Service ID (int)
    :param storage_location_id: Storage Location ID (int)
    :param aip_uuid: AIP UUID (str)

    :returns: SQLAlchemy query results
    """
    files = (
        File.query.join(AIP)
        .join(StorageLocation)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.preservation)
        .order_by(AIP.uuid, File.file_format)
    )
    if storage_location_id:
        files = files.filter(StorageLocation.id == storage_location_id)
    if aip_uuid:
        files = files.filter(AIP.uuid == aip_uuid)
    return files


def preservation_derivatives(
    storage_service_id, storage_location_id=None, aip_uuid=None
):
    """Return details of preservation derivatives in Storage Service.

    This includes information about each preservation derivative, as well as
    its corresponding original file and AIP.

    :param storage_service_id: Storage Service ID (int)
    :param storage_location_id: Storage Location ID (int)
    :param aip_uuid: AIP UUID (str)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Files"]: List of result files ordered desc by size
    """
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_FILES] = []

    files = _preservation_derivatives_query(
        storage_service_id, storage_location_id, aip_uuid
    )

    for file_ in files:
        file_info = {}

        file_info[fields.FIELD_AIP_UUID] = file_.aip.uuid
        file_info[fields.FIELD_AIP_NAME] = file_.aip.transfer_name

        file_info[fields.FIELD_ID] = file_.id
        file_info[fields.FIELD_UUID] = file_.uuid
        file_info[fields.FIELD_NAME] = file_.name
        file_info[fields.FIELD_FORMAT] = file_.file_format

        original_file = file_.original_file
        if original_file:
            file_info[fields.FIELD_ORIGINAL_UUID] = original_file.uuid
            file_info[fields.FIELD_ORIGINAL_NAME] = original_file.name
            file_info[fields.FIELD_ORIGINAL_FORMAT] = original_file.file_format
            file_info[fields.FIELD_ORIGINAL_VERSION] = ""
            try:
                file_info[fields.FIELD_ORIGINAL_VERSION] = original_file.format_version
            except AttributeError:
                pass
            file_info[fields.FIELD_ORIGINAL_PUID] = ""
            try:
                file_info[fields.FIELD_ORIGINAL_PUID] = original_file.puid
            except AttributeError:
                pass

        report[fields.FIELD_FILES].append(file_info)

    return report


def _get_storage_locations(storage_service_id):
    """Return queryset of locations in this Storage Service."""
    return StorageLocation.query.filter_by(storage_service_id=storage_service_id).all()


def _sort_storage_locations(unsorted_locations):
    """Sort list of location dictionaries by AIP count descending."""
    return sorted(unsorted_locations, key=itemgetter(fields.FIELD_AIPS), reverse=True)


def storage_locations(storage_service_id, start_date, end_date):
    """Return details of AIP store locations in Storage Service.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Locations"]: List of result locations ordered desc by size
    """
    report = {}
    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)

    locations = _get_storage_locations(storage_service_id)

    unsorted_results = []

    for location in locations:
        loc_info = {}

        loc_info[fields.FIELD_ID] = location.id
        loc_info[fields.FIELD_UUID] = location.uuid
        loc_info[fields.FIELD_STORAGE_LOCATION] = location.description
        loc_info[fields.FIELD_AIPS] = location.aip_count(start_date, end_date)
        loc_info[fields.FIELD_SIZE] = location.aip_total_size(start_date, end_date)
        loc_info[fields.FIELD_FILE_COUNT] = location.file_count(start_date, end_date)

        unsorted_results.append(loc_info)

    report[fields.FIELD_LOCATIONS] = _sort_storage_locations(unsorted_results)

    return report


def _get_days_covered_by_date_range(storage_service_id, start_date, end_date):
    """Return days covered by date range as list of ISO values.

    First, replace datetime.min and datetime.max, if used, with more sensible
    values so that we do not end up returning every day since the beginning
    of time.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)

    :returns: List of strings like "YYYY-MM-DD"
    """
    if start_date == datetime.min:
        storage_service = db.session.get(StorageService, storage_service_id)
        start_date = storage_service.earliest_aip_created
    if end_date >= datetime.now():
        end_date = datetime.now()

    return [
        dt.isoformat()[:10] for dt in rrule(DAILY, dtstart=start_date, until=end_date)
    ]


def storage_locations_usage_over_time(
    storage_service_id, start_date, end_date, cumulative=False
):
    """Return details of AIP store locations in Storage Service over time.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param cumulative: Flag indicating whether to calculate cumulatively, where
        each month adds to previous totals (bool)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Locations"]: List of result locations ordered desc by size
    """
    report = {}
    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)

    locations = _get_storage_locations(storage_service_id)
    days = _get_days_covered_by_date_range(storage_service_id, start_date, end_date)

    results = {}

    for day in days:
        daily_locations_data = []

        for location in locations:
            loc_info = {}

            subquery_start_date = datetime.strptime(day, "%Y-%m-%d")
            subquery_end_date = subquery_start_date + timedelta(days=1)
            if cumulative:
                subquery_start_date = datetime.strptime(days[0], "%Y-%m-%d")

            loc_info[fields.FIELD_ID] = location.id
            loc_info[fields.FIELD_UUID] = location.uuid
            loc_info[fields.FIELD_STORAGE_LOCATION] = location.description
            loc_info[fields.FIELD_AIPS] = location.aip_count(
                subquery_start_date, subquery_end_date
            )
            loc_info[fields.FIELD_SIZE] = location.aip_total_size(
                subquery_start_date, subquery_end_date
            )
            loc_info[fields.FIELD_FILE_COUNT] = location.file_count(
                subquery_start_date, subquery_end_date
            )

            daily_locations_data.append(loc_info)

        results[day] = daily_locations_data

    report[fields.FIELD_LOCATIONS_USAGE_OVER_TIME] = results

    return report
