"""Infos namespace

At the moment, this is just a demonstration endpoint to show how
a namespace can be created and used. We only use it to return version
from the application itself.
"""

from flask_restx import Namespace
from flask_restx import Resource
from flask_restx import fields

import AIPscan

api = Namespace(
    "infos", description="Additional metadata associated with the application"
)

version = api.model(
    "Version",
    {
        "version": fields.String(
            required=True, description="The current version of AIPscan"
        )
    },
)

APPVERSION = {"version": AIPscan.__version__}


@api.route("/version")
class Version(Resource):
    @api.doc("aipscan_version")
    @api.marshal_list_with(version)
    def get(self):
        """Get the application version"""
        return APPVERSION
