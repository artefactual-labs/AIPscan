import os

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "aipscan.db")
SQLALCHEMY_ECHO = True

SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
