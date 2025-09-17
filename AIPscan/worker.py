"""This module defines and initalizes a Celery worker.

Since Celery workers are run separately from the Flask application (for
example via a systemd service), we use our Application Factory function
to provide application context.
"""

from AIPscan import create_app
from AIPscan.celery import configure_celery

app = create_app()
celery = configure_celery(app)
