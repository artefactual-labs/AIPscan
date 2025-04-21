# -*- coding: utf-8 -*-
__version__ = "0.7.0b"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())

__all__ = ["__version__", "__version_info__"]

import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from AIPscan.celery import configure_celery
from AIPscan.navbar import NavBar
from config import CONFIGS

db = SQLAlchemy()


def create_app(config_name="default"):
    """Flask app factory, returns app instance."""
    app = Flask(__name__)

    app.config.from_object(CONFIGS[config_name])

    # Display DB settings
    if "SQLALCHEMY_DATABASE_URI" in os.environ:
        print(f"SQLALCHEMY_DATABASE_URI set to {os.environ['SQLALCHEMY_DATABASE_URI']}")

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

        # Define navigation bar sections and route-to-section mapping (needed
        # given that the "AIPs" and "Reports" sections are in the same Blueprint)
        navbar = NavBar()
        navbar.add_section(
            "Archivematica Storage Services", "aggregator.storage_services"
        )
        navbar.add_section("AIPs", "reporter.view_aips")
        navbar.add_section("Reports", "reporter.reports")

        navbar.map_route("reporter.view_aip", "AIPs")
        navbar.map_route("reporter.view_file", "AIPs")

        # Inject navigation bar into templates
        @app.context_processor
        def inject_navbar():
            return dict(navbar=navbar)

        # Set up 404 handling
        @app.errorhandler(404)
        def page_not_found(e):
            return render_template("error/404.html"), 404

        return app
