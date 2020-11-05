# -*- coding: utf-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from AIPscan.celery import configure_celery
from config import CONFIGS

db = SQLAlchemy()


def create_app(config_name="default"):
    """Flask app factory, returns app instance."""
    app = Flask(__name__)

    app.config.from_object(CONFIGS[config_name])

    with app.app_context():

        from AIPscan.Aggregator.views import aggregator
        from AIPscan.Reporter.views import reporter
        from AIPscan.User.views import user
        from AIPscan.API.views import api
        from AIPscan.Home.views import home

        app.register_blueprint(aggregator, url_prefix="/aggregator")
        app.register_blueprint(reporter, url_prefix="/reporter")
        app.register_blueprint(user, url_prefix="/user")
        app.register_blueprint(api)
        app.register_blueprint(home)

        db.init_app(app)
        configure_celery(app)

        db.create_all()

        return app
