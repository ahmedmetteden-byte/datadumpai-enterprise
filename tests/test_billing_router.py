"""
Tests for api/routers/billing.py — calls the router functions directly,
matching this repo's established pattern (see
tests/test_intelligence_conversation_persistence.py) rather than
fastapi.testclient.TestClient, which isn't used anywhere in this repo.
"""

from __future__ import annotations

import pytest

from api.auth_jwt import AuthenticatedPrincipal
from api.routers.billing import (
    cancel_subscription,
    complete_checkout,
    get_billing_summary,
    list_plans,
    open_portal,
    start_checkout,
)
from api.schemas import CompleteCheckoutBody, StartCheckoutBody
from services.subscription_service import SubscriptionService
from tests.conftest import TEST_USER


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user=TEST_USER, access_token="test-token")


@pytest.fixture
def billing_env(isolated_env, monkeypatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setattr("config.PAYMENTS_ENABLED", True)
    monkeypatch.setattr("config.STRIPE_SECRET_KEY", "sk_test_example")
    return isolated_env


def test_list_plans_returns_catalog(isolated_env, principal):
    import config

    plans = list_plans(principal, TEST_USER)

    plan_ids = {plan.id for plan in plans}
    assert plan_ids == set(config.PLANS)
    billable = {plan.id for plan in plans if plan.billable}
    assert billable == set(config.BILLABLE_PLANS)


def test_summary_reports_disabled_when_unconfigured(isolated_env, principal):
    summary = get_billing_summary(principal, TEST_USER)

    assert summary.enabled is False
    assert summary.available_providers == []
    assert summary.effective_plan == "free"
    assert summary.usage.reports_limit == 5


def test_start_checkout_unconfigured_provider_errors(isolated_env, principal):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        start_checkout(
            StartCheckoutBody(plan_id="starter", provider="stripe"),
            principal,
            TEST_USER,
        )
    assert exc_info.value.status_code == 400


def test_start_checkout_happy_path(billing_env, principal, monkeypatch):
    monkeypatch.setattr(
        "services.billing_service.create_checkout_session",
        lambda **kwargs: "https://checkout.stripe.test/session",
    )

    result = start_checkout(
        StartCheckoutBody(plan_id="starter", provider="stripe"),
        principal,
        TEST_USER,
    )

    assert result.checkout_url == "https://checkout.stripe.test/session"


def test_complete_checkout_happy_path(billing_env, principal, monkeypatch):
    payload = {
        "user_id": TEST_USER.id,
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

    summary = complete_checkout(
        CompleteCheckoutBody(provider="stripe", session_id="cs_test"),
        principal,
        TEST_USER,
    )

    assert summary.billing_plan == "starter"
    assert summary.payment_provider == "stripe"
    assert summary.enabled is True


def test_open_portal_without_customer_errors(billing_env, principal):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        open_portal(principal, TEST_USER)
    assert exc_info.value.status_code == 400


def test_cancel_subscription_marks_cancel_at_period_end(isolated_env, principal):
    SubscriptionService(current_user=TEST_USER).activate_paid_plan(
        "starter", provider="stripe", customer_id="cus_1"
    )

    summary = cancel_subscription(principal, TEST_USER)

    assert summary.cancel_at_period_end is True
    assert summary.billing_plan == "starter"
