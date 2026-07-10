"""
Unified billing facade — Stripe (international) and Paystack (Nigeria).
"""

from __future__ import annotations

from typing import Literal

import config
from core import auth
from services.paystack_billing_service import (
    PaystackBillingError,
    initialize_transaction as paystack_initialize,
    verify_transaction as paystack_verify,
)
from services.stripe_billing_service import (
    StripeBillingError,
    cancel_subscription_at_period_end,
    create_checkout_session,
    create_customer_portal_session,
    verify_checkout_session,
)
from services.subscription_service import SubscriptionService

PaymentProvider = Literal["stripe", "paystack"]


class BillingService:
    """Checkout, portal, and subscription activation for the active user."""

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id or auth.get_current_user_id()
        self._subscription = SubscriptionService(self._user_id)

    @staticmethod
    def is_enabled() -> bool:
        return config.PAYMENTS_ENABLED and (
            config.is_stripe_configured() or config.is_paystack_configured()
        )

    @staticmethod
    def available_providers() -> list[PaymentProvider]:
        providers: list[PaymentProvider] = []
        if config.is_stripe_configured():
            providers.append("stripe")
        if config.is_paystack_configured():
            providers.append("paystack")
        return providers

    def _user_email(self) -> str:
        user = auth.get_current_user()
        if user is None or not user.email:
            raise ValueError("Signed-in user email is required for checkout")
        return user.email

    def start_checkout(self, plan_id: str, *, provider: PaymentProvider) -> str:
        plan = config.resolve_plan_id(plan_id)
        if plan not in config.BILLABLE_PLANS:
            raise ValueError(f"Plan {plan_id!r} cannot be purchased online")

        email = self._user_email()

        if provider == "stripe":
            return create_checkout_session(
                user_id=self._user_id,
                email=email,
                plan_id=plan,
            )

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
            if not session_id:
                raise ValueError("session_id is required for Stripe checkout")
            payload = verify_checkout_session(session_id)
        else:
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
        summary = self._subscription.get_billing_summary()
        subscription_id = summary.get("payment_subscription_id")
        provider = summary.get("payment_provider")

        if provider == "stripe" and subscription_id:
            cancel_subscription_at_period_end(subscription_id)

        return self._subscription.mark_canceled(at_period_end=True)

    def get_summary(self) -> dict:
        return self._subscription.get_billing_summary()


def activate_subscription_for_user(user_id: str, payload: dict) -> dict:
    """Webhook helper — activate plan for a specific user."""

    subscription = SubscriptionService(user_id)
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
