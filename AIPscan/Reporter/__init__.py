"""Initialize components which need to be shared across the report
module, notably too the Blueprint itself.
"""

from flask import Blueprint

from AIPscan.Reporter.helpers import download_csv  # noqa: F401
from AIPscan.Reporter.helpers import format_size_for_csv  # noqa: F401
from AIPscan.Reporter.helpers import get_display_end_date  # noqa: F401
from AIPscan.Reporter.helpers import sort_puids  # noqa: F401
from AIPscan.Reporter.helpers import translate_headers  # noqa: F401

reporter = Blueprint("reporter", __name__, template_folder="templates")
