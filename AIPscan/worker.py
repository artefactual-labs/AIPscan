from AIPscan.application import create_app
from AIPscan.celery import configure_celery

app = create_app()
celery = configure_celery(app)
