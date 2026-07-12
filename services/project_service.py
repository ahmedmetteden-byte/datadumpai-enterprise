"""
DataDumpAI Enterprise
Project Service
"""

from __future__ import annotations

import json
import shutil
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.current_user import CurrentUser, require_current_user
from repositories.project_repository import ProjectRepository
from services.document_service import DocumentService
from services.timeline_service import TimelineService


class ProjectService:
    """
    Manages project persistence for DataDumpAI Enterprise.

    Projects are stored as JSON on disk. All file I/O is handled
    internally so the UI layer only interacts with project data
    through this service.

    Public lookup and mutation methods use project IDs. Names are
    display metadata only.
    """

    def __init__(
        self,
        *,
        document_service: DocumentService | None = None,
        current_user: CurrentUser | None = None,
    ) -> None:
        self._current_user = current_user or require_current_user()
        self.repository = ProjectRepository(self._current_user)
        self._document_service = document_service or DocumentService(
            current_user=self._current_user,
        )
        self._ensure_storage_exists()

    @property
    def current_user(self) -> CurrentUser:
        return self._current_user

    def _ensure_storage_exists(self) -> None:
        """Create the storage directory and file when they do not exist."""

        self.repository.all()

    def _utc_now(self) -> str:
        """Return the current UTC timestamp in ISO 8601 format."""

        return datetime.now(timezone.utc).isoformat()

    def _find_project_index(
        self,
        projects: list[dict[str, Any]],
        project_id: str,
    ) -> int:
        """Return the index of a project by id, or raise ValueError."""

        for index, project in enumerate(projects):
            if project.get("id") == project_id:
                return index

        raise ValueError(f"Project not found: {project_id!r}")

    def _project_name_exists(
        self,
        projects: list[dict[str, Any]],
        name: str,
        *,
        exclude_index: int | None = None,
    ) -> bool:
        """Return True when another project already uses the given name."""

        normalized_name = name.strip()

        for index, project in enumerate(projects):
            if exclude_index is not None and index == exclude_index:
                continue
            if project.get("name") == normalized_name:
                return True

        return False

    def get_projects(self) -> list[dict[str, Any]]:
        """
        Return all projects.

        Returns a deep copy so callers can inspect data without
        accidentally mutating persisted state.
        """

        return deepcopy(self.repository.all())

    def get_statistics(self) -> dict[str, int]:
        """
        Return aggregate counts across all projects.

        Useful for dashboard metrics without loading full project data.
        """

        projects = self.repository.all()

        return {
            "projects": len(projects),
            "documents": sum(
                len(p["documents"])
                for p in projects
            ),
            "reports": sum(
                len(p["reports"])
                for p in projects
            ),
        }

    def get_project(self, project_id: str) -> dict[str, Any]:
        """Return a single project by id."""

        projects = self.repository.all()

        for project in projects:

            if project["id"] == project_id:

                return deepcopy(project)

        raise ValueError("Project not found.")

    def get_project_by_name(self, name: str) -> dict[str, Any]:
        """Return a single project by display name."""

        projects = self.repository.all()

        for project in projects:

            if project["name"] == name:

                return deepcopy(project)

        raise ValueError("Project not found.")

    def project_exists(self, project_id: str) -> bool:
        """
        Check whether a project exists by id.
        """

        projects = self.repository.all()

        return any(project.get("id") == project_id for project in projects)

    def create_project(self, name: str) -> dict[str, Any]:
        """
        Create a new project.
        """

        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError("Project name cannot be empty.")

        projects = self.repository.all()

        if self._project_name_exists(projects, normalized_name):
            raise ValueError(
                f"Project '{normalized_name}' already exists."
            )

        timestamp = self._utc_now()

        project = {
            "id": str(uuid.uuid4()),
            "owner_id": self._current_user.id,
            "name": normalized_name,
            "description": "",
            "created_at": timestamp,
            "updated_at": timestamp,
            "documents": [],
            "reports": [],
            "exports": [],
            "storage_used": 0,
            "last_activity": timestamp,
        }

        self._document_service.create_project_folders(project["id"])

        projects.append(project)

        self.repository.save(projects)

        TimelineService().record_project_created(
            project_id=project["id"],
            timestamp=timestamp,
        )

        return deepcopy(project)

    def update_project(self, project: dict[str, Any]) -> None:
        """
        Update an existing project.
        """

        projects = self.repository.all()

        for i, existing in enumerate(projects):

            if existing["id"] == project["id"]:

                project["updated_at"] = self._utc_now()

                projects[i] = project

                self.repository.save(projects)

                return

        raise ValueError("Project not found.")

    def rename_project(self, project_id: str, new_name: str) -> dict[str, Any]:
        """
        Rename an existing project.

        Args:
            project_id: ID of the project to rename.
            new_name: New display name for the project.

        Returns:
            The updated project dictionary.

        Raises:
            ValueError: If the name is invalid, the project does not exist,
                or another project already uses the new name.
        """

        normalized_new_name = new_name.strip()

        if not normalized_new_name:
            raise ValueError("Project name cannot be empty.")

        projects = self.repository.all()
        index = self._find_project_index(projects, project_id)

        if self._project_name_exists(
            projects,
            normalized_new_name,
            exclude_index=index,
        ):
            raise ValueError(
                f"A project named {normalized_new_name!r} already exists."
            )

        project = projects[index]
        project["name"] = normalized_new_name
        project["updated_at"] = self._utc_now()

        self.repository.save(projects)

        return deepcopy(project)

    def delete_project(self, project_id: str) -> None:
        """
        Delete a project by id.

        Args:
            project_id: ID of the project to remove.

        Raises:
            ValueError: If the project does not exist.
        """

        projects = self.repository.all()
        index = self._find_project_index(projects, project_id)

        del projects[index]
        self.repository.save(projects)

        project_root = self._document_service._file_store._local_root(project_id)

        if project_root.exists():
            shutil.rmtree(project_root)

    def save_projects(self, projects: list[dict[str, Any]]) -> None:
        """
        Replace all persisted projects with the provided list.

        Args:
            projects: Complete list of project dictionaries to store.

        Raises:
            ValueError: If the payload is not a list of project objects.
        """

        if not isinstance(projects, list):
            raise ValueError("Projects must be provided as a list.")

        for project in projects:
            if not isinstance(project, dict):
                raise ValueError("Each project must be a dictionary.")
            if "id" not in project:
                raise ValueError("Each project must include an id.")
            if "name" not in project:
                raise ValueError("Each project must include a name.")

        self.repository.save(deepcopy(projects))
