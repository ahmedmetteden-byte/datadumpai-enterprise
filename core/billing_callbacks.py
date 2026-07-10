"""
Handle billing return URLs in the Streamlit app (query params).
"""

from __future__ import annotations

import streamlit as st

from services.billing_service import BillingService, PaystackBillingError, StripeBillingError


def handle_billing_return() -> None:
    """Process Stripe/Paystack success or cancel redirects once per visit."""

    params = st.query_params
    billing = params.get("billing")
    if not billing:
        return

    if billing == "canceled":
        st.session_state["billing_message"] = ("info", "Checkout canceled. No charges were made.")
        _clear_billing_params()
        return

    if billing != "success":
        return

    if st.session_state.get("billing_return_handled"):
        return

    provider = params.get("provider", "stripe")
    billing_service = BillingService()

    try:
        if provider == "stripe":
            session_id = params.get("session_id")
            billing_service.complete_checkout(provider="stripe", session_id=session_id)
        else:
            reference = params.get("reference") or params.get("trxref")
            billing_service.complete_checkout(provider="paystack", reference=reference)

        st.session_state["billing_message"] = (
            "success",
            "Payment successful — your plan is now active.",
        )
    except (StripeBillingError, PaystackBillingError, ValueError) as exc:
        st.session_state["billing_message"] = ("error", str(exc))
    finally:
        st.session_state["billing_return_handled"] = True
        _clear_billing_params()


def render_billing_message() -> None:
    message = st.session_state.pop("billing_message", None)
    if not message:
        return

    level, text = message
    if level == "success":
        st.success(text)
    elif level == "error":
        st.error(text)
    else:
        st.info(text)


def _clear_billing_params() -> None:
    for key in ("billing", "provider", "session_id", "reference", "trxref"):
        if key in st.query_params:
            del st.query_params[key]
