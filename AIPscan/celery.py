"""This module contains code related to Celery configuration."""

import os

from celery import Celery

DEFAULT_CELERY_RESULT_BACKEND = (
    "db+mysql+pymysql://aipscan:demo@127.0.0.1:3406/celery?charset=utf8mb4"
)
DEFAULT_CELERY_BROKER_URL = "amqp://guest@localhost//"

celery = Celery(
    "tasks",
    backend=os.getenv("CELERY_RESULT_BACKEND", DEFAULT_CELERY_RESULT_BACKEND),
    broker=os.getenv("CELERY_BROKER_URL", DEFAULT_CELERY_BROKER_URL),
    include=["AIPscan.Aggregator.tasks"],
)


def configure_celery(app):
    """Add Flask app context to celery.Task."""
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    celery.conf.result_backend = os.getenv(
        "CELERY_RESULT_BACKEND", DEFAULT_CELERY_RESULT_BACKEND
    )
    celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", DEFAULT_CELERY_BROKER_URL)
    return celery
