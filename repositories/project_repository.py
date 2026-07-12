"""
Project repository — JSON or Supabase depending on configuration.
"""

from __future__ import annotations

from core.current_user import CurrentUser, require_current_user
import config
from repositories.json_project_repository import JsonProjectRepository
from repositories.supabase_project_repository import SupabaseProjectRepository


class ProjectRepository:
    """Repository responsible for loading and saving projects for one user."""

    def __init__(self, current_user: CurrentUser | None = None) -> None:
        resolved = current_user or require_current_user()
        self._current_user = resolved
        self._user_id = resolved.id

        if config.use_database():
            self._impl = SupabaseProjectRepository(self._user_id)
        else:
            self._impl = JsonProjectRepository(self._user_id)

    @property
    def user_id(self) -> str:
        return self._user_id

    def all(self) -> list:
        return self._impl.all()

    def save(self, projects: list) -> None:
        self._impl.save(projects)
