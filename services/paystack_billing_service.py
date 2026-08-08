"""
Paystack payment initialization and verification.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

import config


class PaystackBillingError(Exception):
    """Raised when Paystack billing cannot be completed."""


PAYSTACK_BASE_URL = "https://api.paystack.co"


def _headers() -> dict[str, str]:
    if not config.is_paystack_configured():
        raise PaystackBillingError("Paystack is not configured")
    return {
        "Authorization": f"Bearer {config.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _plan_amount_kobo(plan_id: str) -> int:
    plan = config.resolve_plan_id(plan_id)
    amounts = config.PLAN_PRICES.get(plan)
    if not amounts:
        raise PaystackBillingError(f"No Paystack amount configured for plan {plan_id!r}")
    return int(amounts["paystack_amount_kobo"])


def _plan_code(plan_id: str) -> str:
    plan = config.resolve_plan_id(plan_id)
    if plan == "starter":
        return config.PAYSTACK_STARTER_PLAN_CODE
    if plan == "professional":
        return config.PAYSTACK_PROFESSIONAL_PLAN_CODE
    return ""


def _call_paystack(
    method: str, path: str, *, json_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call a Paystack endpoint and return its `data` payload.

    Wraps every failure mode — network errors, timeouts, non-2xx statuses,
    and malformed/empty response bodies — in PaystackBillingError, so a
    Paystack-side hiccup surfaces as a clean checkout error instead of an
    unhandled exception leaking through the API as a raw 500.
    """

    try:
        response = requests.request(
            method,
            f"{PAYSTACK_BASE_URL}{path}",
            json=json_body,
            headers=_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise PaystackBillingError(
            "Could not reach Paystack. Please try again."
        ) from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise PaystackBillingError(
            "Paystack returned an unexpected response. Please try again."
        ) from exc

    if not response.ok or not body.get("status"):
        message = body.get("message", "Paystack request failed")
        raise PaystackBillingError(message)

    data = body.get("data")
    if not isinstance(data, dict):
        raise PaystackBillingError("Paystack response was missing expected data.")

    return data


def initialize_transaction(
    *,
    user_id: str,
    email: str,
    plan_id: str,
) -> str:
    """Return Paystack authorization URL for the first subscription payment."""

    plan = config.resolve_plan_id(plan_id)
    if plan not in config.BILLABLE_PLANS:
        raise PaystackBillingError(f"Plan {plan_id!r} is not billable via Paystack")

    # Paystack appends its own `reference`/`trxref` query params to whatever
    # callback_url is given when it redirects the customer back — don't add
    # a literal, unsubstituted "{reference}" placeholder here (that isn't an
    # f-string interpolation since Paystack fills it in, not Python).
    callback_url = (
        f"{config.BILLING_SUCCESS_URL.rstrip('/')}"
        "?billing=success&provider=paystack"
    )

    payload: dict[str, Any] = {
        "email": email,
        "amount": _plan_amount_kobo(plan),
        "currency": "NGN",
        "callback_url": callback_url,
        "metadata": {
            "user_id": user_id,
            "plan_id": plan,
        },
    }

    plan_code = _plan_code(plan)
    if plan_code:
        payload["plan"] = plan_code

    data = _call_paystack("POST", "/transaction/initialize", json_body=payload)
    authorization_url = data.get("authorization_url")
    if not authorization_url:
        raise PaystackBillingError("Paystack did not return an authorization URL")
    return authorization_url


def verify_transaction(reference: str) -> dict[str, Any]:
    """Verify a Paystack transaction and return activation payload."""

    data = _call_paystack("GET", f"/transaction/verify/{reference}")
    if data.get("status") != "success":
        raise PaystackBillingError("Paystack payment was not successful")

    metadata = data.get("metadata") or {}
    plan_id = metadata.get("plan_id") or config.DEFAULT_PLAN
    user_id = metadata.get("user_id")

    customer = data.get("customer") or {}
    customer_id = str(customer.get("id") or customer.get("customer_code") or "")
    subscription_code = None
    authorization = data.get("authorization") or {}
    if data.get("plan"):
        subscription_code = str(data["plan"])

    period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "provider": "paystack",
        "customer_id": customer_id or None,
        "subscription_id": subscription_code,
        "reference": reference,
        "current_period_end": period_end,
    }


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    import hashlib
    import hmac

    if not config.is_paystack_configured():
        return False

    digest = hmac.new(
        config.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)
