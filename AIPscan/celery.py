"""This module contains code related to Celery configuration."""

import importlib
import importlib.util
import logging
import os

from celery import Celery

DEFAULT_CELERY_RESULT_BACKEND = (
    "db+mysql+pymysql://aipscan:demo@127.0.0.1:3406/celery?charset=utf8mb4"
)
DEFAULT_CELERY_BROKER_URL = "amqp://guest@localhost//"

logger = logging.getLogger(__name__)

celery = Celery("tasks", include=["AIPscan.Aggregator.tasks"])

# Attempt to load optional user-provided settings from a `celeryconfig.py` on
# PYTHONPATH.
spec = importlib.util.find_spec("celeryconfig")
if spec is not None:
    cfg = importlib.import_module("celeryconfig")
    celery.config_from_object(cfg)
    logger.info("Loaded Celery settings from celeryconfig.")

# Environment variables take precedence over anything loaded above.
celery.conf.result_backend = os.getenv(
    "CELERY_RESULT_BACKEND", DEFAULT_CELERY_RESULT_BACKEND
)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", DEFAULT_CELERY_BROKER_URL)


def configure_celery(app):
    """Add Flask app context to celery.Task."""
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
