# -*- coding: utf-8 -*-

"""Initialize components which need to be shared across the report
module, notably too the Blueprint itself.
"""

from flask import Blueprint

from AIPscan.Reporter.helpers import (  # noqa: F401
    download_csv,
    get_display_end_date,
    sort_puids,
    translate_headers,
)

reporter = Blueprint("reporter", __name__, template_folder="templates")

request_params = {
    "storage_service_id": "amss_id",
    "file_format": "file_format",
    "puid": "puid",
    "original_files": "original_files",
    "file_type": "file_type",
    "limit": "limit",
    "start_date": "start_date",
    "end_date": "end_date",
    "csv": "csv",
}
