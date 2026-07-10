"""
DataDumpAI v1.0
Feedback delivery — local storage plus optional webhook/email handoff.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from config import FEEDBACK_EMAIL, SUPPORT_EMAIL


class FeedbackDeliveryError(Exception):
    """Raised when feedback cannot be delivered."""


def build_mailto_link(
    *,
    to_email: str,
    subject: str,
    body: str,
) -> str:
    return (
        f"mailto:{quote(to_email)}"
        f"?subject={quote(subject)}"
        f"&body={quote(body)}"
    )


def deliver_feedback(entry: dict[str, Any]) -> str:
    """
    Deliver feedback to configured endpoints.

    Always persists locally before optional remote delivery.
    Returns a short status string for the UI.
    """

    webhook_url = os.getenv("FEEDBACK_WEBHOOK_URL", "").strip()

    if webhook_url:
        try:
            request = urllib.request.Request(
                webhook_url,
                data=json.dumps(entry).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(request, timeout=8)
            return "webhook"
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FeedbackDeliveryError(
                "Could not reach the feedback endpoint. "
                "Your message was saved locally — try email instead."
            ) from exc

    return "local"


def deliver_support_request(entry: dict[str, Any]) -> str:
    """Deliver a support request to a webhook when configured."""

    webhook_url = os.getenv(
        "SUPPORT_WEBHOOK_URL",
        os.getenv("FEEDBACK_WEBHOOK_URL", ""),
    ).strip()

    if webhook_url:
        try:
            request = urllib.request.Request(
                webhook_url,
                data=json.dumps(entry).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(request, timeout=8)
            return "webhook"
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FeedbackDeliveryError(
                "Could not reach the support endpoint. "
                "Your message was saved locally — try email instead."
            ) from exc

    return "local"


def feedback_mailto(entry: dict[str, Any]) -> str:
    subject = f"DataDumpAI Feedback — {entry.get('category', 'General')}"
    body = (
        f"Category: {entry.get('category', 'General')}\n"
        f"Email: {entry.get('email') or 'not provided'}\n\n"
        f"{entry.get('message', '')}"
    )
    return build_mailto_link(
        to_email=FEEDBACK_EMAIL,
        subject=subject,
        body=body,
    )


def support_mailto(entry: dict[str, Any]) -> str:
    subject = entry.get("subject", "DataDumpAI Support")
    body = (
        f"From: {entry.get('name', '')}\n"
        f"Email: {entry.get('email', '')}\n\n"
        f"{entry.get('message', '')}"
    )
    return build_mailto_link(
        to_email=SUPPORT_EMAIL,
        subject=subject,
        body=body,
    )
