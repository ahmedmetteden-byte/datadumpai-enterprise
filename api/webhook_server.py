"""
FastAPI webhook server for Stripe and Paystack subscription events.

Run separately from Streamlit:
    uvicorn api.webhook_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request

import config
from repositories.billing_repository import (
    find_user_id_by_customer_id,
    find_user_id_by_subscription_id,
)
from services.billing_service import activate_subscription_for_user
from services.paystack_billing_service import verify_webhook_signature
from services.stripe_billing_service import construct_webhook_event
from services.subscription_service import SubscriptionService

app = FastAPI(title="DataDumpAI Billing Webhooks", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata") or {}
        user_id = metadata.get("user_id") or data_object.get("client_reference_id")
        plan_id = metadata.get("plan_id")
        if user_id and plan_id:
            period_end = None
            subscription_id = data_object.get("subscription")
            activate_subscription_for_user(
                user_id,
                {
                    "plan_id": plan_id,
                    "provider": "stripe",
                    "customer_id": data_object.get("customer"),
                    "subscription_id": subscription_id,
                    "reference": data_object.get("id"),
                    "current_period_end": period_end,
                },
            )

    elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        subscription_id = data_object.get("id")
        user_id = (data_object.get("metadata") or {}).get("user_id")
        if not user_id:
            user_id = find_user_id_by_subscription_id(subscription_id)

        if user_id:
            subscription = SubscriptionService.for_user_id(user_id)
            status = data_object.get("status")
            if status == "active":
                plan_id = (data_object.get("metadata") or {}).get("plan_id")
                period_end = None
                if data_object.get("current_period_end"):
                    period_end = datetime.fromtimestamp(
                        data_object["current_period_end"],
                        tz=timezone.utc,
                    ).isoformat()
                if plan_id:
                    subscription.activate_paid_plan(
                        plan_id,
                        provider="stripe",
                        customer_id=data_object.get("customer"),
                        subscription_id=subscription_id,
                        current_period_end=period_end,
                    )
            elif status in {"canceled", "unpaid", "incomplete_expired"}:
                subscription.mark_canceled(at_period_end=False)
            elif status == "past_due":
                subscription.mark_payment_failed()

    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        user_id = find_user_id_by_customer_id(customer_id)
        if user_id:
            SubscriptionService.for_user_id(user_id).mark_payment_failed()
            try:
                from services.notification_service import NotificationService

                NotificationService.for_user_id(user_id).notify_billing_event(
                    subject="Payment failed — action required",
                    body=(
                        "We could not process your latest subscription payment. "
                        "Update your billing details to restore full access."
                    ),
                )
            except Exception:
                pass

    return {"received": "true"}


@app.post("/webhooks/paystack")
async def paystack_webhook(request: Request) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    event = json.loads(payload.decode("utf-8"))
    event_type = event.get("event")
    data = event.get("data") or {}

    if event_type == "charge.success":
        metadata = data.get("metadata") or {}
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan_id")
        if user_id and plan_id:
            customer = data.get("customer") or {}
            activate_subscription_for_user(
                user_id,
                {
                    "plan_id": plan_id,
                    "provider": "paystack",
                    "customer_id": str(customer.get("id") or customer.get("customer_code") or ""),
                    "subscription_id": str(data.get("plan") or ""),
                    "reference": data.get("reference"),
                    "current_period_end": None,
                },
            )

    elif event_type in {"subscription.disable", "subscription.not_renew"}:
        customer_id = str((data.get("customer") or {}).get("id") or "")
        user_id = find_user_id_by_customer_id(customer_id)
        if user_id:
            SubscriptionService.for_user_id(user_id).mark_canceled(at_period_end=False)

    return {"received": "true"}
