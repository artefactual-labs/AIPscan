"""Data endpoints optimized for providing general overviews of AIPs."""

from AIPscan.Data import fields
from AIPscan.Data import report_dict
from AIPscan.helpers import _simplify_datetime
from AIPscan.models import AIP
from AIPscan.models import File
from AIPscan.models import FileType
from AIPscan.models import StorageService


def storage_services():
    """Return a summary overview of storage services."""
    report = {}

    storage_services = []
    for storage_service in StorageService.query.all():
        storage_services.append(
            {"id": storage_service.id, "name": storage_service.name}
        )

    report["storage_services"] = storage_services
    return report


def file_format_aip_overview(
    storage_service_id, original_files=True, storage_location_id=None
):
    """Return summary overview of file formats and the AIPs they're in."""
    report = report_dict(storage_service_id, storage_location_id)
    formats = {}
    aips = AIP.query.filter_by(storage_service_id=storage_service_id)
    if storage_location_id:
        aips = aips.filter_by(storage_location_id=storage_location_id)
    aips = aips.all()
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
                formats[format_key][fields.FIELD_COUNT] = (
                    formats[format_key][fields.FIELD_COUNT] + 1
                )
                if aip.uuid not in formats[format_key][fields.FIELD_AIPS]:
                    formats[format_key][fields.FIELD_AIPS].append(aip.uuid)
            else:
                formats[format_key] = {}
                formats[format_key][fields.FIELD_COUNT] = 1
                try:
                    formats[format_key][fields.FIELD_VERSION] = file_.format_version
                    formats[format_key][fields.FIELD_NAME] = file_.file_format
                except AttributeError:
                    pass
                if formats[format_key].get(fields.FIELD_AIPS) is None:
                    formats[format_key][fields.FIELD_AIPS] = []
                formats[format_key][fields.FIELD_AIPS].append(aip.uuid)

    report[fields.FIELD_FORMATS] = formats

    return report


def aip_file_format_overview(
    storage_service_id,
    start_date,
    end_date,
    original_files=True,
    storage_location_id=None,
):
    """Return summary overview of AIPs and their file formats."""
    report = report_dict(storage_service_id, storage_location_id)
    report[fields.FIELD_AIPS] = []
    formats = {}

    aips = AIP.query.filter_by(storage_service_id=storage_service_id)
    if storage_location_id:
        aips = aips.filter_by(storage_location_id=storage_location_id)
    aips = aips.all()

    for aip in aips:
        if aip.create_date < start_date or aip.create_date >= end_date:
            continue

        aip_info = {}
        aip_info[fields.FIELD_UUID] = aip.uuid
        aip_info[fields.FIELD_AIP_NAME] = aip.transfer_name
        aip_info[fields.FIELD_CREATED_DATE] = _simplify_datetime(aip.create_date, False)
        aip_info[fields.FIELD_SIZE] = 0
        aip_info[fields.FIELD_FORMATS] = {}

        files = None
        format_key = None

        files = File.query.filter_by(aip_id=aip.id, file_type=FileType.original)
        if not original_files:
            files = File.query.filter_by(aip_id=aip.id, file_type=FileType.preservation)

        for file_ in files:
            try:
                format_key = file_.puid
            except AttributeError:
                format_key = file_.file_format
            if format_key is None:
                continue

            formats[format_key] = file_.file_format
            if file_.format_version:
                formats[format_key] = f"{file_.file_format} {file_.format_version}"

            size = aip_info[fields.FIELD_SIZE]
            try:
                aip_info[fields.FIELD_SIZE] = size + file_.size
            # TODO: Find out why size is sometimes None.
            except (AttributeError, TypeError):
                pass

            if format_key not in aip_info[fields.FIELD_FORMATS]:
                aip_info[fields.FIELD_FORMATS][format_key] = {}
                aip_info[fields.FIELD_FORMATS][format_key][fields.FIELD_COUNT] = 1
                try:
                    aip_info[fields.FIELD_FORMATS][format_key][fields.FIELD_VERSION] = (
                        file_.format_version
                    )
                    aip_info[fields.FIELD_FORMATS][format_key][fields.FIELD_NAME] = (
                        file_.file_format
                    )
                except AttributeError:
                    pass
            else:
                count = aip_info[fields.FIELD_FORMATS][format_key][fields.FIELD_COUNT]
                aip_info[fields.FIELD_FORMATS][format_key][fields.FIELD_COUNT] = (
                    count + 1
                )
        report[fields.FIELD_AIPS].append(aip_info)

    report[fields.FIELD_FORMATS] = formats

    return report


def derivative_overview(storage_service_id, storage_location_id=None):
    """Return a summary of derivatives across AIPs with a mapping
    created between the original format and the preservation copy.
    """
    report = report_dict(storage_service_id, storage_location_id)

    aips = AIP.query.filter_by(storage_service_id=storage_service_id)
    if storage_location_id:
        aips = aips.filter_by(storage_location_id=storage_location_id)
    aips = aips.all()
    all_aips = []
    for aip in aips:
        if not aip.preservation_file_count > 0:
            continue

        aip_report = {}
        aip_report[fields.FIELD_TRANSFER_NAME] = aip.transfer_name
        aip_report[fields.FIELD_UUID] = aip.uuid
        aip_report[fields.FIELD_FILE_COUNT] = aip.original_file_count
        aip_report[fields.FIELD_DERIVATIVE_COUNT] = aip.preservation_file_count
        aip_report[fields.FIELD_RELATED_PAIRING] = []

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
            file_derivative_pair[fields.FIELD_DERIVATIVE_UUID] = (
                preservation_derivative.uuid
            )
            file_derivative_pair[fields.FIELD_ORIGINAL_UUID] = original_file.uuid
            original_format_version = original_file.format_version
            if original_format_version is None:
                original_format_version = ""
            file_derivative_pair[fields.FIELD_ORIGINAL_FORMAT] = (
                f"{original_file.file_format} {original_format_version} ({original_file.puid})"
            )
            file_derivative_pair[fields.FIELD_DERIVATIVE_FORMAT] = (
                f"{preservation_derivative.file_format}"
            )
            aip_report[fields.FIELD_RELATED_PAIRING].append(file_derivative_pair)

        all_aips.append(aip_report)

    report[fields.FIELD_ALL_AIPS] = all_aips

    return report
