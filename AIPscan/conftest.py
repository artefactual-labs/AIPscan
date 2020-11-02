# -*- coding: utf-8 -*-

"""This module defines shared AIPscan pytest fixtures."""

import pytest

from AIPscan import db, create_app


@pytest.fixture
def app_instance():
    """Pytest fixture that returns an instance of our application.

    This fixture provides a Flask application context for tests using
    AIPscan's test configuration.

    This pattern can be extended in additional fixtures to, e.g. load
    state to the test database from a fixture as needed for tests.
    """
    app = create_app("test")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
