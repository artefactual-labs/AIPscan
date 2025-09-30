import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _metadata_version

try:
    __version__ = _metadata_version("AIPscan")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]

from flask import Flask
from flask import render_template
from flask_sqlalchemy import SQLAlchemy

from AIPscan.celery import configure_celery
from AIPscan.config import CONFIGS
from AIPscan.navbar import NavBar

db = SQLAlchemy()


def create_app(config_name=None):
    """Flask app factory, returns app instance.

    If no config_name is passed (i.e. config_name is None), honor the
    ``FLASK_CONFIG`` environment variable; otherwise default to "default".
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "default")
    config = CONFIGS.get(config_name)

    app = Flask(__name__)
    app.config.from_object(config)

    app.logger.info("Starting AIPscan application... (config=%s)", config_name)

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

        # Ensure all SQLAlchemy models are registered before schema creation.
        from AIPscan import models  # noqa: F401

        db.init_app(app)
        configure_celery(app)

        from AIPscan.cli import register_cli

        register_cli(app)

        # Avoid schema creation races under Gunicorn/Celery.
        # Set this only for one process.
        if app.config.get("CREATE_DB"):
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
