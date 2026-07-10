"""
Unit tests for FeedbackService.
"""

from __future__ import annotations

from services.feedback_service import FeedbackService
from storage.json_storage import JSONStorage


def test_submit_feedback_persists(tmp_path):
    feedback_path = tmp_path / "feedback.json"
    support_path = tmp_path / "support.json"
    service = FeedbackService(
        feedback_path=str(feedback_path),
        support_path=str(support_path),
    )

    entry = service.submit_feedback(
        message="Love the report generator.",
        category="Feature request",
        email="user@example.com",
    )

    stored = JSONStorage(feedback_path).load()

    assert len(stored) == 1
    assert stored[0]["id"] == entry["id"]
    assert stored[0]["message"] == "Love the report generator."


def test_submit_support_request_persists(tmp_path):
    feedback_path = tmp_path / "feedback.json"
    support_path = tmp_path / "support.json"
    service = FeedbackService(
        feedback_path=str(feedback_path),
        support_path=str(support_path),
    )

    entry = service.submit_support_request(
        name="Ahmed",
        email="ahmed@example.com",
        subject="Billing question",
        message="How do I upgrade?",
    )

    stored = JSONStorage(support_path).load()

    assert len(stored) == 1
    assert stored[0]["subject"] == "Billing question"
    assert stored[0]["email"] == "ahmed@example.com"
    assert stored[0]["id"] == entry["id"]
