"""Tests for Flask application factory configuration.

Ensures that SECRET_KEY is properly validated in production and that
development/test environments have appropriate fallback behavior.
"""

import pytest

from AIPscan import create_app


@pytest.mark.parametrize(
    "config_name,secret_value,should_raise,expected_secret",
    [
        # Production requires valid SECRET_KEY.
        ("default", None, True, None),
        ("default", "", True, None),
        ("default", "   ", True, None),
        ("default", "super-secret", False, "super-secret"),
        # Dev and test use fallback.
        ("dev", None, False, "dev"),
        ("test", None, False, "dev"),
    ],
    ids=[
        "prod-rejects-missing-key",
        "prod-rejects-empty-key",
        "prod-rejects-whitespace-key",
        "prod-accepts-valid-key",
        "dev-provides-fallback-key",
        "test-provides-fallback-key",
    ],
)
def test_create_app_secret_key_handling(
    monkeypatch, config_name, secret_value, should_raise, expected_secret
):
    """Test SECRET_KEY validation across all config environments."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    if secret_value is not None:
        monkeypatch.setenv("SECRET_KEY", secret_value)

    if should_raise:
        with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
            create_app(config_name)
    else:
        app = create_app(config_name)
        assert app.config["SECRET_KEY"] == expected_secret
