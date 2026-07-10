"""
Tests for UI formatting helpers.
"""

from __future__ import annotations

from ui.formatting import (
    file_type_info,
    format_file_size,
    format_relative_time,
    format_report_timestamp,
)


def test_format_file_size():
    assert format_file_size(25) == "25 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(25600) == "25 KB"


def test_file_type_info():
    assert file_type_info("Minutes.pdf") == ("PDF", "📄", "🔴")
    assert file_type_info("notes.docx")[0] == "DOCX"


def test_format_relative_time_empty():
    assert format_relative_time("") == "—"


def test_format_report_timestamp_recent():
    from datetime import datetime, timedelta, timezone

    two_hours_ago = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()

    label = format_report_timestamp(two_hours_ago)

    assert label.startswith("Generated ")
    assert "hour" in label


def test_format_report_timestamp_yesterday():
    from datetime import datetime, timedelta, timezone

    yesterday = (
        datetime.now(timezone.utc) - timedelta(days=1, hours=2)
    ).isoformat()

    assert format_report_timestamp(yesterday) == "Yesterday"
