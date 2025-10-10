"""Helpers for working with Aggregator download directories."""

import os
from importlib import resources

from flask import current_app

DEFAULT_DOWNLOAD_ROOT = os.fspath(resources.files(__package__).joinpath("downloads"))


def get_download_root(app=None) -> str:
    """Return the base directory used to stage download artifacts."""
    if app is not None:
        return app.config.get("AGGREGATOR_DOWNLOAD_ROOT", DEFAULT_DOWNLOAD_ROOT)

    try:
        application = current_app._get_current_object()
    except RuntimeError:
        env_override = os.getenv("AGGREGATOR_DOWNLOAD_ROOT")
        if env_override:
            return env_override
        return DEFAULT_DOWNLOAD_ROOT

    return application.config.get("AGGREGATOR_DOWNLOAD_ROOT", DEFAULT_DOWNLOAD_ROOT)
