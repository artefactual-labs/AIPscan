import datetime
import sys
import time

import typesense
from flask import current_app
from sqlalchemy import inspect

from AIPscan.models import AIP, File, FileType

APP_MODELS = [AIP, File]

COLLECTION_PREFIX = "aipscan_"

FACET_FIELDS = {
    "file": ["file_format", "file_type", "puid", "aip_id", "size", "aip_create_date"]
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
            "connection_timeout_seconds": 10,
        }
    )


def list_collections(ts_client):
    results = ts_client.collections.retrieve()

    return results


def search(table, search_parameters, ts_client=None):
    if ts_client is None:
        ts_client = client()

    return ts_client.collections[collection_prefix(table)].documents.search(
        search_parameters
    )


def collection_prefix(table):
    return COLLECTION_PREFIX + table


def date_string_to_timestamp_int(date_string):
    # Round date string to date if time is included
    if len(date_string) > 10:
        date_string = date_string[0:10]

    return int(
        time.mktime(datetime.datetime.strptime(date_string, "%Y-%m-%d").timetuple())
    )


def datetime_to_timestamp_int(datetime_obj):
    # Round datetime to date in case time is included
    datetime_obj = datetime_obj.replace(hour=0, minute=0, second=0)

    return int(time.mktime(datetime_obj.timetuple()))


def assemble_filter_by(filters):
    filter_by = ""

    for clause in filters:
        if filter_by != "":
            filter_by += " && "

        filter_by += f"{clause[0]}:{clause[1]}{str(clause[2])}"

    return filter_by


def file_filters(storage_service_id, storage_location_id, start_date, end_date):
    if type(start_date) is datetime.datetime:
        start_timestamp = datetime_to_timestamp_int(start_date)
        end_timestamp = datetime_to_timestamp_int(end_date) - 1
    else:
        start_timestamp = date_string_to_timestamp_int(start_date)
        end_timestamp = date_string_to_timestamp_int(end_date) - 1

    filters = [
        ("date_created", ">", start_timestamp),
        ("date_created", "<", end_timestamp),
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
        if c.type.python_type == FileType:
            field["type"] = "string"
        else:
            ts_types = {
                int: "int32",
                str: "string",
                bool: "bool",
                datetime.datetime: "int64",
            }

            if c.type.python_type not in ts_types:
                print("ERROR")
                sys.exit(1)
            else:
                field["type"] = ts_types[c.type.python_type]

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

    return fields


def initialize_index():
    ts_client = client()

    # Create Typesense collections containing data for each model
    for model in APP_MODELS:
        table = get_model_table(model)

        # Delete collection if it exists
        try:
            ts_client.collections[collection_prefix(table)].delete()
        except Exception:
            pass

        # Create collection
        fields = collection_fields_from_model(model)

        ts_client.collections.create(
            {"name": collection_prefix(table), "fields": fields}
        )


def populate_index():
    ts_client = client()

    # Cache AIP storage services/locations
    aip_storage_service_ids = {}
    aip_storage_location_ids = {}
    aip_create_dates = {}
    aip_original_file_counts = {}

    results = AIP.query.all()

    for result in results:
        aip_storage_service_ids[result.id] = result.storage_service_id
        aip_storage_location_ids[result.id] = result.storage_location_id
        aip_create_dates[result.id] = result.create_date
        aip_original_file_counts[result.id] = result.original_file_count

    # Add documents to collections
    for model in APP_MODELS:
        table = get_model_table(model)
        model_fields = collection_fields_from_model(model)

        results = model.query.all()

        docs = []
        indexed = 0
        for result in results:
            document = {}

            for field in model_fields:
                if hasattr(result, field["name"]):
                    value = getattr(result, field["name"])

                    if field["name"] == "id":
                        value = str(value)

                    if isinstance(value, datetime.datetime):
                        value = int(value.timestamp())

                    if isinstance(value, FileType):
                        value = str(value).replace("FileType.", "")

                    if value is not None:
                        document[field["name"]] = value

            if table == "aip":
                document["original_file_count"] = aip_original_file_counts[result.id]

            if table == "file":
                document["storage_service_id"] = aip_storage_service_ids[result.aip_id]
                document["storage_location_id"] = aip_storage_location_ids[
                    result.aip_id
                ]

                # Round AIP create date to the day
                dt = aip_create_dates[result.aip.id]
                dt = datetime.datetime(*dt.timetuple()[0:3])
                document["aip_create_date"] = int(dt.strftime("%s"))

            docs.append(document)

            # Send bulk creation every 40 documents
            if len(docs) == 40:
                print("Importing...")
                result = ts_client.collections[
                    collection_prefix(table)
                ].documents.import_(docs)
                docs = []

            indexed += 1
            yield (table, indexed, len(results))

        # Send bulk creation of remaining documents
        if len(docs):
            print("Importing...")
            result = ts_client.collections[collection_prefix(table)].documents.import_(
                docs
            )
