"""
Tests for api/routers/public.py's unauthenticated contact-form endpoint.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import api.routers.public as public_router
from api.schemas import ContactRequestBody


def make_request(client_host: str = "203.0.113.1") -> Request:
    scope = {
        "type": "http",
        "client": (client_host, 12345),
        "headers": [],
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def clear_rate_limit_log():
    public_router._submission_log.clear()
    yield
    public_router._submission_log.clear()


def contact_body(**overrides) -> ContactRequestBody:
    defaults = dict(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        company="Acme",
        subject="general",
        message="Hello there.",
    )
    defaults.update(overrides)
    return ContactRequestBody(**defaults)


def test_honeypot_filled_skips_without_sending(monkeypatch):
    called = []
    monkeypatch.setattr(
        public_router, "send_email", lambda **kwargs: called.append(kwargs) or "sent"
    )

    result = public_router.submit_contact(
        contact_body(honeypot="I am a bot"), make_request()
    )

    assert result.status == "skipped"
    assert called == []


def test_email_disabled_returns_skipped(monkeypatch):
    monkeypatch.setattr("config.EMAIL_ENABLED", False)

    result = public_router.submit_contact(contact_body(), make_request())

    assert result.status == "skipped"


def test_email_enabled_sends_with_correct_recipient(monkeypatch):
    monkeypatch.setattr("config.EMAIL_ENABLED", True)
    monkeypatch.setattr("config.SUPPORT_EMAIL", "support@example.com")

    captured = {}

    def fake_send_email(*, to_email, subject, body_text, body_html=None):
        captured["to_email"] = to_email
        captured["subject"] = subject
        captured["body_text"] = body_text
        return "resend"

    monkeypatch.setattr(public_router, "send_email", fake_send_email)

    result = public_router.submit_contact(
        contact_body(subject="sales"), make_request()
    )

    assert result.status == "sent"
    assert captured["to_email"] == "support@example.com"
    assert "Ada Lovelace" in captured["subject"]
    assert "Sales inquiry" in captured["subject"]
    assert "Hello there." in captured["body_text"]


def test_invalid_email_rejected():
    with pytest.raises(HTTPException) as exc_info:
        public_router.submit_contact(
            contact_body(email="not-an-email"), make_request()
        )
    assert exc_info.value.status_code == 400


def test_rate_limit_blocks_after_max_requests(monkeypatch):
    monkeypatch.setattr("config.EMAIL_ENABLED", False)
    request = make_request("198.51.100.7")

    for _ in range(public_router._RATE_LIMIT_MAX_REQUESTS):
        result = public_router.submit_contact(contact_body(), request)
        assert result.status == "skipped"

    with pytest.raises(HTTPException) as exc_info:
        public_router.submit_contact(contact_body(), request)
    assert exc_info.value.status_code == 429


def test_email_delivery_error_returns_502(monkeypatch):
    from services.email_service import EmailDeliveryError

    monkeypatch.setattr("config.EMAIL_ENABLED", True)

    def raise_error(**kwargs):
        raise EmailDeliveryError("boom")

    monkeypatch.setattr(public_router, "send_email", raise_error)

    with pytest.raises(HTTPException) as exc_info:
        public_router.submit_contact(contact_body(), make_request())
    assert exc_info.value.status_code == 502
