#!/usr/bin/env python3
"""
Migrate per-user JSON metadata into Supabase PostgreSQL.

Usage:
    DATABASE_BACKEND=supabase python scripts/migrate_json_to_supabase.py
    python scripts/migrate_json_to_supabase.py --user-id <uuid>

Requires:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import use_database  # noqa: E402
from repositories.json_project_repository import JsonProjectRepository  # noqa: E402
from repositories.json_timeline_repository import JsonTimelineRepository  # noqa: E402
from repositories.account_repository import (  # noqa: E402
    JsonProfileRepository,
    JsonUsageRepository,
)
from repositories.supabase_project_repository import SupabaseProjectRepository  # noqa: E402
from repositories.supabase_timeline_repository import SupabaseTimelineRepository  # noqa: E402
from repositories.account_repository import (  # noqa: E402
    SupabaseProfileRepository,
    SupabaseUsageRepository,
)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def _discover_user_ids(data_root: Path, user_id: str | None) -> list[str]:
    if user_id:
        return [user_id]

    users_root = data_root / "users"
    if not users_root.exists():
        return []

    return sorted(
        path.name
        for path in users_root.iterdir()
        if path.is_dir() and _is_uuid(path.name)
    )


def migrate_user(user_id: str, *, data_root: Path) -> None:
    user_root = data_root / "users" / user_id
    projects_json = user_root / "projects.json"

    if projects_json.exists():
        projects = JsonProjectRepository(user_id).all()
        if projects:
            SupabaseProjectRepository(user_id).save(projects)
            print(f"  projects: {len(projects)}")

        projects_root = user_root / "projects"
        for project in projects:
            timeline_json = projects_root / project["id"] / "timeline.json"
            if not timeline_json.exists():
                continue

            events = JsonTimelineRepository(
                project["id"],
                user_id=user_id,
                projects_root=projects_root,
            ).load()

            if events:
                SupabaseTimelineRepository(
                    project["id"],
                    user_id=user_id,
                ).replace_all(events)
                print(f"  timeline ({project['name']}): {len(events)} events")

    usage_json = user_root / "usage.json"
    if usage_json.exists():
        usage = json.loads(usage_json.read_text(encoding="utf-8"))
        SupabaseUsageRepository(
            user_id,
            default={
                "plan": "free",
                "period": usage.get("period", ""),
                "reports_generated": 0,
                "uploads": 0,
            },
        ).save(usage)
        print("  usage: migrated")

    profile_json = user_root / "profile.json"
    if profile_json.exists():
        profile = json.loads(profile_json.read_text(encoding="utf-8"))
        SupabaseProfileRepository(
            user_id,
            default={
                "full_name": "",
                "company": "",
                "job_title": "",
                "photo_url": "",
            },
        ).save(profile)
        print("  profile: migrated")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate JSON metadata to Supabase.")
    parser.add_argument("--user-id", help="Migrate one user UUID")
    parser.add_argument(
        "--data-root",
        default=str(ROOT / "data"),
        help="Path to the data directory",
    )
    args = parser.parse_args()

    if not use_database():
        print(
            "Set DATABASE_BACKEND=supabase and configure Supabase env vars first.",
            file=sys.stderr,
        )
        return 1

    data_root = Path(args.data_root)
    user_ids = _discover_user_ids(data_root, args.user_id)

    if not user_ids:
        print("No migratable users found under data/users/.")
        return 0

    print(f"Migrating {len(user_ids)} user(s)...")

    for user_id in user_ids:
        print(f"- {user_id}")
        migrate_user(user_id, data_root=data_root)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
