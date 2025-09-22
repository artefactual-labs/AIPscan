from AIPscan import db
from AIPscan.Data import fields
from AIPscan.models import StorageLocation
from AIPscan.models import StorageService


def _get_storage_service(storage_service_id):
    """Return Storage Service with ID or None.

    Unlike elsewhere in our application, here we do not fall back to
    a different StorageService if the user-supplied ID is invalid to
    prevent inaccurate information from being returned.

    :param storage_service_id: Storage Service ID

    :returns: StorageService object or None
    """
    return db.session.get(StorageService, storage_service_id)


def get_storage_service_name(storage_service_id):
    """Return name of Storage Service or None."""
    name = None
    if storage_service_id:
        storage_service = _get_storage_service(storage_service_id)
        if storage_service:
            name = storage_service.name
    return name


def _get_storage_location(storage_location_id):
    """Return Storage Location with ID or None."""
    return db.session.get(StorageLocation, storage_location_id)


def get_storage_location_description(storage_location_id):
    """Return description of Storage Location or None."""
    description = None
    if storage_location_id:
        storage_location = _get_storage_location(storage_location_id)
        if storage_location:
            description = storage_location.description
    return description


def report_dict(storage_service_id, storage_location_id):
    report = {}

    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)
    report[fields.FIELD_STORAGE_LOCATION] = get_storage_location_description(
        storage_location_id
    )

    return report
