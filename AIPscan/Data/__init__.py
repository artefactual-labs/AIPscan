# -*- coding: utf-8 -*-

from AIPscan.models import StorageService


def _get_storage_service(storage_service_id):
    """Return Storage Service with ID or None.

    Unlike elsewhere in our application, here we do not fall back to
    a different StorageService if the user-supplied ID is invalid to
    prevent inaccurate information from being returned.

    :param storage_service_id: Storage Service ID

    :returns: StorageService object or None
    """
    return StorageService.query.get(storage_service_id)
