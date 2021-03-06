# -*- coding: utf-8 -*-

from datetime import timedelta

from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_datetime_bound
from AIPscan.Reporter import reporter, request_params, translate_headers


@reporter.route("/report_format_versions_count/", methods=["GET"])
def report_format_versions_count():
    """Return overview of format versions in Storage Service."""
    storage_service_id = request.args.get(request_params["storage_service_id"])
    start_date = parse_datetime_bound(request.args.get(request_params["start_date"]))
    end_date = parse_datetime_bound(
        request.args.get(request_params["end_date"]), upper=True
    )

    version_data = report_data.format_versions_count(
        storage_service_id=storage_service_id, start_date=start_date, end_date=end_date
    )
    versions = version_data.get(fields.FIELD_FORMAT_VERSIONS)

    headers = [
        fields.FIELD_PUID,
        fields.FIELD_FORMAT,
        fields.FIELD_VERSION,
        fields.FIELD_COUNT,
        fields.FIELD_SIZE,
    ]

    # Remove day added to end date for purposes of comparison by
    # parse_datetime_bound before passing to template.
    display_end_date = end_date - timedelta(days=1)

    return render_template(
        "report_format_versions_count.html",
        storage_service_id=storage_service_id,
        storage_service_name=version_data.get(fields.FIELD_STORAGE_NAME),
        columns=translate_headers(headers),
        versions=versions,
        total_file_count=sum(
            version.get(fields.FIELD_COUNT, 0) for version in versions
        ),
        total_size=sum(version.get(fields.FIELD_SIZE, 0) for version in versions),
        puid_count=len(versions),
        start_date=start_date,
        end_date=display_end_date,
    )
