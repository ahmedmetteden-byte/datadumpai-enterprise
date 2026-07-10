"""
DataDumpAI v1.0
Feedback and support request storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from storage.json_storage import JSONStorage

from services.feedback_delivery import deliver_feedback, deliver_support_request


class FeedbackService:
    """Persist user feedback and support messages locally."""

    def __init__(
        self,
        feedback_path: str = "data/feedback.json",
        support_path: str = "data/support_requests.json",
    ) -> None:
        self._feedback = JSONStorage(feedback_path)
        self._support = JSONStorage(support_path)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def submit_feedback(
        self,
        *,
        message: str,
        category: str = "general",
        email: str = "",
    ) -> dict[str, Any]:
        entry = {
            "id": str(uuid4()),
            "type": "feedback",
            "category": category.strip() or "general",
            "message": message.strip(),
            "email": email.strip(),
            "created_at": self._utc_now(),
        }

        items = self._feedback.load()
        items.append(entry)
        self._feedback.save(items)

        entry["delivery"] = deliver_feedback(entry)

        return entry

    def submit_support_request(
        self,
        *,
        name: str,
        email: str,
        subject: str,
        message: str,
    ) -> dict[str, Any]:
        entry = {
            "id": str(uuid4()),
            "type": "support",
            "name": name.strip(),
            "email": email.strip(),
            "subject": subject.strip(),
            "message": message.strip(),
            "created_at": self._utc_now(),
        }

        items = self._support.load()
        items.append(entry)
        self._support.save(items)

        entry["delivery"] = deliver_support_request(entry)

        return entry
