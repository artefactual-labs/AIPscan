import os

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "aipscan.db")
SQLALCHEMY_ECHO = False

CELERY_BROKER_URL = "amqp://guest@localhost//"
CELERY_RESULT_BACKEND = "db+sqlite:///celerytasks.db"

# change to a long random code (e.g. UUID) when pushing to production
SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
