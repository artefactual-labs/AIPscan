# -*- coding: utf-8 -*-

"""Initialize components which need to be shared across the report
module, notably too the Blueprint itself.
"""

from flask import Blueprint

from AIPscan.Reporter.helpers import translate_headers  # noqa: F401


reporter = Blueprint("reporter", __name__, template_folder="templates")
