"""
Tests for api/webhook_server.py's Paystack webhook handling — calls the
handler function directly (asyncio.run), matching this repo's established
pattern for async endpoints (see tests/test_usage_enforcement_router.py)
rather than a real ASGI test client, which isn't used anywhere in this repo.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from api.webhook_server import paystack_webhook
from services.subscription_service import SubscriptionService
from tests.conftest import TEST_USER_ID


class _FakeWebhookRequest:
    """Duck-types just what paystack_webhook actually reads from a
    starlette Request: an awaitable .body() and a .headers.get(...)."""

    def __init__(self, body: dict) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.headers = {"x-paystack-signature": "test-signature"}

    async def body(self) -> bytes:
        return self._body


@pytest.fixture(autouse=True)
def valid_signature(monkeypatch):
    monkeypatch.setattr(
        "api.webhook_server.verify_webhook_signature", lambda payload, signature: True
    )


def test_subscription_create_persists_code_and_token(isolated_env):
    """The webhook is the only source of the subscription_code/email_token
    pair Paystack's disable endpoint requires — see
    services.paystack_billing_service.disable_subscription()."""

    subscription = SubscriptionService()
    subscription.activate_paid_plan(
        "starter", provider="paystack", customer_id="cus_webhook_1"
    )

    request = _FakeWebhookRequest(
        {
            "event": "subscription.create",
            "data": {
                "customer": {"id": "cus_webhook_1"},
                "subscription_code": "SUB_webhook_1",
                "email_token": "tok_webhook_1",
            },
        }
    )

    result = asyncio.run(paystack_webhook(request))

    assert result == {"received": "true"}
    state = SubscriptionService.for_user_id(TEST_USER_ID).load_state()
    assert state["paystack_subscription_code"] == "SUB_webhook_1"
    assert state["paystack_subscription_token"] == "tok_webhook_1"


def test_subscription_create_ignores_unknown_customer(isolated_env):
    """No matching user_id — must not raise, must not create a phantom
    record for a customer this app doesn't recognize."""

    request = _FakeWebhookRequest(
        {
            "event": "subscription.create",
            "data": {
                "customer": {"id": "cus_unknown"},
                "subscription_code": "SUB_x",
                "email_token": "tok_x",
            },
        }
    )

    result = asyncio.run(paystack_webhook(request))
    assert result == {"received": "true"}


def test_subscription_create_ignores_incomplete_payload(isolated_env):
    """A subscription.create event missing subscription_code or email_token
    must not be treated as a valid (but empty) token pair."""

    subscription = SubscriptionService()
    subscription.activate_paid_plan(
        "starter", provider="paystack", customer_id="cus_webhook_2"
    )

    request = _FakeWebhookRequest(
        {
            "event": "subscription.create",
            "data": {"customer": {"id": "cus_webhook_2"}, "subscription_code": "SUB_x"},
        }
    )

    asyncio.run(paystack_webhook(request))

    state = SubscriptionService.for_user_id(TEST_USER_ID).load_state()
    assert state["paystack_subscription_code"] is None
    assert state["paystack_subscription_token"] is None


def test_invalid_signature_rejected(monkeypatch, isolated_env):
    monkeypatch.setattr(
        "api.webhook_server.verify_webhook_signature", lambda payload, signature: False
    )

    from fastapi import HTTPException

    request = _FakeWebhookRequest({"event": "subscription.create", "data": {}})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(paystack_webhook(request))
    assert exc_info.value.status_code == 400
