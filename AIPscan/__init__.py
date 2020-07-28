# -*- coding: utf-8 -*-

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
