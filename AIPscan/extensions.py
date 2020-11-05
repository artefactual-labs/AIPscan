# -*- coding: utf-8 -*-

"""This module contains code related to Flask extensions.

The Celery instance that is initialized here is lacking application
context, which will be provided via AIPscan.celery's configure_celery
function.
"""

from celery import Celery

from celery_config import CELERY_RESULT_BACKEND, CELERY_BROKER_URL


celery = Celery(
    "tasks",
    backend=CELERY_RESULT_BACKEND,
    broker=CELERY_BROKER_URL,
    include=["AIPscan.Aggregator.tasks"],
)
