#!/usr/bin/env python3
"""
Check that Supabase automated backups are enabled and recent, using the
Supabase Management API's read-only backups-list endpoint.

This script is deliberately read-only. It never calls Supabase's
restore/PITR endpoints (POST .../database/backups/restore-pitr) — those
are destructive (Supabase's own docs describe restore-pitr as
experimental and it restores in place, into the *same* project, with no
option to target a new one via the API). The safe way to actually drill
a restore is the dashboard's "Restore to a New Project" feature, which
is not exposed by the Management API at all — see the "Backup / restore
readiness" section in PRODUCTION.md for that manual runbook. This script
only answers "is there a recent, healthy backup to restore *from*", not
"does restoring actually work" — only a real drill (dashboard, off a
non-production project) answers that.

Usage:
    python scripts/check_supabase_backups.py
    python scripts/check_supabase_backups.py --max-age-hours 48
    python scripts/check_supabase_backups.py --json

Requires:
    SUPABASE_ACCESS_TOKEN   Personal access token for the Management API
                            (Supabase dashboard -> Account -> Access Tokens).
                            Distinct from SUPABASE_SERVICE_ROLE_KEY, which
                            has no access to this API.
    SUPABASE_PROJECT_REF    The project ref (the subdomain in
                             https://<ref>.supabase.co), e.g. abcdefghijklmnop.

Exit codes:
    0   Backups are healthy (PITR or a recent completed backup exists)
    1   Backups are stale, missing, failed, or PITR is disabled
    2   Could not check (missing config, network error, bad response)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import requests  # noqa: E402

MANAGEMENT_API_BASE_URL = "https://api.supabase.com"
DEFAULT_MAX_AGE_HOURS = 26  # daily backups + buffer for a slow/delayed run


class BackupCheckError(Exception):
    """Raised when the check can't be completed (config/network/response)."""


def fetch_backups(project_ref: str, access_token: str) -> dict[str, Any]:
    try:
        response = requests.get(
            f"{MANAGEMENT_API_BASE_URL}/v1/projects/{project_ref}/database/backups",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise BackupCheckError(f"Could not reach Supabase Management API: {exc}") from exc

    if not response.ok:
        raise BackupCheckError(
            f"Supabase Management API returned {response.status_code}: {response.text[:300]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise BackupCheckError("Supabase Management API returned a non-JSON response") from exc


def evaluate(payload: dict[str, Any], *, max_age_hours: int) -> dict[str, Any]:
    """Turn a raw backups-list response into a healthy/unhealthy verdict.

    Pure function of the parsed response (no I/O) so the decision logic is
    testable against fixture payloads without a live Supabase project.
    """

    problems: list[str] = []

    pitr_enabled = bool(payload.get("pitr_enabled"))
    if not pitr_enabled:
        problems.append("Point-in-time recovery (PITR) is not enabled on this project.")

    backups = payload.get("backups") or []
    completed = [b for b in backups if b.get("status") == "COMPLETED"]
    failed = [b for b in backups if b.get("status") not in {"COMPLETED", None} and b.get("status")]

    if failed:
        statuses = ", ".join(sorted({b.get("status", "") for b in failed}))
        problems.append(f"{len(failed)} backup(s) in a non-completed state ({statuses}).")

    latest_completed_at: datetime | None = None
    if completed:
        timestamps = []
        for backup in completed:
            raw = backup.get("inserted_at")
            if not raw:
                continue
            try:
                timestamps.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
            except ValueError:
                continue
        if timestamps:
            latest_completed_at = max(timestamps)

    physical = payload.get("physical_backup_data") or {}
    latest_physical_unix = physical.get("latest_physical_backup_date_unix")
    if latest_physical_unix:
        physical_dt = datetime.fromtimestamp(latest_physical_unix, tz=timezone.utc)
        if latest_completed_at is None or physical_dt > latest_completed_at:
            latest_completed_at = physical_dt

    if latest_completed_at is None:
        problems.append("No completed backup was found.")
    else:
        age_hours = (datetime.now(timezone.utc) - latest_completed_at).total_seconds() / 3600
        if age_hours > max_age_hours:
            problems.append(
                f"Most recent completed backup is {age_hours:.1f}h old "
                f"(threshold: {max_age_hours}h)."
            )

    return {
        "healthy": not problems,
        "problems": problems,
        "pitr_enabled": pitr_enabled,
        "backup_count": len(backups),
        "latest_completed_at": latest_completed_at.isoformat() if latest_completed_at else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=DEFAULT_MAX_AGE_HOURS,
        help=f"Flag the most recent backup as stale past this age (default: {DEFAULT_MAX_AGE_HOURS})",
    )
    parser.add_argument("--project-ref", default=None, help="Override SUPABASE_PROJECT_REF")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of text")
    args = parser.parse_args()

    project_ref = args.project_ref or os.getenv("SUPABASE_PROJECT_REF", "").strip()
    access_token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()

    if not project_ref or not access_token:
        print(
            "This script requires SUPABASE_PROJECT_REF and SUPABASE_ACCESS_TOKEN "
            "(a Management API personal access token — see script docstring)."
        )
        return 2

    try:
        payload = fetch_backups(project_ref, access_token)
    except BackupCheckError as exc:
        print(f"ERROR: {exc}")
        return 2

    result = evaluate(payload, max_age_hours=args.max_age_hours)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["healthy"]:
        print(
            f"OK — {result['backup_count']} backup(s), PITR enabled={result['pitr_enabled']}, "
            f"most recent completed backup: {result['latest_completed_at']}"
        )
    else:
        print("UNHEALTHY:")
        for problem in result["problems"]:
            print(f"  - {problem}")

    return 0 if result["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
