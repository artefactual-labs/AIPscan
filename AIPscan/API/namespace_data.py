# -*- coding: utf-8 -*-

"""Data namespace

Return 'unkempt' data from AIPscan so that it can be filtered, cut, and
remixed as the caller desires. Data is 'unkempt' not raw. No data is
raw. No data is without bias.
"""

from flask import request
from flask_restx import Namespace, Resource

from AIPscan.helpers import parse_bool
from AIPscan.API import fields
from AIPscan.Data import data

api = Namespace("data", description="Retrieve data from AIPscan to shape as you desire")

"""
data = api.model('Data', {
    'id': fields.String(required=True, description='Do we need this? An identifier for the data...'),
    'name': fields.String(required=True, description='Do we need this? A name for the datas...'),
})
"""


@api.route("/aip-overview/<storage_service_id>")
class FMTList(Resource):
    @api.doc(
        "list_formats",
        params={
            fields.FIELD_ORIGINAL_FILES: {
                "description": "Return data for original files or copies",
                "in": "query",
                "type": "bool",
            }
        },
    )
    def get(self, storage_service_id):
        """List PUIDs and AIPs containing examples of them"""
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        aip_data = data.aip_overview(
            storage_service_id=storage_service_id, original_files=original_files
        )
        return aip_data


@api.route("/fmt-overview/<storage_service_id>")
class AIPList(Resource):
    @api.doc(
        "list_formats",
        params={
            fields.FIELD_ORIGINAL_FILES: {
                "description": "Return data for original files or preservation derivatives",
                "in": "query",
                "type": "bool",
            }
        },
    )
    def get(self, storage_service_id):
        """List AIPs and a summary of the file formats they contain"""
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        aip_data = data.aip_overview_two(
            storage_service_id=storage_service_id, original_files=original_files
        )
        return aip_data


@api.route("/derivative-overview/<storage_service_id>")
class DerivativeList(Resource):
    @api.doc("list_aips")
    def get(self, storage_service_id):
        """List original and derivative identifiers per AIP"""
        aip_data = data.derivative_overview(storage_service_id=storage_service_id)
        return aip_data
