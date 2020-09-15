# -*- coding: utf-8 -*-

import os

basedir = os.path.abspath(os.path.dirname(__file__))

# change to os.environ settings in production
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "aipscan.db")
SQLALCHEMY_ECHO = False

CELERY_BROKER_URL = "amqp://guest@localhost//"

"""PICTURAR TODO:

We get different protocol errors for these connection strings depending
on which we use and where.

    * SQLAlchemy: Can't load plugin: sqlalchemy.dialects:db.sqlite ("db+sqlite://")
    * Celery: No module named sqlite ("sqlite://")
"""
CELERY_RESULT_BACKEND = "db+sqlite:///celerytasks.db"
SQLALCHEMY_CELERY_BACKEND = "sqlite:///" + os.path.join(basedir, "celerytasks.db")

# change to a long random code (e.g. UUID) when pushing to production
SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"

SQLALCHEMY_BINDS = {"celery": SQLALCHEMY_CELERY_BACKEND}
