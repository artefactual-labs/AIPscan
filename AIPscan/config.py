import os

DEFAULT_AIPSCAN_DB = (
    "mysql+pymysql://aipscan:demo@127.0.0.1:3406/aipscan?charset=utf8mb4"
)
DEFAULT_CELERY_DB = "mysql+pymysql://aipscan:demo@127.0.0.1:3406/celery?charset=utf8mb4"
DEFAULT_TEST_DB = (
    "mysql+pymysql://aipscan:demo@127.0.0.1:3406/aipscan_test?charset=utf8mb4"
)
DEFAULT_TEST_CELERY_DB = (
    "mysql+pymysql://aipscan:demo@127.0.0.1:3406/celery?charset=utf8mb4"
)

DEFAULT_TYPESENSE_HOST = "localhost"
DEFAULT_TYPESENSE_PORT = "8108"
DEFAULT_TYPESENSE_API_KEY = None
DEFAULT_TYPESENSE_PROTOCOL = "http"
DEFAULT_TYPESENSE_TIMEOUT_SECONDS = "30"
DEFAULT_TYPESENSE_COLLECTION_PREFIX = "aipscan_"


def _env_bool(name, default="false"):
    """Return a boolean from an environment variable.

    Accepts common truthy strings: 1, true, yes, on (case-insensitive).
    """
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


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
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", DEFAULT_TYPESENSE_HOST)
    TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", DEFAULT_TYPESENSE_PORT)
    TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", DEFAULT_TYPESENSE_API_KEY)
    TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", DEFAULT_TYPESENSE_PROTOCOL)
    TYPESENSE_TIMEOUT_SECONDS = os.getenv(
        "TYPESENSE_TIMEOUT_SECONDS", DEFAULT_TYPESENSE_TIMEOUT_SECONDS
    )
    TYPESENSE_COLLECTION_PREFIX = os.getenv(
        "TYPESENSE_COLLECTION_PREFIX", DEFAULT_TYPESENSE_COLLECTION_PREFIX
    )


class DevelopmentConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_TEST_DATABASE_URI", DEFAULT_TEST_DB)
    SQLALCHEMY_CELERY_BACKEND = os.getenv(
        "SQLALCHEMY_TEST_CELERY_BACKEND",
        os.getenv("SQLALCHEMY_CELERY_BACKEND", DEFAULT_TEST_CELERY_DB),
    )
    SQLALCHEMY_BINDS = {"celery": SQLALCHEMY_CELERY_BACKEND}


CONFIGS = {"dev": DevelopmentConfig, "test": TestConfig, "default": Config}
