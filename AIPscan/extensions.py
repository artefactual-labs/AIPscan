# -*- coding: utf-8 -*-

from celery import Celery

from celery_config import CELERY_RESULT_BACKEND, CELERY_BROKER_URL

# Celery instance that will be initialized at import time and then
# further configured via AIPscan.celery's configure_celery method.
celery = Celery(
    "tasks",
    backend=CELERY_RESULT_BACKEND,
    broker=CELERY_BROKER_URL,
    include=["AIPscan.Aggregator.tasks"],
)
