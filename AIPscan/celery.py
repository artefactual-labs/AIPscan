"""This module contains code related to Celery configuration."""

import os

from celery import Celery

from AIPscan.config import DEFAULT_CELERY_DB

DEFAULT_CELERY_RESULT_BACKEND = "db+" + DEFAULT_CELERY_DB

celery = Celery(
    "tasks",
    backend=os.getenv("CELERY_RESULT_BACKEND", DEFAULT_CELERY_RESULT_BACKEND),
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest@localhost//"),
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
        "CELERY_RESULT_BACKEND", "db+" + app.config["SQLALCHEMY_CELERY_BACKEND"]
    )
    celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", celery.conf.broker_url)
    return celery
