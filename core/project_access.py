"""
Fail-closed project access checks for multi-tenant isolation.
"""

from __future__ import annotations

from core.current_user import require_current_user
from core.workspace_context import is_quick_report_workspace


class ProjectAccessError(PermissionError):
    """Raised when a project cannot be accessed by the current user."""


def validate_project_id(project_id: str) -> str:
    """Reject path traversal and empty project identifiers."""

    if not project_id or not isinstance(project_id, str):
        raise ProjectAccessError("Project id is required.")

    cleaned = project_id.strip()
    if not cleaned:
        raise ProjectAccessError("Project id is required.")

    if cleaned in {".", ".."}:
        raise ProjectAccessError(f"Invalid project id: {project_id!r}")

    if any(token in cleaned for token in ("/", "\\", "..")):
        raise ProjectAccessError(f"Invalid project id: {project_id!r}")

    return cleaned


def assert_project_access(project_id: str) -> str:
    """
    Verify the authenticated user may access a project workspace.

    Fail closed: unknown, invalid, or foreign project ids are rejected.
    """

    require_current_user()
    safe_project_id = validate_project_id(project_id)

    if is_quick_report_workspace(safe_project_id):
        return safe_project_id

    from services.project_service import ProjectService

    if not ProjectService().project_exists(safe_project_id):
        raise ProjectAccessError(f"Access denied to project: {safe_project_id!r}")

    return safe_project_id
