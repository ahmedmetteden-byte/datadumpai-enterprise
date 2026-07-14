"""
Supabase PostgreSQL project repository.
"""

from __future__ import annotations

from typing import Any

from core.database import get_database_client, handle_response
from core.project_access import require_real_project_uuid
from core.workspace_context import is_quick_report


class SupabaseProjectRepository:
    """Persist projects and related metadata in PostgreSQL."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._client = get_database_client()

    @property
    def user_id(self) -> str:
        return self._user_id

    def all(self) -> list[dict[str, Any]]:
        response = handle_response(
            self._client.table("projects")
            .select("*")
            .eq("user_id", self._user_id)
            .order("created_at")
            .execute(),
            action="load projects",
        )

        projects: list[dict[str, Any]] = []

        for row in response.data or []:
            project_id = str(row["id"])
            projects.append(self._assemble_project(row, project_id))

        return projects

    def save(self, projects: list[dict[str, Any]]) -> None:
        existing_response = handle_response(
            self._client.table("projects")
            .select("id")
            .eq("user_id", self._user_id)
            .execute(),
            action="list existing projects",
        )
        existing_ids = {str(row["id"]) for row in (existing_response.data or [])}
        incoming_ids = {str(project["id"]) for project in projects}

        for project_id in existing_ids - incoming_ids:
            self._delete_project(project_id)

        for project in projects:
            if is_quick_report(str(project.get("id", ""))):
                continue
            self._upsert_project(project)

    def _assemble_project(self, row: dict[str, Any], project_id: str) -> dict[str, Any]:
        safe_project_id = require_real_project_uuid(project_id)
        return {
            "id": safe_project_id,
            "owner_id": str(row["user_id"]),
            "name": row["name"],
            "description": row.get("description", ""),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_activity": row["last_activity"],
            "storage_used": int(row.get("storage_used", 0)),
            "documents": self._load_documents(safe_project_id),
            "reports": self._load_reports(safe_project_id),
            "exports": self._load_exports(safe_project_id),
        }

    def _load_documents(self, project_id: str) -> list[dict[str, Any]]:
        safe_project_id = require_real_project_uuid(project_id)
        response = handle_response(
            self._client.table("documents")
            .select("*")
            .eq("project_id", safe_project_id)
            .eq("user_id", self._user_id)
            .order("uploaded_at")
            .execute(),
            action="load documents",
        )

        return [
            {
                "filename": row["filename"],
                "size": int(row["size"]),
                "uploaded_at": row["uploaded_at"],
                "path": row["storage_path"],
            }
            for row in (response.data or [])
        ]

    def _load_reports(self, project_id: str) -> list[dict[str, Any]]:
        safe_project_id = require_real_project_uuid(project_id)
        response = handle_response(
            self._client.table("reports")
            .select("*")
            .eq("project_id", safe_project_id)
            .eq("user_id", self._user_id)
            .order("created_at")
            .execute(),
            action="load reports",
        )

        reports: list[dict[str, Any]] = []

        for row in response.data or []:
            reports.append(
                {
                    "filename": row["filename"],
                    "name": row["name"],
                    "path": row["storage_path"],
                    "size": int(row["size"]),
                    "created_at": row["created_at"],
                    "report_type": row.get("report_type", ""),
                    "source_documents": row.get("source_documents") or [],
                }
            )

        return reports

    def _load_exports(self, project_id: str) -> list[dict[str, Any]]:
        safe_project_id = require_real_project_uuid(project_id)
        response = handle_response(
            self._client.table("exports")
            .select("*")
            .eq("project_id", safe_project_id)
            .eq("user_id", self._user_id)
            .order("exported_at")
            .execute(),
            action="load exports",
        )

        return [
            {
                "filename": row["filename"],
                "path": row["storage_path"],
                "size": int(row["size"]),
                "format": row.get("format", ""),
                "mime_type": row.get("mime_type", ""),
                "exported_at": row["exported_at"],
            }
            for row in (response.data or [])
        ]

    def _delete_project(self, project_id: str) -> None:
        safe_project_id = require_real_project_uuid(project_id)
        handle_response(
            self._client.table("projects")
            .delete()
            .eq("id", safe_project_id)
            .eq("user_id", self._user_id)
            .execute(),
            action="delete project",
        )

    def _upsert_project(self, project: dict[str, Any]) -> None:
        project_id = require_real_project_uuid(str(project["id"]))
        row = {
            "id": project_id,
            "user_id": self._user_id,
            "name": project["name"],
            "description": project.get("description", ""),
            "storage_used": int(project.get("storage_used", 0)),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at"),
            "last_activity": project.get("last_activity"),
        }

        handle_response(
            self._client.table("projects").upsert(row).execute(),
            action="save project",
        )

        self._sync_documents(project_id, project.get("documents", []))
        self._sync_reports(project_id, project.get("reports", []))
        self._sync_exports(project_id, project.get("exports", []))

    def _sync_documents(
        self,
        project_id: str,
        documents: list[dict[str, Any]],
    ) -> None:
        safe_project_id = require_real_project_uuid(project_id)
        existing = handle_response(
            self._client.table("documents")
            .select("filename")
            .eq("project_id", safe_project_id)
            .eq("user_id", self._user_id)
            .execute(),
            action="list documents",
        )
        existing_names = {row["filename"] for row in (existing.data or [])}
        incoming_names = {doc["filename"] for doc in documents}

        for filename in existing_names - incoming_names:
            handle_response(
                self._client.table("documents")
                .delete()
                .eq("project_id", safe_project_id)
                .eq("user_id", self._user_id)
                .eq("filename", filename)
                .execute(),
                action="delete document",
            )

        for document in documents:
            row = {
                "project_id": safe_project_id,
                "user_id": self._user_id,
                "filename": document["filename"],
                "size": int(document.get("size", 0)),
                "storage_path": document.get("path", ""),
                "uploaded_at": document.get("uploaded_at"),
            }
            handle_response(
                self._client.table("documents")
                .upsert(row, on_conflict="project_id,filename")
                .execute(),
                action="save document",
            )

    def _sync_reports(
        self,
        project_id: str,
        reports: list[dict[str, Any]],
    ) -> None:
        safe_project_id = require_real_project_uuid(project_id)
        existing = handle_response(
            self._client.table("reports")
            .select("filename")
            .eq("project_id", safe_project_id)
            .eq("user_id", self._user_id)
            .execute(),
            action="list reports",
        )
        existing_names = {row["filename"] for row in (existing.data or [])}
        incoming_names = {report["filename"] for report in reports}

        for filename in existing_names - incoming_names:
            handle_response(
                self._client.table("reports")
                .delete()
                .eq("project_id", safe_project_id)
                .eq("user_id", self._user_id)
                .eq("filename", filename)
                .execute(),
                action="delete report",
            )

        for report in reports:
            row = {
                "project_id": safe_project_id,
                "user_id": self._user_id,
                "filename": report["filename"],
                "name": report.get("name", report["filename"]),
                "storage_path": report.get("path", ""),
                "size": int(report.get("size", 0)),
                "report_type": report.get("report_type", ""),
                "source_documents": report.get("source_documents", []),
                "created_at": report.get("created_at"),
            }
            handle_response(
                self._client.table("reports")
                .upsert(row, on_conflict="project_id,filename")
                .execute(),
                action="save report",
            )

    def _sync_exports(
        self,
        project_id: str,
        exports: list[dict[str, Any]],
    ) -> None:
        safe_project_id = require_real_project_uuid(project_id)
        existing = handle_response(
            self._client.table("exports")
            .select("filename")
            .eq("project_id", safe_project_id)
            .eq("user_id", self._user_id)
            .execute(),
            action="list exports",
        )
        existing_names = {row["filename"] for row in (existing.data or [])}
        incoming_names = {export["filename"] for export in exports}

        for filename in existing_names - incoming_names:
            handle_response(
                self._client.table("exports")
                .delete()
                .eq("project_id", safe_project_id)
                .eq("user_id", self._user_id)
                .eq("filename", filename)
                .execute(),
                action="delete export",
            )

        for export in exports:
            row = {
                "project_id": safe_project_id,
                "user_id": self._user_id,
                "filename": export["filename"],
                "format": export.get("format", ""),
                "mime_type": export.get("mime_type", ""),
                "size": int(export.get("size", 0)),
                "storage_path": export.get("path", ""),
                "exported_at": export.get("exported_at"),
            }
            handle_response(
                self._client.table("exports")
                .upsert(row, on_conflict="project_id,filename")
                .execute(),
                action="save export",
            )
