"""
Fail-closed project access checks for multi-tenant isolation.
"""

from __future__ import annotations

from core.current_user import CurrentUser, require_current_user
from core.workspace_context import is_quick_report


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


def require_real_project_uuid(project_id: str) -> str:
    """
    Reject Quick Report and other non-UUID workspace ids before PostgreSQL queries.
    """

    safe_project_id = validate_project_id(project_id)
    if is_quick_report(safe_project_id):
        raise ProjectAccessError(
            f"Quick Report is not a database project: {safe_project_id!r}"
        )
    return safe_project_id


def assert_project_access(
    project_id: str,
    *,
    current_user: CurrentUser | None = None,
    access_token: str | None = None,
) -> str:
    """
    Verify the authenticated user may access a project workspace.

    Fail closed: unknown, invalid, or foreign project ids are rejected.

    Pass ``current_user`` and ``access_token`` explicitly when calling from
    worker threads that do not inherit Streamlit session / ContextVar auth.
    """

    user = current_user or require_current_user()
    safe_project_id = validate_project_id(project_id)

    if is_quick_report(safe_project_id):
        return safe_project_id

    from services.project_service import ProjectService

    if not ProjectService(
        current_user=user,
        access_token=access_token,
    ).project_exists(safe_project_id):
        raise ProjectAccessError(f"Access denied to project: {safe_project_id!r}")

    return safe_project_id
