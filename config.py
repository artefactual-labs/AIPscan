# -*- coding: utf-8 -*-

import os

basedir = os.path.abspath(os.path.dirname(__file__))

DEFAULT_AIPSCAN_DB = "sqlite:///" + os.path.join(basedir, "aipscan.db")
DEFAULT_CELERY_DB = "sqlite:///" + os.path.join(basedir, "celerytasks.db")


class Config:
    # Be sure to set a secure secret key for production.
    SECRET_KEY = os.getenv("SECRET_KEY", "you-will-never-guess")

    DEBUG = False
    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", DEFAULT_AIPSCAN_DB)
    SQLALCHEMY_CELERY_BACKEND = os.getenv(
        "SQLALCHEMY_CELERY_BACKEND", DEFAULT_CELERY_DB
    )
    SQLALCHEMY_BINDS = {"celery": SQLALCHEMY_CELERY_BACKEND}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


CONFIGS = {"dev": DevelopmentConfig, "test": TestConfig, "default": Config}
