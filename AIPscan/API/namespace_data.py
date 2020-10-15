# -*- coding: utf-8 -*-

"""Data namespace

Return 'unkempt' data from AIPscan so that it can be filtered, cut, and
remixed as the caller desires. Data is 'unkempt' not raw. No data is
raw. No data is without bias.
"""

from flask import request
from flask_restx import Namespace, Resource

from AIPscan.helpers import parse_bool
from AIPscan.Data import data

FILE_FORMAT_FIELD = "file_format"
FILE_TYPE_FIELD = "file_type"
LIMIT_FIELD = "limit"
ORIGINAL_FILES_FIELD = "original_files"
PUID_FIELD = "puid"

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
            ORIGINAL_FILES_FIELD: {
                "description": "Return data for original files or copies",
                "in": "query",
                "type": "bool",
            }
        },
    )
    def get(self, storage_service_id):
        """AIP overview One"""
        original_files = parse_bool(request.args.get(ORIGINAL_FILES_FIELD, True))
        aip_data = data.aip_overview(
            storage_service_id=storage_service_id, original_files=original_files
        )
        return aip_data


@api.route("/fmt-overview/<storage_service_id>")
class AIPList(Resource):
    @api.doc(
        "list_formats",
        params={
            ORIGINAL_FILES_FIELD: {
                "description": "Return data for original files or preservation derivatives",
                "in": "query",
                "type": "bool",
            }
        },
    )
    def get(self, storage_service_id):
        """AIP overview two"""
        original_files = parse_bool(request.args.get(ORIGINAL_FILES_FIELD, True))
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
            FILE_TYPE_FIELD: {
                "description": "Optional file type filter (original or preservation)",
                "in": "query",
                "type": "str",
            },
            LIMIT_FIELD: {
                "description": "Number of results to return (default is 20)",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id, file_type=None, limit=20):
        """Largest files"""
        file_type = request.args.get(FILE_TYPE_FIELD)
        try:
            limit = int(request.args.get("limit", 20))
        except ValueError:
            pass
        file_data = data.largest_files(
            storage_service_id=storage_service_id, file_type=file_type, limit=limit
        )
        return file_data


@api.route("/aips-by-file-format/<storage_service_id>")
class AIPsByFormatList(Resource):
    @api.doc(
        "list_aips_by_format",
        params={
            FILE_FORMAT_FIELD: {
                "description": "File format name (must be exact match)",
                "in": "query",
                "type": "str",
            },
            ORIGINAL_FILES_FIELD: {
                "description": "Return data for original files or preservation derivatives",
                "in": "query",
                "type": "bool",
            },
        },
    )
    def get(self, storage_service_id):
        """AIPs containing given file format."""
        file_format = request.args.get(FILE_FORMAT_FIELD, "")
        original_files = parse_bool(request.args.get(ORIGINAL_FILES_FIELD, True))
        aip_data = data.aips_by_file_format(
            storage_service_id=storage_service_id,
            file_format=file_format,
            original_files=original_files,
        )
        return aip_data


@api.route("/aips-by-puid/<storage_service_id>")
class AIPsByPUIDList(Resource):
    @api.doc(
        "list_aips_by_puid",
        params={
            PUID_FIELD: {
                "description": "PRONOM ID (PUID)",
                "in": "query",
                "type": "str",
            },
            ORIGINAL_FILES_FIELD: {
                "description": "Return data for original files or preservation derivatives",
                "in": "query",
                "type": "bool",
            },
        },
    )
    def get(self, storage_service_id):
        """AIPs containing given format version, specified by PUID."""
        puid = request.args.get(PUID_FIELD, "")
        original_files = parse_bool(request.args.get(ORIGINAL_FILES_FIELD, True))
        aip_data = data.aips_by_puid(
            storage_service_id=storage_service_id,
            puid=puid,
            original_files=original_files,
        )
        return aip_data
