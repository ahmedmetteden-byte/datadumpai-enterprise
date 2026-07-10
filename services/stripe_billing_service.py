"""
Stripe Checkout and Customer Portal integration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import config

try:
    import stripe
except ImportError:  # pragma: no cover - optional until installed
    stripe = None  # type: ignore[assignment]


class StripeBillingError(Exception):
    """Raised when Stripe billing cannot be completed."""


def _require_stripe() -> None:
    if stripe is None:
        raise StripeBillingError("stripe package is not installed")
    if not config.is_stripe_configured():
        raise StripeBillingError("Stripe is not configured")


def _configure_stripe() -> None:
    _require_stripe()
    stripe.api_key = config.STRIPE_SECRET_KEY


def _stripe_price_id(plan_id: str) -> str:
    plan = config.resolve_plan_id(plan_id)
    if plan == "starter":
        return config.STRIPE_STARTER_PRICE_ID
    if plan == "professional":
        return config.STRIPE_PROFESSIONAL_PRICE_ID
    return ""


def _line_item(plan_id: str) -> dict[str, Any]:
    plan = config.resolve_plan_id(plan_id)
    price_id = _stripe_price_id(plan)
    if price_id:
        return {"price": price_id, "quantity": 1}

    amounts = config.PLAN_PRICES.get(plan)
    if not amounts:
        raise StripeBillingError(f"No Stripe price configured for plan {plan_id!r}")

    plan_meta = config.PLANS[plan]
    return {
        "price_data": {
            "currency": "usd",
            "unit_amount": amounts["stripe_amount_cents"],
            "recurring": {"interval": "month"},
            "product_data": {
                "name": f"DataDumpAI {plan_meta['label']}",
                "description": plan_meta.get("tagline", ""),
            },
        },
        "quantity": 1,
    }


def create_checkout_session(
    *,
    user_id: str,
    email: str,
    plan_id: str,
) -> str:
    """Return Stripe Checkout URL for a subscription."""

    _configure_stripe()
    plan = config.resolve_plan_id(plan_id)
    if plan not in config.BILLABLE_PLANS:
        raise StripeBillingError(f"Plan {plan_id!r} is not billable via Stripe")

    success_url = (
        f"{config.BILLING_SUCCESS_URL.rstrip('/')}"
        "?billing=success&provider=stripe&session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = f"{config.BILLING_CANCEL_URL.rstrip('/')}?billing=canceled"

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[_line_item(plan)],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=user_id,
        metadata={"user_id": user_id, "plan_id": plan},
        subscription_data={"metadata": {"user_id": user_id, "plan_id": plan}},
    )

    if not session.url:
        raise StripeBillingError("Stripe did not return a checkout URL")
    return session.url


def verify_checkout_session(session_id: str) -> dict[str, Any]:
    """Verify a completed Checkout session and return activation payload."""

    _configure_stripe()
    session = stripe.checkout.Session.retrieve(
        session_id,
        expand=["subscription", "customer"],
    )

    if session.payment_status != "paid" and session.status != "complete":
        raise StripeBillingError("Checkout session is not paid")

    subscription = session.subscription
    if isinstance(subscription, str):
        subscription = stripe.Subscription.retrieve(subscription)

    customer_id = session.customer
    if hasattr(customer_id, "id"):
        customer_id = customer_id.id

    plan_id = (session.metadata or {}).get("plan_id") or config.DEFAULT_PLAN
    user_id = (session.metadata or {}).get("user_id") or session.client_reference_id

    period_end = None
    if subscription and getattr(subscription, "current_period_end", None):
        period_end = datetime.fromtimestamp(
            subscription.current_period_end,
            tz=timezone.utc,
        ).isoformat()

    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "provider": "stripe",
        "customer_id": customer_id,
        "subscription_id": subscription.id if subscription else None,
        "reference": session_id,
        "current_period_end": period_end,
    }


def create_customer_portal_session(*, customer_id: str) -> str:
    _configure_stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=config.BILLING_SUCCESS_URL,
    )
    if not session.url:
        raise StripeBillingError("Stripe did not return a portal URL")
    return session.url


def cancel_subscription_at_period_end(subscription_id: str) -> None:
    _configure_stripe()
    stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)


def construct_webhook_event(payload: bytes, signature: str) -> Any:
    _require_stripe()
    if not config.STRIPE_WEBHOOK_SECRET:
        raise StripeBillingError("STRIPE_WEBHOOK_SECRET is not configured")
    return stripe.Webhook.construct_event(
        payload,
        signature,
        config.STRIPE_WEBHOOK_SECRET,
    )
