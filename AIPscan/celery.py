"""This module contains code related to Celery configuration."""

import os

from celery import Celery

celery = Celery(
    "tasks",
    backend=os.getenv("CELERY_RESULT_BACKEND", "db+sqlite:///celerytasks.db"),
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
    return celery
