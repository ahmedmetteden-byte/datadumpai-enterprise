"""
Unauthenticated public routes — currently just the marketing site's
contact form. Deliberately has no auth dependency.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

import config
from fastapi import APIRouter, HTTPException, Request, status

from api.schemas import ContactRequestBody, ContactResponseOut
from services.email_service import EmailDeliveryError, send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["public"])

_RATE_LIMIT_WINDOW_SECONDS = 600
_RATE_LIMIT_MAX_REQUESTS = 5
_submission_log: dict[str, list[float]] = defaultdict(list)

_CONTACT_SUBJECT_LABELS = {
    "general": "General inquiry",
    "sales": "Sales inquiry",
    "support": "Support request",
    "partnership": "Partnership inquiry",
    "press": "Press inquiry",
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    recent = [ts for ts in _submission_log[ip] if ts > cutoff]
    recent.append(now)
    _submission_log[ip] = recent
    return len(recent) > _RATE_LIMIT_MAX_REQUESTS


@router.post("/contact", response_model=ContactResponseOut)
def submit_contact(body: ContactRequestBody, request: Request) -> ContactResponseOut:
    if body.honeypot:
        return ContactResponseOut(status="skipped")

    ip = _client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please try again later.",
        )

    if "@" not in body.email or len(body.email) > 254:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid email address.")

    subject_label = _CONTACT_SUBJECT_LABELS.get(body.subject, "General inquiry")
    subject = f"[Contact] {subject_label} from {body.first_name} {body.last_name}"
    body_lines = [
        f"Name: {body.first_name} {body.last_name}",
        f"Email: {body.email}",
    ]
    if body.company:
        body_lines.append(f"Company: {body.company}")
    body_lines.append(f"Subject: {subject_label}")
    body_lines.append("")
    body_lines.append(body.message)
    body_text = "\n".join(body_lines)

    try:
        result = send_email(
            to_email=config.SUPPORT_EMAIL,
            subject=subject,
            body_text=body_text,
        )
    except EmailDeliveryError as exc:
        # A misconfigured mail provider (EMAIL_ENABLED=true with no working
        # Resend/SMTP setup) is an ops problem, not something a public site
        # visitor caused — never surface it as a broken submit. Log loudly
        # so it's visible in server logs, but still report success.
        logger.error("Contact form email delivery failed: %s", exc)
        return ContactResponseOut(status="skipped")

    if result == "skipped":
        logger.info(
            "Contact form submission received (email not configured): from=%s subject=%s",
            body.email,
            subject_label,
        )
        return ContactResponseOut(status="skipped")

    return ContactResponseOut(status="sent")
