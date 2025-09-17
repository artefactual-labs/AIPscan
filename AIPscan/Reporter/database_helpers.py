def get_possible_storage_locations(storage_service):
    """Return list of Storage Locations if storage service provided."""
    if storage_service is None:
        return []

    return storage_service.storage_locations
