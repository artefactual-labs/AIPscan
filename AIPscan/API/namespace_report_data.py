"""Report data namespace

Return data optimized for reports implemented in the Reporter
blueprint for consumption by external systems.
"""

from flask import request
from flask_restx import Namespace
from flask_restx import Resource

from AIPscan.API import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_bool
from AIPscan.helpers import parse_datetime_bound

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
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """List file format versions with file count and size"""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)

        return report_data.format_versions_count(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            storage_location_id=storage_location_id,
        )


@api.route("/largest-aips/<storage_service_id>")
class LargestAIPList(Resource):
    @api.doc(
        "list_largest_aips",
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
            fields.FIELD_LIMIT: {
                "description": "Number of results to return (default is 20)",
                "in": "query",
                "type": "int",
            },
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id, limit=20):
        """List largest AIPs"""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        try:
            limit = int(request.args.get(fields.FIELD_LIMIT, 20))
        except ValueError:
            limit = 20
        return report_data.largest_aips(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            storage_location_id=storage_location_id,
            limit=limit,
        )


@api.route("/largest-files/<storage_service_id>")
class LargestFileList(Resource):
    @api.doc(
        "list_largest_files",
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
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id, file_type=None, limit=20):
        """List largest files"""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        file_type = request.args.get(fields.FIELD_FILE_TYPE)
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        try:
            limit = int(request.args.get(fields.FIELD_LIMIT, 20))
        except ValueError:
            limit = 20
        return report_data.largest_files(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            storage_location_id=storage_location_id,
            file_type=file_type,
            limit=limit,
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
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """List AIPs containing given file format"""
        file_format = request.args.get(fields.FIELD_FILE_FORMAT, "")
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        return report_data.aips_by_file_format(
            storage_service_id=storage_service_id,
            file_format=file_format,
            original_files=original_files,
            storage_location_id=storage_location_id,
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
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """List AIPs containing given format version, specified by PUID"""
        puid = request.args.get(fields.FIELD_PUID, "")
        original_files = parse_bool(request.args.get(fields.FIELD_ORIGINAL_FILES, True))
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        return report_data.aips_by_puid(
            storage_service_id=storage_service_id,
            puid=puid,
            original_files=original_files,
            storage_location_id=storage_location_id,
        )


@api.route("/agents-transfers/<storage_service_id>")
class AgentData(Resource):
    @api.doc(
        "agent_info",
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
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """List user agents and their transfers"""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)
        return report_data.agents_transfers(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            storage_location_id=storage_location_id,
        )


@api.route("/storage_locations/<storage_service_id>")
class StorageLocations(Resource):
    @api.doc(
        "storage_locations",
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
        """List AIP store locations and their usage."""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        return report_data.storage_locations(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
        )


@api.route("/storage_location_usage_over_time/<storage_service_id>")
class StorageLocationsUsageOverTime(Resource):
    @api.doc(
        "storage_locations_usage_over_time",
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
            fields.FIELD_CUMULATIVE: {
                "description": "Return per month storage location usage: differential (False, default) or cumulative (True)",
                "in": "query",
                "type": "bool",
            },
        },
    )
    def get(self, storage_service_id):
        """List AIP store locations and their usage."""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        cumulative = parse_bool(
            request.args.get(fields.FIELD_CUMULATIVE), default=False
        )
        return report_data.storage_locations_usage_over_time(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            cumulative=cumulative,
        )
