import datetime
import math

import typesense
from flask import current_app
from sqlalchemy import inspect

from AIPscan.models import AIP
from AIPscan.models import File
from AIPscan.models import FileType

APP_MODELS = [AIP, File]

FACET_FIELDS = {
    "file": ["file_format", "file_type", "puid", "aip_id", "size", "aip_create_date"]
}

AIP_FIELDS_TO_CACHE = {
    "storage_service_id": None,
    "storage_location_id": None,
    "create_date": "aip_create_date",
    "transfer_name": None,
    "uuid": "aip_uuid",
}


def typesense_enabled():
    return current_app.config["TYPESENSE_API_KEY"] is not None


def client():
    config = current_app.config
    return typesense.Client(
        {
            "api_key": config["TYPESENSE_API_KEY"],
            "nodes": [
                {
                    "host": config["TYPESENSE_HOST"],
                    "port": config["TYPESENSE_PORT"],
                    "protocol": config["TYPESENSE_PROTOCOL"],
                }
            ],
            "connection_timeout_seconds": int(config["TYPESENSE_TIMEOUT_SECONDS"]),
        }
    )


def search(collection, search_parameters, ts_client=None):
    if ts_client is None:
        ts_client = client()

    return ts_client.collections[collection_prefix(collection)].documents.search(
        search_parameters
    )


def collection_prefix(collection):
    return current_app.config["TYPESENSE_COLLECTION_PREFIX"] + collection


EPOCH_UTC = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def datetime_to_timestamp_int(datetime_obj):
    """Convert a date or datetime to a Unix timestamp (seconds).

    This function normalizes to midnight and computes seconds since the Unix
    epoch in UTC. Naive datetimes are treated as UTC. `time.mktime` was used in
    the past but avoided now because its behavior is inconsistent across
    platforms and timezones.
    """
    # Floor to midnight.
    base = datetime_obj.replace(hour=0, minute=0, second=0, microsecond=0)

    # Normalize to UTC.
    if base.tzinfo is None:
        # Naive datetime: assume it's in UTC by attaching UTC tzinfo.
        base = base.replace(tzinfo=datetime.timezone.utc)
    else:
        # Aware datetime: convert the timestamp to the equivalent UTC time.
        base = base.astimezone(datetime.timezone.utc)

    return int((base - EPOCH_UTC).total_seconds())


def assemble_filter_by(filters):
    filter_by = ""

    for clause in filters:
        if filter_by != "":
            filter_by += " && "

        filter_by += f"{clause[0]}:{clause[1]}{str(clause[2])}"

    return filter_by


def file_filters(storage_service_id, storage_location_id, start_date, end_date):
    start_timestamp = datetime_to_timestamp_int(start_date)
    end_timestamp = datetime_to_timestamp_int(end_date)

    filters = [
        ("aip_create_date", ">=", start_timestamp),
        ("aip_create_date", "<", end_timestamp),
        ("storage_service_id", "=", storage_service_id),
        ("file_type", "=", "'original'"),
    ]

    if storage_location_id is not None and storage_location_id != "":
        filters.append(("storage_location_id", "=", storage_location_id))

    return filters


def facet_value_counts(result, field_name=None):
    facet_value_counts = {}

    for facet_count in result["facet_counts"]:
        facet_value_counts[facet_count["field_name"]] = {}

        for count in facet_count["counts"]:
            facet_value_counts[facet_count["field_name"]][count["value"]] = count[
                "count"
            ]

    if field_name:
        return facet_value_counts[field_name]

    return facet_value_counts


def get_model_table(model):
    inst = inspect(model)
    return str(inst.tables[0])


def collection_fields_from_model(model):
    # Reference model definition
    inst = inspect(model)
    table = str(inst.tables[0])

    # Define Typesense fields for model
    fields = []

    for c in inst.columns:
        field = {"name": c.name}

        # Use Python type as basis of Typesense type
        try:
            py_type = c.type.python_type
        except NotImplementedError:
            py_type = str

        if py_type == FileType:
            field["type"] = "string"
        else:
            ts_types = {
                int: "int32",
                str: "string",
                bool: "bool",
                datetime.datetime: "int64",
            }

            # Use larger number type for size data
            if c.name == "size":
                ts_types[int] = "int64"

            if py_type not in ts_types:
                # Fallback to string for any remaining unmapped types
                field["type"] = "string"
            else:
                field["type"] = ts_types[py_type]

        # Mark certain fields as facets
        if table in FACET_FIELDS and field["name"] in FACET_FIELDS[table]:
            field["facet"] = True

        # Mark non-id fields as optional (to accommodate None values)
        if field["name"] != "id":
            field["optional"] = True

        fields.append(field)

    # AIP collection documents will be augmented with related data
    if table == "aip":
        fields.append({"name": "original_file_count", "type": "int32"})

    # File collection documents will be augmented with related data
    if table == "file":
        fields.append({"name": "storage_service_id", "type": "int32"})
        fields.append({"name": "storage_location_id", "type": "int32"})
        fields.append({"name": "aip_create_date", "type": "int64", "facet": True})
        fields.append({"name": "transfer_name", "type": "string"})
        fields.append({"name": "aip_uuid", "type": "string"})

    return fields


def initialize_index():
    ts_client = client()

    # Create Typesense collections containing data for each model
    for model in APP_MODELS:
        table = get_model_table(model)

        # Delete collection if it exists
        try:
            ts_client.collections[collection_prefix(table)].delete()
        except typesense.exceptions.ObjectNotFound:
            pass

        # Create collection
        fields = collection_fields_from_model(model)

        ts_client.collections.create(
            {"name": collection_prefix(table), "fields": fields}
        )


def model_instance_to_document(model, instance, model_fields=None):
    if model_fields is None:
        model_fields = collection_fields_from_model(model)

    document = {}

    for field in model_fields:
        if hasattr(instance, field["name"]):
            value = getattr(instance, field["name"])

            # Typesense IDs need to be strings
            if field["name"] == "id":
                value = str(value)

            if isinstance(value, datetime.datetime):
                value = int(value.timestamp())

            if isinstance(value, FileType):
                value = str(value).replace("FileType.", "")

            if value is not None:
                document[field["name"]] = value

    return document


def augment_file_document_with_aip_data(table, document, aip_cache, result):
    for aip_field in AIP_FIELDS_TO_CACHE:
        if aip_field != "create_date":
            if AIP_FIELDS_TO_CACHE[aip_field] is None:
                document[aip_field] = aip_cache[aip_field][result.aip_id]
            else:
                document_field = AIP_FIELDS_TO_CACHE[aip_field]
                document[document_field] = aip_cache[aip_field][result.aip_id]

    # Round AIP create date to the day
    dt = aip_cache["create_date"][result.aip_id]
    dt = datetime.datetime(*dt.timetuple()[0:3])
    document["aip_create_date"] = int(dt.strftime("%s"))


def populate_index():
    ts_client = client()

    # Initialize AIP cache
    aip_cache = {}
    for aip_field in AIP_FIELDS_TO_CACHE:
        aip_cache[aip_field] = {}

    # Add documents to collections
    for model in APP_MODELS:
        table = get_model_table(model)
        model_fields = collection_fields_from_model(model)

        results = model.query.all()

        docs = []
        indexed = 0
        completed_percent = 0

        for result in results:
            document = model_instance_to_document(model, result, model_fields)

            if model is File:
                augment_file_document_with_aip_data(table, document, aip_cache, result)

            docs.append(document)
            perform_bulk_document_creation(ts_client, table, docs)

            indexed += 1
            completed_percent = math.ceil(indexed / len(results) * 100)

            status = {
                "type": model.__name__,
                "indexed": indexed,
                "total": len(results),
                "percent": completed_percent,
            }

            if model == AIP:
                for aip_field in AIP_FIELDS_TO_CACHE:
                    aip_cache[aip_field][result.id] = getattr(result, aip_field)

            yield status

        finish_bulk_document_creation(ts_client, table, docs)


def perform_bulk_document_creation(ts_client, table, docs):
    # Send bulk creation every 40 documents
    if len(docs) == 40:
        ts_client.collections[collection_prefix(table)].documents.import_(docs)
        docs = []


def finish_bulk_document_creation(ts_client, table, docs):
    # Send bulk creation of remaining documents
    if len(docs):
        ts_client.collections[collection_prefix(table)].documents.import_(docs)
