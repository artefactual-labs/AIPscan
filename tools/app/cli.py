import pathlib
import sys

import click
from flask import Flask

# Alter path so tools can import AIPscan's modules
relpath = f"{pathlib.Path(__file__).parent}/../../../AIPscan"
sys.path.append(str(pathlib.Path(relpath).resolve()))

config_name = "default"


def create_app_instance(configuration, db):
    app = Flask(__name__)
    app.config.from_object(configuration)

    db.init_app(app)

    return app


def raise_click_error(message):
    err = click.ClickException(message)
    err.exit_code = 1
    raise err


def log_and_raise_click_error(logger, message):
    logger.critical(message)
    raise_click_error(message)
