# -*- coding: utf-8 -*-

"""Data namespace

Return 'unkempt' data from AIPscan so that it can be filtered, cut, and
remixed as the caller desires. Data is 'unkempt' not raw. No data is
raw. No data is without bias.
"""
from datetime import datetime
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


@api.route("/derivative-overview/<storage_service_id>")
class DerivativeList(Resource):
    @api.doc("list_aips")
    def get(self, storage_service_id):
        """AIP overview two"""
        aip_data = data.derivative_overview(storage_service_id=storage_service_id)
        return aip_data


@api.route("/largest-files/<storage_service_id>")
class LargestFileList(Resource):
    @api.doc(
        "list_formats",
        params={
            "file_type": {
                "description": "Optional file type filter (original or preservation)",
                "in": "query",
                "type": "str",
            },
            "limit": {
                "description": "Number of results to return (default is 20)",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id, file_type=None, limit=20):
        """Largest files"""
        file_type = request.args.get("file_type", None)
        try:
            limit = int(request.args.get("limit", 20))
        except ValueError:
            pass
        file_data = data.largest_files(
            storage_service_id=storage_service_id, file_type=file_type, limit=limit
        )
        return file_data


@api.route("/storage_service/<storage_service_id>/file-format")
class AIPsByFormatList(Resource):
    @api.doc(
        "list_aips_by_format",
        params={
            "file_format": {
                "description": "File format name (must be exact match)",
                "in": "query",
                "type": "str",
            },
            "start_date": {
                "description": "Start date (inclusive)",
                "in": "query",
                "type": "datetime",
            },
            "end_date": {
                "description": "End date (inclusive)",
                "in": "query",
                "type": "datetime",
            },
        },
    )
    def get(self, storage_service_id):
        """AIPs containing file format"""
        file_format = request.args.get("file_format")
        if not file_format:
            return {"success": "False", "error": "Must specify a file format."}

        start_date = request.args.get("start_date")
        if start_date is not None:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return {"success": "False", "error": "Invalid start_date value."}

        end_date = request.args.get("end_date")
        if end_date is not None:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return {"success": "False", "error": "Invalid end_date value."}

        aip_data = data.aips_by_file_format(
            storage_service_id=storage_service_id,
            file_format=file_format,
            start_date=start_date,
            end_date=end_date,
        )
        return aip_data


@api.route("/storage_service/<storage_service_id>/puid")
class AIPsByPUIDList(Resource):
    @api.doc(
        "list_aips_by_puid",
        params={
            "puid": {"description": "PRONOM ID (PUID)", "in": "query", "type": "str"},
            "start_date": {
                "description": "Start date (inclusive)",
                "in": "query",
                "type": "datetime",
            },
            "end_date": {
                "description": "End date (inclusive)",
                "in": "query",
                "type": "datetime",
            },
        },
    )
    def get(self, storage_service_id):
        """AIPs containing PUID"""
        puid = request.args.get("puid")
        if not puid:
            return {"success": "False", "error": "Must specify a PUID."}

        start_date = request.args.get("start_date")
        if start_date is not None:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return {"success": "False", "error": "Invalid start_date value."}

        end_date = request.args.get("end_date")
        if end_date is not None:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return {"success": "False", "error": "Invalid end_date value."}

        aip_data = data.aips_by_puid(
            storage_service_id=storage_service_id,
            puid=puid,
            start_date=start_date,
            end_date=end_date,
        )

        return aip_data
