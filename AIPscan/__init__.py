# -*- coding: utf-8 -*-

from flask import Flask, render_template
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
        from AIPscan.API.views import api
        from AIPscan.Home.views import home
        from AIPscan.Reporter.views import reporter
        from AIPscan.User.views import user

        app.register_blueprint(aggregator, url_prefix="/aggregator")
        app.register_blueprint(reporter, url_prefix="/reporter")
        app.register_blueprint(user, url_prefix="/user")
        app.register_blueprint(api)
        app.register_blueprint(home)

        db.init_app(app)
        configure_celery(app)

        db.create_all()

        @app.errorhandler(404)
        def page_not_found(e):
            return render_template("error/404.html"), 404

        return app
