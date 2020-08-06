# -*- coding: utf-8 -*-

"""Data namespace

Return 'unkempt' data from AIPscan so that it can be filtered, cut, and
remixed as the caller desires. Data is 'unkempt' not raw. No data is
raw. No data is without bias.
"""

from flask_restx import Namespace, Resource, fields
from AIPscan.Data import data

api = Namespace("data", description="Retrieve data from AIPscan to shape as you desire")

"""
data = api.model('Data', {
    'id': fields.String(required=True, description='Do we need this? An identifier for the data...'),
    'name': fields.String(required=True, description='Do we need this? A name for the datas...'),
})
"""


@api.route("/aip-overview/<amss_id>")
class FMTList(Resource):
    @api.doc("list_formats")
    # @api.marshal_list_with(data)
    def get(self, amss_id):
        """AIP overview One"""
        aip_data = data.aip_overview(storage_service_id=amss_id)
        return aip_data


@api.route("/fmt-overview/<amss_id>")
class AIPList(Resource):
    @api.doc("list_aips")
    # @api.marshal_list_with(data)
    def get(self, amss_id):
        """AIP overview two"""
        aip_data = data.aip_overview_two(storage_service_id=amss_id)
        return aip_data
