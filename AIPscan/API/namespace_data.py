# -*- coding: utf-8 -*-

"""Data namespace

Return 'unkempt' data from AIPscan so that it can be filtered, cut, and
remixed as the caller desires. Data is 'unkempt' not raw. No data is
raw. No data is without bias.
"""

from flask import request
from flask_restx import Namespace, Resource

from AIPscan.API import fields
from AIPscan.Data import data
from AIPscan.helpers import parse_bool

api = Namespace("data", description="Retrieve data from AIPscan to shape as you desire")

"""
data = api.model('Data', {
    'id': fields.String(required=True, description='Do we need this? An identifier for the data...'),
    'name': fields.String(required=True, description='Do we need this? A name for the datas...'),
})
"""


@api.route("/aip-overview/<storage_service_id>")
class AIPList(Resource):
    @api.doc(
        "list_formats",
        params={
            fields.FIELD_ORIGINAL_FILES: {
                "description": "Return data on original files or preservation derivatives",
                "in": "query",
                "type": "bool",
            },
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """Return data on AIPs and the file formats they contain."""
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        return data.aip_file_format_overview(
            storage_service_id=storage_service_id,
            original_files=original_files,
            storage_location_id=storage_location_id,
        )


@api.route("/fmt-overview/<storage_service_id>")
class FMTList(Resource):
    @api.doc(
        "list_formats",
        params={
            fields.FIELD_ORIGINAL_FILES: {
                "description": "Return data on original files or preservation derivatives",
                "in": "query",
                "type": "bool",
            },
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """Return data on PUIDs and the AIPs they are contained within."""
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        return data.file_format_aip_overview(
            storage_service_id=storage_service_id,
            original_files=original_files,
            storage_location_id=storage_location_id,
        )


@api.route("/derivative-overview/<storage_service_id>")
class DerivativeList(Resource):
    @api.doc(
        "list_aips",
        params={
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            }
        },
    )
    def get(self, storage_service_id):
        """List original and derivative identifiers per AIP"""
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        return data.derivative_overview(
            storage_service_id=storage_service_id,
            storage_location_id=storage_location_id,
        )
