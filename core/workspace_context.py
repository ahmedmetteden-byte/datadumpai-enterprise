"""
Workspace context — Quick Report vs user-created projects.
"""

from __future__ import annotations

from datetime import datetime, timezone

QUICK_REPORT_PROJECT_ID = "__quick_report__"
QUICK_REPORT_NAME = "Quick Report"
PROJECT_MODE_LABEL = "Project"

WORKSPACE_MODE_QUICK = "quick_report"
WORKSPACE_MODE_PROJECT = "project"


def is_quick_report_workspace(workspace_id: str | None) -> bool:
    return workspace_id == QUICK_REPORT_PROJECT_ID


def build_pending_project_record() -> dict:
    """Placeholder workspace shown before the user creates a project."""

    return {
        "id": "",
        "name": PROJECT_MODE_LABEL,
        "is_quick_report": False,
        "is_pending": True,
        "documents": [],
        "reports": [],
    }


def build_quick_report_record() -> dict:
    """Virtual project record for the Quick Report workspace."""

    now = datetime.now(timezone.utc).isoformat()

    return {
        "id": QUICK_REPORT_PROJECT_ID,
        "name": QUICK_REPORT_NAME,
        "is_quick_report": True,
        "created_at": now,
        "updated_at": now,
        "last_activity": now,
        "documents": [],
        "reports": [],
        "exports": [],
        "storage_used": 0,
    }
