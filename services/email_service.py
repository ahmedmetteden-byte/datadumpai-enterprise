"""
Outbound email delivery — SMTP or Resend API.
"""

from __future__ import annotations

import json
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

import requests

import config


class EmailDeliveryError(Exception):
    """Raised when an email cannot be sent."""


def is_email_configured() -> bool:
    if not config.EMAIL_ENABLED:
        return False
    if config.RESEND_API_KEY:
        return True
    return bool(config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD)


def send_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> str:
    """Send an email. Returns provider id: resend, smtp, or skipped."""

    if not config.EMAIL_ENABLED:
        return "skipped"

    if not to_email.strip():
        raise EmailDeliveryError("Recipient email is required")

    if config.RESEND_API_KEY:
        return _send_via_resend(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    if config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD:
        return _send_via_smtp(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    raise EmailDeliveryError(
        "Email is enabled but no provider is configured. "
        "Set RESEND_API_KEY or SMTP_HOST/SMTP_USER/SMTP_PASSWORD."
    )


def _send_via_resend(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None,
) -> str:
    payload: dict[str, Any] = {
        "from": f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM}>",
        "to": [to_email],
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {config.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=20,
    )

    if not response.ok:
        raise EmailDeliveryError(response.text or "Resend request failed")

    return "resend"


def _send_via_smtp(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None,
) -> str:
    message = EmailMessage()
    message["From"] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body_text)
    if body_html:
        message.add_alternative(body_html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
        if config.SMTP_USE_TLS:
            server.starttls(context=context)
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(message)

    return "smtp"
