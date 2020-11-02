# -*- coding: utf-8 -*-

import os

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", "db+sqlite:///celerytasks.db"
)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest@localhost//")
