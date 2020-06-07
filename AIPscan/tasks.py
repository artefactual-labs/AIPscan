from celery import Celery
from AIPscan import celery


@celery.task()
def add_together(a, b):
    return a + b
