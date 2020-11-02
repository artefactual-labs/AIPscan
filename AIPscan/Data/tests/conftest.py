# -*- coding: utf-8 -*-

import pytest

from AIPscan import db
from AIPscan.application import create_app


@pytest.fixture
def app_instance():
    """Pytest fixture that returns an instance of our application.

    This fixture provides a Flask application context for tests using
    AIPscan's test configuration.

    This pattern can be extended in additional fixtures to, e.g. load
    state to the test database from a fixture as needed for tests.
    """
    app = create_app("test")
    context = app.app_context()
    context.push()
    db.create_all()
    yield app
    db.drop_all()
    context.pop()
