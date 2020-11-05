# -*- coding: utf-8 -*-

"""This module contains code related to Celery configuration."""

from AIPscan import extensions


def configure_celery(app):
    """Add Flask app context to celery.Task."""
    TaskBase = extensions.celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    extensions.celery.Task = ContextTask
    return extensions.celery
