# -*- coding: utf-8 -*-

"""AIPscan API entry point

Provides metadata to the swagger endpoint as well as importing the
different namespace modules required to provide all the functionality
we'd like from AIPscan.

HOWTO extend: Proposal is to evolve the API. So avoid versioning, and
instead, add fields to endpoints. Add endpoints. And when absolutely
necessary, following good communication with stakeholders, sunset, and
deprecate endpoints.
"""

from flask import Blueprint
from flask_restx import Api

from .namespace_data import api as ns1
from .namespace_infos import api as ns3
from .namespace_report_data import api as ns2

api_doc = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt
in culpa qui officia deserunt mollit anim id est laborum.
"""

api = Blueprint("api", __name__, url_prefix="/api")
report_api = Api(
    api,
    title="AIPscan API endpoint - you know, for data!",
    version="0.1",
    description=api_doc,
    license="Apache License 2.0",
    license_url="https://github.com/artefactual-labs/AIPscan/blob/60afe37bfd0106735b47635606a0658a90ba9946/LICENSE",
    default_mediatype="application/json",
)

report_api.add_namespace(ns1)
report_api.add_namespace(ns2)
report_api.add_namespace(ns3)
