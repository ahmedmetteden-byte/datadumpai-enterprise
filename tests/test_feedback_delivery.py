"""
Tests for feedback delivery helpers.
"""

from __future__ import annotations

from services.feedback_delivery import build_mailto_link, feedback_mailto


def test_build_mailto_link_encodes_subject_and_body():
    link = build_mailto_link(
        to_email="feedback@datadumpai.com",
        subject="Hello World",
        body="Line one\nLine two",
    )

    assert link.startswith("mailto:feedback%40datadumpai.com?")
    assert "Hello%20World" in link
    assert "Line%20one" in link


def test_feedback_mailto_contains_message():
    link = feedback_mailto(
        {
            "category": "Bug report",
            "email": "user@example.com",
            "message": "Upload failed on PDF.",
        }
    )

    assert "Bug%20report" in link
    assert "Upload%20failed" in link
