# -*- coding: utf-8 -*-

from datetime import datetime

from AIPscan.models import (
    aips as aip_model,
    originals,
    events,
    agents,
    event_agents,
    copies,
    fetch_jobs,
    storage_services,
)


def _get_storage_service(storage_service_id):
    DEFAULT_STORAGE_SERVICE_ID = 1
    if storage_service_id == 0 or storage_service_id is None:
        storage_service_id = DEFAULT_STORAGE_SERVICE_ID
    storage_service = storage_services.query.get(storage_service_id)
    return storage_services.query.first() if not storage_service else storage_service


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
    aips = aip_model.query.filter_by(storage_service_id=storage_service.id).all()
    for aip in aips:
        files = None
        if original_files is True:
            files = originals.query.filter_by(aip_id=aip.id)
        else:
            files = copies.query.filter_by(aip_id=aip.id)
        for file_ in files:
            # Originals have PUIDs but Preservation Masters don't.
            # Return a key (PUID or Format Name) for our report based on that.
            try:
                format_key = file_.puid
            except AttributeError:
                format_key = file_.format
            if format_key in report:
                report[format_key]["Count"] = report[format_key]["Count"] + 1
                if aip.uuid not in report[format_key]["AIPs"]:
                    report[format_key]["AIPs"].append(aip.uuid)
            else:
                report[format_key] = {}
                report[format_key]["Count"] = 1
                try:
                    report[format_key]["Version"] = file_.format_version
                    report[format_key]["Name"] = file_.format
                except AttributeError:
                    pass
                if report[format_key].get("AIPs") is None:
                    report[format_key]["AIPs"] = []
                report[format_key]["AIPs"].append(aip.uuid)
    return report


def aip_overview_two(storage_service_id, original_files=True):
    """Return a summary overview of all AIPs in a given storage service
    """
    report = {}
    formats = {}
    storage_service = _get_storage_service(storage_service_id)
    aips = aip_model.query.filter_by(storage_service_id=storage_service.id).all()
    for aip in aips:
        report[aip.uuid] = {}
        report[aip.uuid]["AipName"] = aip.transfer_name
        report[aip.uuid]["CreatedDate"] = _format_date(aip.create_date)
        report[aip.uuid]["AipSize"] = 0
        report[aip.uuid]["Formats"] = {}
        files = None
        format_key = None
        if original_files is True:
            files = originals.query.filter_by(aip_id=aip.id)
        else:
            files = copies.query.filter_by(aip_id=aip.id)
        for file_ in files:
            try:
                format_key = file_.puid
            except AttributeError:
                format_key = file_.format
            if format_key is None:
                continue
            try:
                formats[format_key] = "{} {}".format(file_.format, file_.format_version)
            except AttributeError:
                formats[format_key] = "{}".format(file_.format)
            size = report[aip.uuid]["AipSize"]
            try:
                report[aip.uuid]["AipSize"] = size + file_.size
            # TODO: Find out why size is sometimes None.
            except TypeError:
                report[aip.uuid]["AipSize"] = size
                pass
            if format_key not in report[aip.uuid]["Formats"]:
                report[aip.uuid]["Formats"][format_key] = {}
                report[aip.uuid]["Formats"][format_key]["Count"] = 1
                try:
                    report[aip.uuid]["Formats"][format_key][
                        "Version"
                    ] = file_.format_version
                    report[aip.uuid]["Formats"][format_key]["Name"] = file_.format
                except AttributeError:
                    pass
            else:
                count = report[aip.uuid]["Formats"][format_key]["Count"]
                report[aip.uuid]["Formats"][format_key]["Count"] = count + 1

    report["Formats"] = formats
    report["StorageName"] = storage_service.name
    return report


# PICTURAE TODO: We should be able to do this in the SQLAlchemy filter
# but I can't quite get it to work yet.
def _has_derivatives(files):
    for file_ in files:
        if file_.related_uuid is not None:
            return True
    return False


def derivative_overview(storage_service_id):
    """Return a summary of derivatives across AIPs with a mapping
    created between the original format and the preservation copy.
    """
    report = {}
    storage_service = _get_storage_service(storage_service_id)
    aips = aip_model.query.filter_by(storage_service_id=storage_service.id).all()
    all_aips = []
    for aip in aips:
        files = originals.query.filter_by(aip_id=aip.id)
        if not _has_derivatives(files):
            continue
        aip_report = {}
        aip_report["TransferName"] = aip.transfer_name
        # Alias our dictionary for ease of use.
        aip_report["FileCount"] = files.count()
        aip_report["DerivativeCount"] = 0
        derivative_pairings = []
        for file_ in files:
            file_derivative_pair = {}
            derivative_uuid = file_.related_uuid
            if derivative_uuid is not None:
                derivative = copies.query.filter_by(related_uuid=file_.uuid).first()
                aip_report["DerivativeCount"] += 1
                file_derivative_pair["DerivativeUUID"] = derivative_uuid
                file_derivative_pair["OriginalUUID"] = file_.uuid
                format_version = file_.format_version
                if format_version is None:
                    format_version = ""
                file_derivative_pair["OriginalFormat"] = "{} {} ({})".format(
                    file_.format, format_version, file_.puid
                )
                file_derivative_pair["DerivativeFormat"] = "{}".format(
                    derivative.format
                )
                derivative_pairings.append(file_derivative_pair)
        aip_report["RelatedPairing"] = derivative_pairings
        all_aips.append(aip_report)
    report["AllAips"] = all_aips
    report["StorageName"] = storage_service.name
    return report
