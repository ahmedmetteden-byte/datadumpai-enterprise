"""
JSON-backed project repository (Phase 1 filesystem storage).
"""

from __future__ import annotations

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
