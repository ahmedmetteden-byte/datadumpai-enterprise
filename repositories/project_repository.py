"""
Project repository — JSON or Supabase depending on configuration.
"""

from __future__ import annotations

from core.auth import get_current_user_id
import config
from repositories.json_project_repository import JsonProjectRepository
from repositories.supabase_project_repository import SupabaseProjectRepository


class ProjectRepository:
    """Repository responsible for loading and saving projects for one user."""

    def __init__(self, user_id: str | None = None) -> None:
        resolved_user_id = user_id or get_current_user_id()
        self._user_id = resolved_user_id

        if config.use_database():
            self._impl = SupabaseProjectRepository(resolved_user_id)
        else:
            self._impl = JsonProjectRepository(resolved_user_id)

    @property
    def user_id(self) -> str:
        return self._user_id

    def all(self) -> list:
        return self._impl.all()

    def save(self, projects: list) -> None:
        self._impl.save(projects)
