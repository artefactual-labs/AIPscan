# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint

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
            if file_.puid in report:
                report[file_.puid]["Count"] = report[file_.puid]["Count"] + 1
                if aip.uuid not in report[file_.puid]["AIPs"]:
                    report[file_.puid]["AIPs"].append(aip.uuid)
            else:
                report[file_.puid] = {}
                report[file_.puid]["Count"] = 1
                report[file_.puid]["Name"] = file_.format
                report[file_.puid]["Version"] = file_.format_version
                if report[file_.puid].get("AIPs") is None:
                    report[file_.puid]["AIPs"] = []
                report[file_.puid]["AIPs"].append(aip.uuid)

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
        if original_files is True:
            files = originals.query.filter_by(aip_id=aip.id)
        else:
            files = copies.query.filter_by(aip_id=aip.id)
        for file_ in files:
            if file_.puid is None:
                continue
            formats[file_.puid] = "{} {}".format(file_.format, file_.format_version)
            size = report[aip.uuid]["AipSize"]
            try:
                report[aip.uuid]["AipSize"] = size + file_.size
            # TODO: Find out why size is sometimes None.
            except TypeError:
                report[aip.uuid]["AipSize"] = size
                pass
            if file_.puid not in report[aip.uuid]["Formats"]:
                report[aip.uuid]["Formats"][file_.puid] = {}
                report[aip.uuid]["Formats"][file_.puid]["Count"] = 1
                report[aip.uuid]["Formats"][file_.puid]["Name"] = file_.format
                report[aip.uuid]["Formats"][file_.puid][
                    "Version"
                ] = file_.format_version
            else:
                count = report[aip.uuid]["Formats"][file_.puid]["Count"]
                report[aip.uuid]["Formats"][file_.puid]["Count"] = count + 1

    report["Formats"] = formats
    report["StorageName"] = storage_service.name
    return report
