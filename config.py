import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    pass


class ProdConfig(Config):
    pass


class DevConfig(Config):
    debug = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "aipscope.db")
    SQLALCHEMY_ECHO = True
