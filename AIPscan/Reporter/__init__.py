# -*- coding: utf-8 -*-

"""Initialize components which need to be shared across the report
module, notably too the Blueprint itself.
"""

from flask import Blueprint

from AIPscan.Reporter.helpers import (  # noqa: F401
    download_csv,
    format_size_for_csv,
    get_display_end_date,
    sort_puids,
    translate_headers,
)

reporter = Blueprint("reporter", __name__, template_folder="templates")
