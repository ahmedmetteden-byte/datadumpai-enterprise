"""
Billing UI — upgrade, manage subscription, provider selection.
"""

from __future__ import annotations

import streamlit as st

import config
from config import BILLABLE_PLANS, PLANS
from core.billing_callbacks import render_billing_message
from services.billing_service import BillingService, PaystackBillingError, StripeBillingError
from services.usage_service import UsageService


def render_billing_section() -> None:
    render_billing_message()

    billing = BillingService()
    summary = billing.get_summary()
    usage = UsageService().get_snapshot()

    st.markdown("### Subscription")

    plan_meta = PLANS.get(summary["effective_plan"], PLANS["free"])
    st.markdown(f"**Current plan:** {plan_meta['label']}")

    status = summary.get("subscription_status", "none")
    if status == "active":
        st.success("Active paid subscription")
        provider = summary.get("payment_provider")
        if provider:
            st.caption(f"Billed via {provider.title()}")
        if summary.get("current_period_end"):
            st.caption(f"Current period ends: {summary['current_period_end']}")
        if summary.get("cancel_at_period_end"):
            st.warning("Cancellation scheduled at end of billing period.")
    elif usage.is_trialing:
        days = summary.get("trial_days_remaining")
        st.info(
            f"Professional trial — {days} day{'s' if days != 1 else ''} remaining. "
            "Upgrade anytime to keep full access."
        )
    elif status == "past_due":
        st.error("Payment failed. Update your billing details to restore access.")
    else:
        st.caption("You are on the Free plan.")

    if not BillingService.is_enabled():
        st.info(
            "Online payments are not configured. Set `PAYMENTS_ENABLED=true` and add "
            "Stripe or Paystack keys in your environment to enable checkout."
        )
        return

    providers = BillingService.available_providers()
    if not providers:
        st.warning("No payment providers are configured.")
        return

    st.divider()
    st.markdown("### Upgrade")

    default_provider = providers[0]
    if len(providers) > 1:
        provider_labels = {
            "stripe": "International (Stripe · USD)",
            "paystack": "Nigeria (Paystack · NGN)",
        }
        provider = st.radio(
            "Payment method",
            options=providers,
            format_func=lambda value: provider_labels.get(value, value.title()),
            horizontal=True,
        )
    else:
        provider = default_provider
        st.caption(
            "International (Stripe)"
            if provider == "stripe"
            else "Nigeria (Paystack)"
        )

    cols = st.columns(len(BILLABLE_PLANS))
    for col, plan_id in zip(cols, BILLABLE_PLANS):
        meta = PLANS[plan_id]
        with col:
            st.markdown(f"**{meta['label']}**")
            st.caption(meta.get("tagline", ""))
            price = meta.get("price_label", "")
            if price:
                st.markdown(price)

            if summary["effective_plan"] == plan_id and status == "active":
                st.success("Current plan")
            elif st.button(
                f"Upgrade to {meta['label']}",
                key=f"billing_upgrade_{plan_id}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    url = billing.start_checkout(plan_id, provider=provider)
                    st.link_button(
                        "Continue to secure checkout",
                        url,
                        type="primary",
                        use_container_width=True,
                    )
                    st.caption("Opens Stripe or Paystack in a new tab.")
                except (StripeBillingError, PaystackBillingError, ValueError) as exc:
                    st.error(str(exc))

    if (
        status == "active"
        and summary.get("payment_provider") == "stripe"
        and summary.get("payment_customer_id")
    ):
        st.divider()
        st.markdown("### Manage billing")
        if st.button("Open Stripe billing portal", type="secondary"):
            try:
                portal_url = billing.open_customer_portal()
                st.link_button("Manage subscription", portal_url)
            except (StripeBillingError, ValueError) as exc:
                st.error(str(exc))

        if not summary.get("cancel_at_period_end") and st.button(
            "Cancel at period end",
            type="secondary",
        ):
            try:
                billing.cancel_at_period_end()
                st.success("Subscription will cancel at the end of the billing period.")
                st.rerun()
            except (StripeBillingError, ValueError) as exc:
                st.error(str(exc))

    st.caption(
        "Enterprise plans include SSO, teams, and on-prem deployment. "
        "Contact sales for a custom quote."
    )
