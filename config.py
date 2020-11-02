# -*- coding: utf-8 -*-

import os

basedir = os.path.abspath(os.path.dirname(__file__))

# change to os.environ settings in production
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "aipscan.db")
SQLALCHEMY_ECHO = False

SQLALCHEMY_CELERY_BACKEND = "sqlite:///" + os.path.join(basedir, "celerytasks.db")

# change to a long random code (e.g. UUID) when pushing to production
SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"

SQLALCHEMY_BINDS = {"celery": SQLALCHEMY_CELERY_BACKEND}
