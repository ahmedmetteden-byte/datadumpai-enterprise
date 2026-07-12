"""
Billing service and subscription activation tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.billing_service import BillingService, activate_subscription_for_user
from services.subscription_service import SubscriptionService
from tests.conftest import TEST_USER_ID


@pytest.fixture
def billing_env(isolated_env, monkeypatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_paystack")
    return isolated_env


def test_activate_paid_plan_persists_billing_fields(isolated_env):
    subscription = SubscriptionService()
    state = subscription.activate_paid_plan(
        "starter",
        provider="stripe",
        customer_id="cus_123",
        subscription_id="sub_456",
        reference="cs_789",
        current_period_end="2026-08-09T00:00:00+00:00",
    )

    assert state["billing_plan"] == "starter"
    assert state["subscription_status"] == "active"
    assert state["payment_provider"] == "stripe"
    assert state["payment_customer_id"] == "cus_123"
    assert state["payment_subscription_id"] == "sub_456"

    reloaded = SubscriptionService().load_state()
    assert reloaded["payment_reference"] == "cs_789"
    assert reloaded["current_period_end"] == "2026-08-09T00:00:00+00:00"


def test_billing_service_stripe_checkout_url(billing_env, monkeypatch):
    monkeypatch.setattr(
        "services.billing_service.create_checkout_session",
        lambda **kwargs: "https://checkout.stripe.test/session",
    )

    url = BillingService().start_checkout("professional", provider="stripe")
    assert url == "https://checkout.stripe.test/session"


def test_billing_service_complete_stripe_checkout(billing_env, monkeypatch):
    payload = {
        "user_id": TEST_USER_ID,
        "plan_id": "starter",
        "provider": "stripe",
        "customer_id": "cus_abc",
        "subscription_id": "sub_def",
        "reference": "cs_test",
        "current_period_end": "2026-08-09T00:00:00+00:00",
    }
    monkeypatch.setattr(
        "services.billing_service.verify_checkout_session",
        lambda session_id: payload,
    )

    state = BillingService().complete_checkout(
        provider="stripe",
        session_id="cs_test",
    )
    assert state["billing_plan"] == "starter"
    assert state["payment_customer_id"] == "cus_abc"


def test_billing_service_rejects_foreign_checkout(billing_env, monkeypatch):
    monkeypatch.setattr(
        "services.billing_service.verify_checkout_session",
        lambda session_id: {
            "user_id": "other-user",
            "plan_id": "starter",
            "provider": "stripe",
        },
    )

    with pytest.raises(ValueError, match="does not belong"):
        BillingService().complete_checkout(
            provider="stripe",
            session_id="cs_test",
        )


def test_find_user_by_customer_id_json(isolated_env):
    from repositories.billing_repository import find_user_id_by_customer_id

    subscription = SubscriptionService()
    subscription.activate_paid_plan(
        "starter",
        provider="stripe",
        customer_id="cus_lookup",
    )

    assert find_user_id_by_customer_id("cus_lookup") == TEST_USER_ID
    assert find_user_id_by_customer_id("missing") is None


def test_activate_subscription_for_user_helper(isolated_env):
    state = activate_subscription_for_user(
        TEST_USER_ID,
        {
            "plan_id": "professional",
            "provider": "paystack",
            "customer_id": "cust_1",
            "subscription_id": "PLN_1",
            "reference": "ref_1",
            "current_period_end": "2026-08-09T00:00:00+00:00",
        },
    )
    assert state["billing_plan"] == "professional"
    assert state["payment_provider"] == "paystack"


@patch("services.stripe_billing_service.stripe")
def test_stripe_checkout_uses_price_id(mock_stripe, billing_env, monkeypatch):
    monkeypatch.setenv("STRIPE_STARTER_PRICE_ID", "price_starter")
    monkeypatch.setattr("config.STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setattr("config.STRIPE_STARTER_PRICE_ID", "price_starter")
    monkeypatch.setattr("config.is_stripe_configured", lambda: True)

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.test/price"
    mock_stripe.checkout.Session.create.return_value = mock_session

    from services.stripe_billing_service import create_checkout_session

    url = create_checkout_session(
        user_id=TEST_USER_ID,
        email="tester@example.com",
        plan_id="starter",
    )

    assert url == "https://checkout.stripe.test/price"
    call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
    assert call_kwargs["line_items"] == [{"price": "price_starter", "quantity": 1}]


def test_mark_canceled_at_period_end(isolated_env):
    subscription = SubscriptionService()
    subscription.activate_paid_plan("starter", provider="stripe", customer_id="cus_1")
    state = subscription.mark_canceled(at_period_end=True)

    assert state["subscription_status"] == "canceled"
    assert state["cancel_at_period_end"] is True
    assert state["billing_plan"] == "starter"

    immediate = subscription.mark_canceled(at_period_end=False)
    assert immediate["billing_plan"] == "free"
