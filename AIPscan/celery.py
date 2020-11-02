# -*- coding: utf-8 -*-

from AIPscan import extensions

# PICTURAE TODO: Create a different app configuration for celery. If
# we inspect the celery object below celery.__dict__ we can see all
# of the app consts have been consumed by the celery constructor,
# probably as a **kwarg and hasn't decided to rid itself of any values
# that are superfluous.


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
