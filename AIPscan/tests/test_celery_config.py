"""Tests for Celery configuration loading and precedence."""

import importlib
import sys


def _import_fresh_celery():
    """Import `AIPscan.celery` fresh so settings re-evaluate."""
    sys.modules.pop("AIPscan.celery", None)
    return importlib.import_module("AIPscan.celery")


def test_defaults_used_when_no_celeryconfig(monkeypatch):
    """Fallback to module defaults when celeryconfig is absent and no env set."""

    # Ensure environment does not override defaults.
    monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    sys.modules.pop("celeryconfig", None)

    celery_mod = _import_fresh_celery()

    assert (
        celery_mod.celery.conf.result_backend
        == celery_mod.DEFAULT_CELERY_RESULT_BACKEND
    )
    assert celery_mod.celery.conf.broker_url == celery_mod.DEFAULT_CELERY_BROKER_URL


def test_env_overrides_celeryconfig(monkeypatch, tmp_path):
    """Env vars should override values loaded from celeryconfig."""

    cfg = tmp_path / "celeryconfig.py"
    cfg.write_text(
        """
result_backend = "db+sqlite:///celeryconfig.db"
broker_url = "amqp://celeryconfig//"
task_always_eager = True
"""
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://env-backend")
    monkeypatch.setenv("CELERY_BROKER_URL", "amqp://env-broker//")

    sys.modules.pop("celeryconfig", None)

    celery_mod = _import_fresh_celery()

    # Custom setting proves celeryconfig was loaded.
    assert celery_mod.celery.conf.task_always_eager is True

    # Env values override celeryconfig values.
    assert celery_mod.celery.conf.result_backend == "redis://env-backend"
    assert celery_mod.celery.conf.broker_url == "amqp://env-broker//"
