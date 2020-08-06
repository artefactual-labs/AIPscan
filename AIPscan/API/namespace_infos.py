# -*- coding: utf-8 -*-

"""Infos namespace

At the moment, this is just a demonstration endpoint to show how
a namespace can be created and used. We only use it to return version
from the application itself.
"""

from flask_restx import Namespace, Resource, fields

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

# TODO: Get this from the application wherever we decide to put it...
APPVERSION = {"version": "0.1"}


@api.route("/version")
class Version(Resource):
    @api.doc("aipscan_version")
    @api.marshal_list_with(version)
    def get(self):
        """Get the application version"""
        return APPVERSION
