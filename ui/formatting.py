"""
Shared formatting helpers for the UI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


FILE_TYPE_LABELS: dict[str, tuple[str, str, str]] = {
    ".pdf": ("PDF", "📄", "🔴"),
    ".docx": ("DOCX", "📝", "🔵"),
    ".doc": ("DOC", "📝", "🔵"),
    ".xlsx": ("XLSX", "📊", "🟢"),
    ".xls": ("XLS", "📊", "🟢"),
    ".pptx": ("PPTX", "📽️", "🟠"),
    ".ppt": ("PPT", "📽️", "🟠"),
    ".csv": ("CSV", "📊", "🟢"),
    ".txt": ("TXT", "📃", "⚪"),
}


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024 * 1024:
        size_kb = size_bytes / 1024
        if size_kb < 10:
            return f"{size_kb:.1f} KB"
        return f"{size_kb:.0f} KB"

    return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_relative_time(value: str) -> str:
    if not value:
        return "—"

    try:
        timestamp = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value[:10]

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    seconds = int((now - timestamp).total_seconds())

    if seconds < 0:
        return "just now"
    if seconds < 45:
        return "just now"
    if seconds < 90:
        return "1 minute ago"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minutes ago"
    if seconds < 7200:
        return "1 hour ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hours ago"
    if seconds < 172800:
        return "yesterday"

    days = seconds // 86400
    if days < 14:
        return f"{days} days ago"

    return timestamp.strftime("%d %b %Y")


def format_report_timestamp(value: str) -> str:
    """Format a report created_at value for the Recent Reports list."""

    if not value:
        return "Generated recently"

    try:
        timestamp = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return "Generated recently"

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    seconds = int((now - timestamp).total_seconds())

    if seconds < 0:
        return "Generated just now"

    if seconds < 86400:
        relative = format_relative_time(value)
        if relative == "just now":
            return "Generated just now"
        return f"Generated {relative}"

    if seconds < 172800:
        return "Yesterday"

    if seconds < 7 * 86400:
        return timestamp.strftime("%A")

    return timestamp.strftime("%d %b %Y")


def file_type_info(filename: str) -> tuple[str, str, str]:
    suffix = Path(filename).suffix.lower()
    return FILE_TYPE_LABELS.get(suffix, ("FILE", "📎", "⚪"))
