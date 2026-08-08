"""
Regression tests: Paystack API failures (network errors, malformed
responses, missing fields) must surface as a clean PaystackBillingError —
which api/routers/billing.py converts to a 400 — never as an unhandled
exception that leaks through as a raw 500.
"""

from __future__ import annotations

import json

import pytest
import requests

from services.paystack_billing_service import (
    PaystackBillingError,
    initialize_transaction,
    verify_transaction,
)


@pytest.fixture(autouse=True)
def paystack_env(monkeypatch):
    monkeypatch.setattr("config.PAYSTACK_SECRET_KEY", "sk_test_example")
    monkeypatch.setattr("config.is_paystack_configured", lambda: True)
    monkeypatch.setattr("config.PAYSTACK_STARTER_PLAN_CODE", "PLN_starter")
    monkeypatch.setattr("config.BILLING_SUCCESS_URL", "https://app.example.com/billing/return")


class _FakeResponse:
    def __init__(self, *, ok: bool, json_data=None, json_error: bool = False):
        self.ok = ok
        self._json_data = json_data
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self._json_data


def test_initialize_transaction_wraps_network_error(monkeypatch):
    def fake_request(*args, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("requests.request", fake_request)

    with pytest.raises(PaystackBillingError, match="Could not reach Paystack"):
        initialize_transaction(user_id="u1", email="user@example.com", plan_id="starter")


def test_initialize_transaction_wraps_malformed_json_response(monkeypatch):
    monkeypatch.setattr(
        "requests.request",
        lambda *a, **k: _FakeResponse(ok=False, json_error=True),
    )

    with pytest.raises(PaystackBillingError, match="unexpected response"):
        initialize_transaction(user_id="u1", email="user@example.com", plan_id="starter")


def test_initialize_transaction_surfaces_paystack_error_message(monkeypatch):
    monkeypatch.setattr(
        "requests.request",
        lambda *a, **k: _FakeResponse(
            ok=False, json_data={"status": False, "message": "Invalid key"}
        ),
    )

    with pytest.raises(PaystackBillingError, match="Invalid key"):
        initialize_transaction(user_id="u1", email="user@example.com", plan_id="starter")


def test_initialize_transaction_rejects_missing_data_field(monkeypatch):
    monkeypatch.setattr(
        "requests.request",
        lambda *a, **k: _FakeResponse(ok=True, json_data={"status": True}),
    )

    with pytest.raises(PaystackBillingError, match="missing expected data"):
        initialize_transaction(user_id="u1", email="user@example.com", plan_id="starter")


def test_initialize_transaction_happy_path_returns_authorization_url(monkeypatch):
    monkeypatch.setattr(
        "requests.request",
        lambda *a, **k: _FakeResponse(
            ok=True,
            json_data={
                "status": True,
                "data": {"authorization_url": "https://checkout.paystack.com/abc123"},
            },
        ),
    )

    url = initialize_transaction(user_id="u1", email="user@example.com", plan_id="starter")
    assert url == "https://checkout.paystack.com/abc123"


def test_verify_transaction_wraps_network_error(monkeypatch):
    def fake_request(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("requests.request", fake_request)

    with pytest.raises(PaystackBillingError, match="Could not reach Paystack"):
        verify_transaction("ref_123")


def test_verify_transaction_happy_path(monkeypatch):
    monkeypatch.setattr(
        "requests.request",
        lambda *a, **k: _FakeResponse(
            ok=True,
            json_data={
                "status": True,
                "data": {
                    "status": "success",
                    "metadata": {"user_id": "u1", "plan_id": "starter"},
                    "customer": {"id": 42},
                },
            },
        ),
    )

    result = verify_transaction("ref_123")
    assert result["provider"] == "paystack"
    assert result["plan_id"] == "starter"
    assert result["customer_id"] == "42"
