"""
Tests for core.monitoring — backend error tracking (Sentry). Before this
module, apps/api and apps/webhooks had no error tracking of any kind: an
unhandled exception's only trace was a local stdout log line, gone once
the container restarts or logs rotate. These tests cover the adapter
selection (noop when unconfigured, real Sentry client when a DSN is
present) and that captured exceptions/messages actually reach
sentry_sdk rather than silently doing nothing.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import config
import core.monitoring as monitoring


@pytest.fixture(autouse=True)
def clean_monitoring_state(monkeypatch):
    monitoring.reset_for_tests()
    monkeypatch.setattr(config, "SENTRY_DSN", "")
    yield
    monitoring.reset_for_tests()


def test_is_sentry_configured_false_when_dsn_empty(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "")
    assert config.is_sentry_configured() is False


def test_is_sentry_configured_true_when_dsn_set(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    assert config.is_sentry_configured() is True


def test_init_monitoring_stays_noop_without_a_dsn():
    monitoring.init_monitoring(service_name="api")
    assert monitoring.is_monitoring_enabled() is False


def test_noop_adapter_capture_calls_never_raise():
    monitoring.init_monitoring(service_name="api")
    # Must be safe to call unconditionally from application code, exactly
    # as if monitoring were fully configured — nothing should need an
    # `if monitoring_enabled():` guard around every call site.
    monitoring.capture_exception(ValueError("should be swallowed"))
    monitoring.capture_message("should be swallowed")


def test_init_monitoring_wires_a_real_sentry_adapter_with_a_dsn(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monitoring.init_monitoring(service_name="api")
    assert monitoring.is_monitoring_enabled() is True


def test_capture_exception_reaches_sentry_sdk(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monitoring.init_monitoring(service_name="api")

    import sentry_sdk

    mock_capture = MagicMock()
    monkeypatch.setattr(sentry_sdk, "capture_exception", mock_capture)

    error = ValueError("boom")
    monitoring.capture_exception(error)

    mock_capture.assert_called_once_with(error)


def test_capture_exception_with_context_still_reaches_sentry_sdk(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monitoring.init_monitoring(service_name="api")

    import sentry_sdk

    mock_capture = MagicMock()
    monkeypatch.setattr(sentry_sdk, "capture_exception", mock_capture)

    error = RuntimeError("indexing failed")
    monitoring.capture_exception(error, workspace_id="ws_1", document_id="doc_1")

    mock_capture.assert_called_once_with(error)


def test_capture_message_reaches_sentry_sdk(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monitoring.init_monitoring(service_name="api")

    import sentry_sdk

    mock_capture = MagicMock()
    monkeypatch.setattr(sentry_sdk, "capture_message", mock_capture)

    monitoring.capture_message("something noteworthy", level="warning")

    mock_capture.assert_called_once_with("something noteworthy", level="warning")


def test_init_monitoring_is_safe_to_call_more_than_once(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monitoring.init_monitoring(service_name="api")
    monitoring.init_monitoring(service_name="api")
    assert monitoring.is_monitoring_enabled() is True
