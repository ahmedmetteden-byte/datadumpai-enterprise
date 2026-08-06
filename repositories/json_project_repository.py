"""
JSON-backed project repository (Phase 1 filesystem storage).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.user_paths import get_user_projects_json
from storage.json_storage import JSONStorage


class JsonProjectRepository:
    """Load and save the denormalized project index from JSON."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self.storage = JSONStorage(get_user_projects_json(user_id))

    @property
    def user_id(self) -> str:
        return self._user_id

    def all(self) -> list:
        return self.storage.load()

    def save(self, projects: list) -> None:
        self.storage.save(projects)

    def upsert_document(
        self,
        project_id: str,
        document: dict[str, Any],
        *,
        size_delta: int = 0,
        last_activity: str | None = None,
    ) -> None:
        projects = self.storage.load()
        for project in projects:
            if str(project.get("id")) != str(project_id):
                continue

            doc_id = document.get("id")
            if not doc_id:
                doc_id = str(uuid.uuid4())
                document["id"] = doc_id

            docs = project.get("documents") or []
            for index, existing in enumerate(docs):
                if existing.get("id") == doc_id or existing.get("filename") == document.get(
                    "filename"
                ):
                    docs[index] = document
                    break
            else:
                docs.append(document)

            project["documents"] = docs
            if size_delta:
                project["storage_used"] = int(project.get("storage_used") or 0) + size_delta
            if last_activity is not None:
                project["last_activity"] = last_activity
            project["updated_at"] = datetime.now(timezone.utc).isoformat()
            break

        self.storage.save(projects)
