#!/usr/bin/env python3
"""
Standalone runtime investigation for tenant isolation (Parts 5–8).

Run from repository root:
    python scripts/investigate_tenant_runtime.py

Does not modify data. Prints findings to stdout and appends to
data/runtime_investigation.log when RUNTIME_INVESTIGATION=true or DEBUG=true.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("RUNTIME_INVESTIGATION", "true")

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import config  # noqa: E402
from config import AUTH_DEV_BYPASS, DEV_USER_ID, is_supabase_configured  # noqa: E402
from core.runtime_investigation import (  # noqa: E402
    auth_provider_label,
    database_backend_label,
    log_identity_verification,
    log_registration_decision,
    log_startup_configuration,
    log_storage_verification,
    storage_backend_label,
    user_storage_paths,
)
from services.auth_service import AuthError, AuthService  # noqa: E402
from services.email_uniqueness import EmailUniquenessService, normalize_email  # noqa: E402


def _section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    _section("Part 6 — Backend configuration")
    fatals = log_startup_configuration()
    print(f"AUTH_DEV_BYPASS:        {AUTH_DEV_BYPASS}")
    print(f"DATABASE_BACKEND:       {config.DATABASE_BACKEND}")
    print(f"Effective DB backend:   {database_backend_label()}")
    print(f"STORAGE_BACKEND:        {config.STORAGE_BACKEND}")
    print(f"Effective storage:      {storage_backend_label()}")
    print(f"Authentication provider:{auth_provider_label()}")
    print(f"Supabase configured:    {is_supabase_configured()}")
    print(f"DEV_USER_ID:            {DEV_USER_ID}")
    for message in fatals:
        print(f"FATAL: {message}")

    _section("Part 7 — User identity (sign_in as User A and User B)")
    service = AuthService()
    session_a = service.sign_in("investigation-user-a@example.com", "password-a")
    session_b = service.sign_in("investigation-user-b@example.com", "password-b")

    print(f"User A ID:    {session_a.user.id}")
    print(f"User A Email: {session_a.user.email}")
    print(f"User B ID:    {session_b.user.id}")
    print(f"User B Email: {session_b.user.email}")
    print(f"IDs identical: {session_a.user.id == session_b.user.id}")

    log_identity_verification(
        user_a_id=session_a.user.id,
        user_b_id=session_b.user.id,
        user_a_email=session_a.user.email,
        user_b_email=session_b.user.email,
    )

    if session_a.user.id == session_b.user.id:
        print()
        print("STOP: User A and User B share the same authenticated user ID.")
        print("This is the root cause of shared workspace data during manual testing.")

    _section("Part 8 — Storage paths")
    paths_a = user_storage_paths(session_a.user.id)
    paths_b = user_storage_paths(session_b.user.id)

    print("User A")
    for key, value in paths_a.items():
        print(f"  {key}: {value}")
    print("User B")
    for key, value in paths_b.items():
        print(f"  {key}: {value}")
    print(f"Workspace paths identical: {paths_a['workspace'] == paths_b['workspace']}")

    log_storage_verification(
        user_a_id=session_a.user.id,
        user_b_id=session_b.user.id,
    )

    if paths_a["workspace"] == paths_b["workspace"]:
        print()
        print("STOP: User A and User B resolve to the same on-disk workspace.")
        print("This is the root cause of shared projects, documents, and reports.")

    _section("Part 5 — Duplicate email registration trace")
    probe_email = "investigation-duplicate@example.com"
    normalized = normalize_email(probe_email)
    exists_before = EmailUniquenessService().email_exists(normalized)
    print(f"Probe email: {probe_email!r}")
    print(f"Normalized:  {normalized!r}")
    print(f"Exists before signup: {exists_before}")

    try:
        signup = service.sign_up(probe_email, "password123", full_name="Probe User")
        allowed = True
        reason = "sign_up succeeded"
        assigned_id = signup.user.id if signup else None
    except AuthError as exc:
        allowed = False
        reason = str(exc)
        assigned_id = None

    log_registration_decision(
        raw_email=probe_email,
        normalized_email=normalized,
        existing_user=exists_before,
        allowed=allowed,
        reason=reason,
        assigned_user_id=assigned_id,
    )
    print(f"First sign_up allowed: {allowed} — {reason}")
    if assigned_id:
        print(f"Assigned user ID: {assigned_id}")

    exists_after = EmailUniquenessService().email_exists(normalized)
    print(f"Exists after first signup: {exists_after}")

    try:
        service.sign_up(probe_email, "password456", full_name="Duplicate Probe")
        duplicate_blocked = False
        duplicate_reason = "second sign_up succeeded (duplicate NOT blocked)"
    except AuthError as exc:
        duplicate_blocked = True
        duplicate_reason = str(exc)

    log_registration_decision(
        raw_email=probe_email,
        normalized_email=normalized,
        existing_user=exists_after,
        allowed=not duplicate_blocked,
        reason=duplicate_reason,
        assigned_user_id=DEV_USER_ID if AUTH_DEV_BYPASS else None,
    )
    print(f"Duplicate sign_up blocked: {duplicate_blocked} — {duplicate_reason}")

    _section("Sign-in vs sign-up behavior under current config")
    if AUTH_DEV_BYPASS:
        print("- sign_in() ignores email/password and always returns DEV_USER_ID.")
        print("- sign_up() stores email in registry but still assigns DEV_USER_ID.")
        print("- restore_session() / refresh_session() also revert to dev_sign_in().")
        print("- Manual testers using Sign In never hit duplicate-email checks.")
        print("- Two different emails on Sign In = same user ID = shared workspace.")

    print()
    print("Investigation log:", ROOT / "data" / "runtime_investigation.log")
    return 1 if session_a.user.id == session_b.user.id else 0


if __name__ == "__main__":
    raise SystemExit(main())
