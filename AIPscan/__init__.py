# -*- coding: utf-8 -*-

import dash

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

from celery import Celery
from flask_celery import make_celery

celery = make_celery(app)

from AIPscan import models

from AIPscan.Aggregator.views import aggregator
from AIPscan.Reporter.views import reporter
from AIPscan.API.views import api
from AIPscan.User.views import user

app.register_blueprint(aggregator, url_prefix="/aggregator")
app.register_blueprint(reporter, url_prefix="/reporter")
app.register_blueprint(api, url_prefix="/api")
app.register_blueprint(api, url_prefix="/user")

from flask.helpers import get_root_path

# TODO: Dash is its own Flask application. Understand if it can even be
# imported in the factory model as a blueprint. It feels like it will be
# unlikely.
#
# Integration pattern taken from Oleg Komarov: https://bit.ly/3gcUXrk
#
def register_charts(app):
    from AIPscan.Charts.layout import layout
    from AIPscan.Charts.callbacks import register_callbacks

    meta_viewport = {
        "name": "viewport",
        "content": "width=device-width, initial-scale=1, shrink-to-fit=no",
    }
    aipscan = dash.Dash(
        __name__,
        server=app,
        url_base_pathname="/charts/",
        assets_folder=get_root_path(__name__) + "/Charts/assets/",
        meta_tags=[meta_viewport],
    )
    with app.app_context():
        aipscan.title = "AIPscan: Charts"
        aipscan.layout = layout
        register_callbacks(aipscan)


register_charts(app)
