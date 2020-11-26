# -*- coding: utf-8 -*-

"""Data endpoints optimized for providing general overviews of AIPs."""

from AIPscan.Data import _get_storage_service, fields
from AIPscan.helpers import _simplify_datetime
from AIPscan.models import AIP, File, FileType


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
                report[format_key][fields.FIELD_COUNT] = (
                    report[format_key][fields.FIELD_COUNT] + 1
                )
                if aip.uuid not in report[format_key][fields.FIELD_AIPS]:
                    report[format_key][fields.FIELD_AIPS].append(aip.uuid)
            else:
                report[format_key] = {}
                report[format_key][fields.FIELD_COUNT] = 1
                try:
                    report[format_key][fields.FIELD_VERSION] = file_.format_version
                    report[format_key][fields.FIELD_NAME] = file_.file_format
                except AttributeError:
                    pass
                if report[format_key].get(fields.FIELD_AIPS) is None:
                    report[format_key][fields.FIELD_AIPS] = []
                report[format_key][fields.FIELD_AIPS].append(aip.uuid)
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
        report[aip.uuid][fields.FIELD_AIP_NAME] = aip.transfer_name
        report[aip.uuid][fields.FIELD_CREATED_DATE] = _simplify_datetime(
            aip.create_date, False
        )
        report[aip.uuid][fields.FIELD_AIP_SIZE] = 0
        report[aip.uuid][fields.FIELD_FORMATS] = {}
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
            size = report[aip.uuid][fields.FIELD_AIP_SIZE]
            try:
                report[aip.uuid][fields.FIELD_AIP_SIZE] = size + file_.size
            # TODO: Find out why size is sometimes None.
            except TypeError:
                report[aip.uuid][fields.FIELD_AIP_SIZE] = size
                pass
            if format_key not in report[aip.uuid][fields.FIELD_FORMATS]:
                report[aip.uuid][fields.FIELD_FORMATS][format_key] = {}
                report[aip.uuid][fields.FIELD_FORMATS][format_key][
                    fields.FIELD_COUNT
                ] = 1
                try:
                    report[aip.uuid][fields.FIELD_FORMATS][format_key][
                        fields.FIELD_VERSION
                    ] = file_.format_version
                    report[aip.uuid][fields.FIELD_FORMATS][format_key][
                        fields.FIELD_NAME
                    ] = file_.file_format
                except AttributeError:
                    pass
            else:
                count = report[aip.uuid][fields.FIELD_FORMATS][format_key][
                    fields.FIELD_COUNT
                ]
                report[aip.uuid][fields.FIELD_FORMATS][format_key][
                    fields.FIELD_COUNT
                ] = (count + 1)

    report[fields.FIELD_FORMATS] = formats
    report[fields.FIELD_STORAGE_NAME] = storage_service.name
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
            file_derivative_pair[
                fields.FIELD_DERIVATIVE_UUID
            ] = preservation_derivative.uuid
            file_derivative_pair[fields.FIELD_ORIGINAL_UUID] = original_file.uuid
            original_format_version = original_file.format_version
            if original_format_version is None:
                original_format_version = ""
            file_derivative_pair[fields.FIELD_ORIGINAL_FORMAT] = "{} {} ({})".format(
                original_file.file_format, original_format_version, original_file.puid
            )
            file_derivative_pair[fields.FIELD_DERIVATIVE_FORMAT] = "{}".format(
                preservation_derivative.file_format
            )
            aip_report[fields.FIELD_RELATED_PAIRING].append(file_derivative_pair)

        all_aips.append(aip_report)

    report[fields.FIELD_ALL_AIPS] = all_aips
    report[fields.FIELD_STORAGE_NAME] = storage_service.name

    return report
