import datetime
import sys
import time

import typesense
from flask import current_app
from sqlalchemy import inspect

from AIPscan import db
from AIPscan.models import AIP, FileType

COLLECTION_PREFIX = "aipscan_"

FACET_FIELDS = {
    "file": ["file_format", "file_type", "puid", "aip_id", "size", "aip_create_date"]
}


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
    return int(
        time.mktime(datetime.datetime.strptime(date_string, "%Y-%m-%d").timetuple())
    )


def assemble_filter_by(filters):
    filter_by = ""

    for clause in filters:
        if filter_by != "":
            filter_by += " && "

        filter_by += f"{clause[0]}:{clause[1]}{str(clause[2])}"

    return filter_by


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


def facet_values(result, field_name=None):
    facet_values = {}

    for facet_count in result["facet_counts"]:
        facet_values[facet_count["field_name"]] = []

        for count in facet_count["counts"]:
            facet_values[facet_count["field_name"]].append(count["value"])

    if field_name:
        return facet_values[field_name]

    return facet_values


def facet_counts(result, field_name=None):
    facet_values = {}

    for facet_count in result["facet_counts"]:
        facet_values[facet_count["field_name"]] = []

        for count in facet_count["counts"]:
            facet_values[facet_count["field_name"]].append(count["count"])

    if field_name:
        return facet_values[field_name]

    return facet_values


def facet_totals(result, field_name=None):
    total_values = {}

    for facet_count in result["facet_counts"]:
        total_values[facet_count["field_name"]] = facet_count["stats"]["total_values"]

    if field_name:
        return total_values[field_name]

    return total_values


def app_models():
    models = []

    for model in db.Model.__subclasses__():
        # Omit models used only by Celery
        if not hasattr(model, "__bind_key__") or model.__bind_key__ != "celery":
            models.append(model)

    return models


def get_model_table(model):
    inst = inspect(model)
    return str(inst.tables[0])


def fields_from_model(model):
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

    # File collection documents will be augmented with related data
    if table == "file":
        fields.append({"name": "storage_service_id", "type": "int32"})
        fields.append({"name": "storage_location_id", "type": "int32"})
        fields.append({"name": "aip_create_date", "type": "int64", "facet": True})

    return fields


def get_model_fields():
    model_fields = {}

    models = app_models()

    for model in models:
        fields = fields_from_model(model)
        model_fields[model] = fields

    return model_fields


def initialize_index():
    ts_client = client()

    # Create Typesense collections containing data for each model
    model_fields = {}

    for model in app_models():
        table = get_model_table(model)

        fields = fields_from_model(model)
        model_fields[model] = fields

        # Delete collection if it exists
        try:
            ts_client.collections[collection_prefix(table)].delete()
        except Exception:
            pass

        # Create collection
        ts_client.collections.create(
            {"name": collection_prefix(table), "fields": fields}
        )


def populate_index():
    ts_client = client()

    models = app_models()
    model_fields = get_model_fields()

    # Cache AIP storage services/locations
    aip_storage_service_ids = {}
    aip_storage_location_ids = {}
    aip_create_dates = {}

    results = AIP.query.all()

    for result in results:
        aip_storage_service_ids[result.id] = result.storage_service_id
        aip_storage_location_ids[result.id] = result.storage_location_id
        aip_create_dates[result.id] = result.create_date

    # Add documents to collections
    for model in models:
        table = get_model_table(model)

        results = model.query.all()

        docs = []
        indexed = 0
        for result in results:
            document = {}

            for field in model_fields[model]:
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

            if table == "file":
                document["storage_service_id"] = aip_storage_service_ids[result.aip_id]
                document["storage_location_id"] = aip_storage_location_ids[
                    result.aip_id
                ]

                # Round AIP create date to the day
                dt = aip_create_dates[result.aip.id]
                dt = datetime.datetime(*dt.timetuple()[0:3])
                document["aip_create_date"] = int(dt.strftime("%s"))
                print("RW:" + str(aip_create_dates[result.aip.id]))
                print("CD:" + str(document["aip_create_date"]))

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
