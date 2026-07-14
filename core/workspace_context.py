"""
Workspace context — Quick Report vs user-created projects.
"""

from __future__ import annotations

from datetime import datetime, timezone

import config

# Session/UI sentinel for Quick Report workspace mode (not a PostgreSQL project id).
QUICK_REPORT_PROJECT_ID = "__quick_report__"
QUICK_REPORT_WORKSPACE_ID = QUICK_REPORT_PROJECT_ID

# Local JSON filesystem folder name (backward compatible).
QUICK_REPORT_JSON_FOLDER = "__quick_report__"

# Supabase Storage path segment — never used as a PostgreSQL UUID.
QUICK_REPORT_STORAGE_SCOPE = "quick_report"

QUICK_REPORT_NAME = "Quick Report"
PROJECT_MODE_LABEL = "Project"

WORKSPACE_MODE_QUICK = "quick_report"
WORKSPACE_MODE_PROJECT = "project"


def is_quick_report(project_id: str | None) -> bool:
    """Return True when the workspace id refers to Quick Report mode."""

    return project_id == QUICK_REPORT_WORKSPACE_ID


# Backward-compatible alias used by existing UI and services.
is_quick_report_workspace = is_quick_report


def quick_report_storage_scope() -> str:
    """
    Return the storage prefix for Quick Report blobs.

    JSON mode keeps the legacy ``__quick_report__`` folder name.
    Supabase mode uses a dedicated scope that is never sent to PostgreSQL.
    """

    if config.use_supabase_storage():
        return QUICK_REPORT_STORAGE_SCOPE
    return QUICK_REPORT_JSON_FOLDER


def resolve_storage_scope(project_id: str) -> str:
    """Map a workspace id to the filesystem or object-storage prefix."""

    if is_quick_report(project_id):
        return quick_report_storage_scope()
    return project_id


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
    """Virtual workspace record for Quick Report mode."""

    now = datetime.now(timezone.utc).isoformat()

    return {
        "id": QUICK_REPORT_WORKSPACE_ID,
        "name": QUICK_REPORT_NAME,
        "is_quick_report": True,
        "workspace_mode": WORKSPACE_MODE_QUICK,
        "created_at": now,
        "updated_at": now,
        "last_activity": now,
        "documents": [],
        "reports": [],
        "exports": [],
        "storage_used": 0,
    }
