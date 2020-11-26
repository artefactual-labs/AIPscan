# -*- coding: utf-8 -*-

"""Report data namespace

Return data optimized for reports implemented in the Reporter
blueprint for consumption by external systems.
"""

from flask import request
from flask_restx import Namespace, Resource

from AIPscan.helpers import parse_bool, parse_datetime_bound
from AIPscan.API import fields
from AIPscan.Data import report_data

api = Namespace(
    "report-data", description="Retrieve data optimized for AIPscan reports"
)


@api.route("/format-version-count/<storage_service_id>")
class FormatVersionList(Resource):
    @api.doc(
        "list_format_versions",
        params={
            fields.FIELD_START_DATE: {
                "description": "AIP creation start date (inclusive, YYYY-MM-DD)",
                "in": "query",
                "type": "str",
            },
            fields.FIELD_END_DATE: {
                "description": "AIP creation end date (inclusive, YYYY-MM-DD)",
                "in": "query",
                "type": "str",
            },
        },
    )
    def get(self, storage_service_id):
        """List file format versions with file count and size"""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )

        return report_data.format_versions_count(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
        )


@api.route("/largest-files/<storage_service_id>")
class LargestFileList(Resource):
    @api.doc(
        "list_formats",
        params={
            fields.FIELD_FILE_TYPE: {
                "description": "Optional file type filter (original or preservation)",
                "in": "query",
                "type": "str",
            },
            fields.FIELD_LIMIT: {
                "description": "Number of results to return (default is 20)",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id, file_type=None, limit=20):
        """List largest files"""
        file_type = request.args.get(fields.FIELD_FILE_TYPE)
        try:
            limit = int(request.args.get(fields.FIELD_LIMIT, 20))
        except ValueError:
            pass
        return report_data.largest_files(
            storage_service_id=storage_service_id, file_type=file_type, limit=limit
        )


@api.route("/aips-by-file-format/<storage_service_id>")
class AIPsByFormatList(Resource):
    @api.doc(
        "list_aips_by_format",
        params={
            fields.FIELD_FILE_FORMAT: {
                "description": "File format name (must be exact match)",
                "in": "query",
                "type": "str",
            },
            fields.FIELD_ORIGINAL_FILES: {
                "description": "Return data for original files (default) or preservation derivatives",
                "in": "query",
                "type": "bool",
            },
        },
    )
    def get(self, storage_service_id):
        """List AIPs containing given file format"""
        file_format = request.args.get(fields.FIELD_FILE_FORMAT, "")
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        return report_data.aips_by_file_format(
            storage_service_id=storage_service_id,
            file_format=file_format,
            original_files=original_files,
        )


@api.route("/aips-by-puid/<storage_service_id>")
class AIPsByPUIDList(Resource):
    @api.doc(
        "list_aips_by_puid",
        params={
            fields.FIELD_PUID: {
                "description": "PRONOM ID (PUID)",
                "in": "query",
                "type": "str",
            },
            fields.FIELD_ORIGINAL_FILES: {
                "description": "Return data for original files (default) or preservation derivatives",
                "in": "query",
                "type": "bool",
            },
        },
    )
    def get(self, storage_service_id):
        """List AIPs containing given format version, specified by PUID"""
        puid = request.args.get(fields.FIELD_PUID, "")
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        return report_data.aips_by_puid(
            storage_service_id=storage_service_id,
            puid=puid,
            original_files=original_files,
        )


@api.route("/agents-transfers/<storage_service_id>")
class AgentData(Resource):
    @api.doc("agent_info")
    def get(self, storage_service_id):
        """List user agents and their transfers"""
        return report_data.agents_transfers(storage_service_id=storage_service_id)
