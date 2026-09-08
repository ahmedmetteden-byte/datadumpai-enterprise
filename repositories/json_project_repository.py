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
        # Assign the document id up front, outside the locked mutator —
        # generating it inside would make a retried/re-entrant mutate()
        # call (not a concern for JSONStorage.update() today, but a trap
        # for a future change) assign a different id each time.
        doc_id = document.get("id")
        if not doc_id:
            doc_id = str(uuid.uuid4())
            document["id"] = doc_id

        def _mutate(projects: list[dict[str, Any]]) -> None:
            for project in projects:
                if str(project.get("id")) != str(project_id):
                    continue

                docs = project.get("documents") or []
                for index, existing in enumerate(docs):
                    if existing.get("id") == doc_id or existing.get(
                        "filename"
                    ) == document.get("filename"):
                        docs[index] = document
                        break
                else:
                    docs.append(document)

                project["documents"] = docs
                if size_delta:
                    project["storage_used"] = (
                        int(project.get("storage_used") or 0) + size_delta
                    )
                if last_activity is not None:
                    project["last_activity"] = last_activity
                project["updated_at"] = datetime.now(timezone.utc).isoformat()
                break

        # JSONStorage.update() holds one lock across the whole load-mutate-
        # save cycle, so a concurrent upsert_document() call for a
        # *different* document in the same project (a second upload, or
        # the indexing background job updating an earlier document's
        # status) can't silently overwrite this write — see
        # JSONStorage.update()'s docstring for why the previous
        # load()-then-save() pattern here could.
        self.storage.update(_mutate)
