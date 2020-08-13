# -*- coding: utf-8 -*-

"""Data namespace

Return 'unkempt' data from AIPscan so that it can be filtered, cut, and
remixed as the caller desires. Data is 'unkempt' not raw. No data is
raw. No data is without bias.
"""
from distutils.util import strtobool

from flask import request
from flask_restx import Namespace, Resource
from AIPscan.Data import data

api = Namespace("data", description="Retrieve data from AIPscan to shape as you desire")

"""
data = api.model('Data', {
    'id': fields.String(required=True, description='Do we need this? An identifier for the data...'),
    'name': fields.String(required=True, description='Do we need this? A name for the datas...'),
})
"""


def parse_bool(val, default=True):
    try:
        return bool(strtobool(val))
    except (ValueError, AttributeError):
        return default


@api.route("/aip-overview/<storage_service_id>")
class FMTList(Resource):
    @api.doc(
        "list_formats",
        params={
            "original_files": {
                "description": "Return data for original files or copies",
                "in": "query",
                "type": "bool",
            }
        },
    )
    def get(self, storage_service_id):
        """AIP overview One"""
        try:
            original_files = parse_bool(request.args.get("original_files"), True)
        except TypeError:
            pass
        aip_data = data.aip_overview(
            storage_service_id=storage_service_id, original_files=original_files
        )
        return aip_data


@api.route("/fmt-overview/<storage_service_id>")
class AIPList(Resource):
    @api.doc(
        "list_formats",
        params={
            "original_files": {
                "description": "Return data for original files or copies",
                "in": "query",
                "type": "bool",
            }
        },
    )
    def get(self, storage_service_id):
        """AIP overview two"""
        try:
            original_files = parse_bool(request.args.get("original_files"), True)
        except TypeError:
            pass
        aip_data = data.aip_overview_two(
            storage_service_id=storage_service_id, original_files=original_files
        )
        return aip_data
