import os
import sys

from flask import Flask

# Alter path so tools can import AIPscan's modules
relpath = f"{os.path.dirname(__file__)}/../../../AIPscan"
sys.path.append(os.path.abspath(relpath))

config_name = "default"


def create_app_instance(configuration, db):
    app = Flask(__name__)
    app.config.from_object(configuration)

    db.init_app(app)

    return app
