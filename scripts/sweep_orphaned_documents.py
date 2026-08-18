#!/usr/bin/env python3
"""
Find (and, with --delete, remove) orphaned document blobs in Supabase
Storage: files that exist in the bucket but are no longer referenced by
any project's `documents` table row. These are left behind when a
document was deleted from the app but the physical Storage delete
silently failed (the bug fixed alongside this script) — invisible in
the Library UI, but still sitting in storage.

Dry-run by default. Nothing is deleted unless --delete is passed.
Re-run the dry run right before any real --delete pass — a document
uploaded between the two could otherwise be misflagged as an orphan.

Usage:
    python scripts/sweep_orphaned_documents.py                    # report only
    python scripts/sweep_orphaned_documents.py --project-id <id>  # scope to one project
    python scripts/sweep_orphaned_documents.py --delete           # actually delete

Requires (from the server's .env):
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import config  # noqa: E402
from core.database import create_service_role_client  # noqa: E402
from core.workspace_context import is_quick_report  # noqa: E402

PAGE_SIZE = 100


def _list_storage_prefix(bucket, prefix: str) -> list[dict[str, Any]]:
    """Paginate Supabase Storage list() — mirrors FileStore.list_files();
    the raw API caps at 100 objects per call and does not paginate itself."""

    entries_out: list[dict[str, Any]] = []
    offset = 0
    while True:
        entries = bucket.list(prefix, {"limit": PAGE_SIZE, "offset": offset})
        if not entries:
            break
        for entry in entries:
            name = entry.get("name")
            if name and not name.endswith("/"):
                entries_out.append(entry)
        if len(entries) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return entries_out


def find_orphans(client, *, project_id: str | None = None) -> list[dict[str, Any]]:
    """Return orphan candidates: storage objects under a project's
    documents/ prefix with no matching `documents` table row."""

    projects_query = client.table("projects").select("id, user_id")
    if project_id:
        projects_query = projects_query.eq("id", project_id)
    projects = [
        row
        for row in (projects_query.execute().data or [])
        if not is_quick_report(row.get("id"))
    ]

    documents_query = client.table("documents").select("project_id, storage_path")
    if project_id:
        documents_query = documents_query.eq("project_id", project_id)
    referenced_by_project: dict[str, set[str]] = {}
    for row in documents_query.execute().data or []:
        referenced_by_project.setdefault(row["project_id"], set()).add(row["storage_path"])

    bucket = client.storage.from_(config.SUPABASE_STORAGE_BUCKET)
    orphans: list[dict[str, Any]] = []

    for project in projects:
        pid = project["id"]
        user_id = project["user_id"]
        prefix = f"{user_id}/{pid}/documents/"
        referenced = referenced_by_project.get(pid, set())

        for entry in _list_storage_prefix(bucket, prefix):
            key = f"{prefix}{entry['name']}"
            if key not in referenced:
                metadata = entry.get("metadata") or {}
                orphans.append(
                    {
                        "user_id": user_id,
                        "project_id": pid,
                        "storage_key": key,
                        "size": metadata.get("size"),
                        "last_modified": entry.get("updated_at") or entry.get("created_at"),
                    }
                )

    return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default=None, help="Scope the sweep to one project id")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete orphan candidates (default: dry run, report only)",
    )
    args = parser.parse_args()

    if not config.use_database() or not config.is_supabase_configured():
        print(
            "This script requires DATABASE_BACKEND=supabase / STORAGE_BACKEND=supabase "
            "and configured Supabase credentials."
        )
        return 1

    client = create_service_role_client()
    orphans = find_orphans(client, project_id=args.project_id)

    if not orphans:
        print("No orphaned document blobs found.")
        return 0

    print(f"Found {len(orphans)} orphaned document blob(s):\n")
    for orphan in orphans:
        print(
            f"  user={orphan['user_id']}  project={orphan['project_id']}  "
            f"key={orphan['storage_key']}  size={orphan['size']}  "
            f"last_modified={orphan['last_modified']}"
        )

    if not args.delete:
        print("\nDry run only — nothing was deleted. Re-run with --delete to remove these.")
        return 0

    print("\nDeleting...")
    bucket = client.storage.from_(config.SUPABASE_STORAGE_BUCKET)
    succeeded = 0
    failed = 0
    for orphan in orphans:
        try:
            bucket.remove([orphan["storage_key"]])
            succeeded += 1
            print(f"  deleted: {orphan['storage_key']}")
        except Exception as exc:
            failed += 1
            print(f"  FAILED: {orphan['storage_key']} — {exc}")

    print(f"\nDone. {succeeded} deleted, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
