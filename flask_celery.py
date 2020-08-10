# -*- coding: utf-8 -*-

from celery import Celery


def make_celery(app):
    task_queue = Celery(
        app.import_name,
        backend=app.config["CELERY_RESULT_BACKEND"],
        broker=app.config["CELERY_BROKER_URL"],
    )
    task_queue.conf.update(app.config)

    TaskBase = task_queue.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    task_queue.Task = ContextTask
    return task_queue
