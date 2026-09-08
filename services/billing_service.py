"""
Unified billing facade — Stripe (international) and Paystack (Nigeria).
"""

from __future__ import annotations

from typing import Literal

import config
from core.current_user import require_current_user
from services.paystack_billing_service import (
    PaystackBillingError,
    disable_subscription as paystack_disable_subscription,
    fetch_active_subscription as paystack_fetch_active_subscription,
    initialize_transaction as paystack_initialize,
    verify_transaction as paystack_verify,
)
from services.stripe_billing_service import (
    StripeBillingError,
    cancel_subscription_at_period_end,
    create_customer_portal_session,
)
from services.subscription_service import SubscriptionService

PaymentProvider = Literal["stripe", "paystack"]


class BillingService:
    """Checkout, portal, and subscription activation for the active user."""

    def __init__(self, *, access_token: str | None = None) -> None:
        self._current_user = require_current_user()
        self._user_id = self._current_user.id
        self._access_token = access_token
        self._subscription = SubscriptionService(
            current_user=self._current_user, access_token=access_token
        )

    @staticmethod
    def is_enabled() -> bool:
        return config.PAYMENTS_ENABLED and config.is_paystack_configured()

    @staticmethod
    def available_providers() -> list[PaymentProvider]:
        # Stripe is never offered, regardless of whether STRIPE_SECRET_KEY
        # happens to hold a value in the environment (e.g. a leftover
        # placeholder) — Stripe cannot be used by this account (business is
        # registered in Nigeria, which Stripe does not support), so it must
        # never be selectable, not just hidden when properly configured.
        if config.is_paystack_configured():
            return ["paystack"]
        return []

    def _user_email(self) -> str:
        if not self._current_user.email:
            raise ValueError("Signed-in user email is required for checkout")
        return self._current_user.email

    def start_checkout(self, plan_id: str, *, provider: PaymentProvider) -> str:
        plan = config.resolve_plan_id(plan_id)
        if plan not in config.BILLABLE_PLANS:
            raise ValueError(f"Plan {plan_id!r} cannot be purchased online")

        # Reject "stripe" outright rather than attempting the Stripe call —
        # it must never be reachable here even if a stale/placeholder
        # STRIPE_SECRET_KEY makes is_stripe_configured() look true. See
        # available_providers() for why.
        if provider == "stripe":
            raise ValueError("Stripe checkout is not available for this account.")

        email = self._user_email()
        return paystack_initialize(
            user_id=self._user_id,
            email=email,
            plan_id=plan,
        )

    def complete_checkout(
        self,
        *,
        provider: PaymentProvider,
        session_id: str | None = None,
        reference: str | None = None,
    ) -> dict:
        if provider == "stripe":
            raise ValueError("Stripe checkout is not available for this account.")
        if not reference:
            raise ValueError("reference is required for Paystack checkout")
        payload = paystack_verify(reference)

        if payload.get("user_id") and payload["user_id"] != self._user_id:
            raise ValueError("Checkout session does not belong to the current user")

        return self._subscription.activate_paid_plan(
            payload["plan_id"],
            provider=payload["provider"],
            customer_id=payload.get("customer_id"),
            subscription_id=payload.get("subscription_id"),
            reference=payload.get("reference"),
            current_period_end=payload.get("current_period_end"),
        )

    def open_customer_portal(self) -> str:
        summary = self._subscription.get_billing_summary()
        customer_id = summary.get("payment_customer_id")
        if not customer_id:
            raise ValueError("No Stripe customer on file")
        if summary.get("payment_provider") != "stripe":
            raise ValueError("Billing portal is only available for Stripe subscriptions")
        return create_customer_portal_session(customer_id=customer_id)

    def cancel_at_period_end(self) -> dict:
        state = self._subscription.load_state()
        provider = state.get("payment_provider")

        if provider == "stripe":
            subscription_id = state.get("payment_subscription_id")
            if subscription_id:
                cancel_subscription_at_period_end(subscription_id)
        elif provider == "paystack":
            self._disable_paystack_subscription(state)

        return self._subscription.mark_canceled(at_period_end=True)

    def _disable_paystack_subscription(self, state: dict) -> None:
        """Actually stop Paystack's recurring billing for this
        subscription — not just flip local status. Paystack requires the
        subscription's own code + email_token (never derivable from
        anything else this app stores); see paystack_billing_service.py
        for why. Prefers whatever the subscription.create webhook already
        persisted; falls back to a live Paystack lookup for a subscription
        created before that webhook was handled, or requested to cancel
        within seconds of checkout (before the webhook has arrived).
        """

        code = state.get("paystack_subscription_code")
        token = state.get("paystack_subscription_token")

        if not (code and token):
            customer_id = state.get("payment_customer_id") or ""
            fetched = paystack_fetch_active_subscription(customer_id)
            if fetched:
                code, token = fetched["code"], fetched["token"]

        if not (code and token):
            raise ValueError(
                "We could not find your Paystack subscription details to "
                "cancel automatically. Please contact support so we can "
                "cancel it for you."
            )

        paystack_disable_subscription(code=code, token=token)

    def get_summary(self) -> dict:
        return self._subscription.get_billing_summary()


def activate_subscription_for_user(
    user_id: str, payload: dict, *, use_service_role: bool = True
) -> dict:
    """Webhook helper — activate plan for a specific user."""

    subscription = SubscriptionService.for_user_id(
        user_id, use_service_role=use_service_role
    )
    return subscription.activate_paid_plan(
        payload["plan_id"],
        provider=payload["provider"],
        customer_id=payload.get("customer_id"),
        subscription_id=payload.get("subscription_id"),
        reference=payload.get("reference"),
        current_period_end=payload.get("current_period_end"),
    )


__all__ = [
    "BillingService",
    "PaystackBillingError",
    "StripeBillingError",
    "activate_subscription_for_user",
]
