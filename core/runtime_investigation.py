"""
Runtime investigation logging for tenant-isolation debugging.

Enable with RUNTIME_INVESTIGATION=true or DEBUG=true in the environment.
Logs append to data/runtime_investigation.log and print to stderr.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from config import (
    AUTH_DEV_BYPASS,
    DATABASE_BACKEND,
    DEBUG,
    DEV_USER_ID,
    ENVIRONMENT,
    STORAGE_BACKEND,
    auth_dev_bypass_enabled,
    is_supabase_configured,
)


_LOG_PATH = Path("data") / "runtime_investigation.log"


def investigation_enabled() -> bool:
    import os

    flag = os.getenv("RUNTIME_INVESTIGATION", "").lower() in {"1", "true", "yes"}
    return flag or DEBUG


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_log(event: str, payload: dict[str, Any]) -> None:
    if not investigation_enabled():
        return

    entry = {
        "timestamp": _utc_now(),
        "event": event,
        **payload,
    }

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str) + "\n")

    print(f"[RUNTIME_INVESTIGATION] {event}", file=sys.stderr)
    for key, value in payload.items():
        print(f"  {key}: {value}", file=sys.stderr)


def auth_provider_label() -> str:
    if auth_dev_bypass_enabled():
        return "AUTH_DEV_BYPASS (development only — all users share DEV_USER_ID)"
    if is_supabase_configured():
        return "Supabase Auth"
    return "NONE (unconfigured)"


def storage_backend_label() -> str:
    if config.use_supabase_storage():
        return "supabase"
    return "JSON/local filesystem"


def database_backend_label() -> str:
    if config.use_database():
        return "supabase"
    return "JSON/local filesystem"


def user_storage_paths(user_id: str) -> dict[str, str]:
    from core.user_paths import get_user_projects_root
    from core.workspace_context import QUICK_REPORT_JSON_FOLDER

    projects_root = get_user_projects_root(user_id)
    quick_root = projects_root / QUICK_REPORT_JSON_FOLDER

    return {
        "workspace": str(projects_root),
        "project_root": str(projects_root),
        "quick_report": str(quick_root),
        "documents": str(quick_root / "documents"),
        "reports": str(quick_root / "reports"),
    }


def log_startup_configuration() -> list[str]:
    """Part 6 — print backend configuration on startup. Returns fatal messages."""

    payload = {
        "AUTH_DEV_BYPASS_REQUESTED": AUTH_DEV_BYPASS,
        "ENVIRONMENT": ENVIRONMENT,
        "auth_dev_bypass_enabled": auth_dev_bypass_enabled(),
        "DATABASE_BACKEND": DATABASE_BACKEND,
        "effective_database_backend": database_backend_label(),
        "STORAGE_BACKEND": STORAGE_BACKEND,
        "effective_storage_backend": storage_backend_label(),
        "authentication_provider": auth_provider_label(),
        "DEV_USER_ID": DEV_USER_ID,
        "supabase_configured": is_supabase_configured(),
        "DEBUG": DEBUG,
    }
    _write_log("startup.configuration", payload)

    fatals: list[str] = []
    if auth_dev_bypass_enabled() and not DEBUG:
        fatals.append(
            "RUNTIME INVESTIGATION: AUTH_DEV_BYPASS=true outside DEBUG mode. "
            "All sign-ins resolve to DEV_USER_ID and share one workspace. "
            "This is not safe for multi-user manual testing."
        )
    return fatals


def log_authenticated_user(
    *,
    action: str,
    user_id: str,
    email: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Part 1 — trace login, registration, logout."""

    paths = user_storage_paths(user_id)
    payload = {
        "action": action,
        "user_id": user_id,
        "email": email,
        "authentication_backend": auth_provider_label(),
        "storage_backend": storage_backend_label(),
        "workspace_path": paths["workspace"],
        "project_root": paths["project_root"],
        "quick_report_path": paths["quick_report"],
    }
    if extra:
        payload.update(extra)
    _write_log("auth.session", payload)


def log_registration_decision(
    *,
    raw_email: str,
    normalized_email: str,
    existing_user: bool,
    allowed: bool,
    reason: str,
    assigned_user_id: str | None = None,
) -> None:
    """Part 5 — trace duplicate-email registration decisions."""

    _write_log(
        "auth.registration",
        {
            "raw_email": raw_email,
            "normalized_email": normalized_email,
            "lookup_result": "exists" if existing_user else "not_found",
            "existing_user": existing_user,
            "registration_allowed": allowed,
            "reason": reason,
            "assigned_user_id": assigned_user_id,
            "AUTH_DEV_BYPASS": auth_dev_bypass_enabled(),
            "email_check_backend": database_backend_label(),
        },
    )


def log_project_load(
    *,
    user_id: str,
    project_count: int,
    project_ids: list[str],
    filesystem_root: str,
) -> None:
    """Part 4 — trace project loading before filtering."""

    _write_log(
        "data.projects",
        {
            "user_id": user_id,
            "filesystem_root": filesystem_root,
            "project_count": project_count,
            "project_ids": project_ids,
        },
    )


def log_document_load(
    *,
    user_id: str,
    project_id: str,
    filesystem_path: str,
    document_count: int,
    filenames: list[str],
) -> None:
    """Part 3 — trace document loading before filtering."""

    _write_log(
        "data.documents",
        {
            "user_id": user_id,
            "project_id": project_id,
            "filesystem_path": filesystem_path,
            "document_count": document_count,
            "filenames": filenames,
        },
    )


def log_report_load(
    *,
    user_id: str,
    project_id: str,
    filesystem_path: str,
    report_count: int,
    filenames: list[str],
) -> None:
    """Part 2 — trace report loading before filtering."""

    _write_log(
        "data.reports",
        {
            "user_id": user_id,
            "project_id": project_id,
            "filesystem_path": filesystem_path,
            "report_count": report_count,
            "filenames": filenames,
        },
    )


def log_identity_verification(
    *,
    user_a_id: str,
    user_b_id: str,
    user_a_email: str,
    user_b_email: str,
) -> None:
    """Part 7 — compare two authenticated identities."""

    _write_log(
        "verify.user_identity",
        {
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "user_a_email": user_a_email,
            "user_b_email": user_b_email,
            "ids_identical": user_a_id == user_b_id,
        },
    )


def log_storage_verification(
    *,
    user_a_id: str,
    user_b_id: str,
) -> None:
    """Part 8 — compare storage roots for two users."""

    paths_a = user_storage_paths(user_a_id)
    paths_b = user_storage_paths(user_b_id)

    _write_log(
        "verify.storage_paths",
        {
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "user_a_workspace": paths_a["workspace"],
            "user_b_workspace": paths_b["workspace"],
            "user_a_quick_report": paths_a["quick_report"],
            "user_b_quick_report": paths_b["quick_report"],
            "workspace_paths_identical": paths_a["workspace"] == paths_b["workspace"],
        },
    )
