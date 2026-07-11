"""
DataDumpAI
Report Service
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage.file_store import FileStore
from models.report_data import ReportData
from services.report_document import report_data_from_storage


class ReportService:
    """Handles report persistence and metadata."""

    @classmethod
    def _file_store(cls) -> FileStore:
        return FileStore.for_current_user()

    @classmethod
    def _reports_dir(cls, project_id: str) -> Path:
        return cls._file_store()._local_root(project_id) / "reports"

    @classmethod
    def _metadata_filename(cls, filename: str) -> str:
        stem = Path(filename).stem
        return f"{stem}.meta.json"

    @classmethod
    def _slugify_report_name(cls, report_name: str) -> str:
        return report_name.strip().replace(" ", "_").lower()

    @classmethod
    def _metadata_storage_path(cls, project_id: str, filename: str) -> str:
        store = cls._file_store()
        meta_name = cls._metadata_filename(filename)
        if store._backend == "local":
            return str(store._local_root(project_id) / "reports" / meta_name)
        return store._storage_key(project_id, "reports", meta_name)

    @classmethod
    def _load_metadata(cls, project_id: str, filename: str) -> dict[str, Any]:
        storage_path = cls._metadata_storage_path(project_id, filename)

        if not cls._file_store().exists(storage_path):
            return {}

        try:
            data = json.loads(cls._file_store().read_text(storage_path))
        except Exception:
            return {}

        return data if isinstance(data, dict) else {}

    @classmethod
    def save_report_metadata(
        cls,
        project_id: str,
        filename: str,
        *,
        report_type: str,
        source_documents: list[str],
        report_data: dict[str, Any] | None = None,
    ) -> None:
        meta_name = cls._metadata_filename(filename)
        payload = {
            "report_type": report_type,
            "source_documents": source_documents,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if report_data:
            payload["report_data"] = report_data
        cls._file_store().write(
            project_id,
            "reports",
            meta_name,
            json.dumps(payload, indent=2).encode("utf-8") + b"\n",
        )

    @classmethod
    def get_report_metadata(cls, project_id: str, filename: str) -> dict[str, Any]:
        return cls._load_metadata(project_id, filename)

    @classmethod
    def save_report(
        cls,
        project_id: str,
        report_name: str,
        report_text: str | None = None,
        source_documents: list[str] | None = None,
        *,
        report: ReportData | None = None,
        report_data: dict[str, Any] | None = None,
    ) -> dict:
        if report is not None:
            report_text = report.to_markdown()
            report_data = report.to_dict()
        elif report_text is None:
            raise ValueError("save_report requires report or report_text")

        filename = f"{cls._slugify_report_name(report_name)}.md"
        created_at = datetime.now(timezone.utc).isoformat()
        content = report_text.encode("utf-8")
        storage_path = cls._file_store().write(
            project_id,
            "reports",
            filename,
            content,
        )

        if source_documents is not None:
            cls.save_report_metadata(
                project_id,
                filename,
                report_type=report_name,
                source_documents=source_documents,
                report_data=report_data,
            )

        from services.timeline_service import TimelineService

        metadata = {
            "filename": filename,
            "name": report_name,
            "path": storage_path,
            "size": len(content),
            "created_at": created_at,
            "report_type": report_name,
            "source_documents": source_documents or [],
        }

        TimelineService().record_report_generated(
            project_id=project_id,
            report_name=report_name,
            timestamp=created_at,
        )

        try:
            from core.auth import get_current_user_id
            from services.activity_service import ActivityService

            ActivityService(get_current_user_id()).log(
                "report.generated",
                f"Generated {report_name}",
                metadata={"project_id": project_id, "report_name": report_name},
            )
        except Exception:
            pass

        try:
            from core.telemetry import track
            from services.notification_service import NotificationService
            from services.project_service import ProjectService

            project = ProjectService().get_project(project_id)
            NotificationService().notify_report_ready(
                report_name=report_name,
                project_name=project.get("name", "Project"),
            )
            track(
                "report_generated",
                properties={"report_type": report_name, "project_id": project_id},
            )
        except Exception:
            pass

        return metadata

    @classmethod
    def update_report(
        cls,
        project_id: str,
        filename: str,
        report_text: str | None = None,
        source_documents: list[str] | None = None,
        *,
        report: ReportData | None = None,
        report_data: dict[str, Any] | None = None,
    ) -> dict:
        if report is not None:
            report_text = report.to_markdown()
            report_data = report.to_dict()
        elif report_text is None:
            raise ValueError("update_report requires report or report_text")

        safe_name = Path(filename).name
        store = cls._file_store()

        if store._backend == "local":
            storage_path = str(store._local_root(project_id) / "reports" / safe_name)
        else:
            storage_path = store._storage_key(project_id, "reports", safe_name)

        if not store.exists(storage_path):
            raise FileNotFoundError(f"Report not found: {safe_name!r}")

        content = report_text.encode("utf-8")
        storage_path = cls._file_store().write(
            project_id,
            "reports",
            safe_name,
            content,
        )
        updated_at = datetime.now(timezone.utc).isoformat()

        existing_meta = cls.get_report_metadata(project_id, safe_name)
        report_type = existing_meta.get("report_type", safe_name.replace("_", " ").title())
        documents = source_documents or existing_meta.get("source_documents", [])

        cls.save_report_metadata(
            project_id,
            safe_name,
            report_type=report_type,
            source_documents=documents,
            report_data=report_data if report_data is not None else existing_meta.get("report_data"),
        )

        return {
            "filename": safe_name,
            "name": report_type,
            "path": storage_path,
            "size": len(content),
            "created_at": updated_at,
            "report_type": report_type,
            "source_documents": documents,
        }

    @classmethod
    def get_reports(cls, project_id: str) -> list[dict]:
        reports: list[dict] = []
        store = cls._file_store()

        for filename in store.list_files(project_id, "reports"):
            if not filename.endswith(".md"):
                continue

            if store._backend == "local":
                storage_path = str(store._local_root(project_id) / "reports" / filename)
            else:
                storage_path = store._storage_key(project_id, "reports", filename)

            meta = cls.get_report_metadata(project_id, filename)
            report_type = meta.get("report_type") or Path(filename).stem.replace("_", " ").title()

            try:
                size = len(store.read_bytes(storage_path))
            except Exception:
                size = 0

            reports.append(
                {
                    "filename": filename,
                    "name": report_type,
                    "size": size,
                    "path": storage_path,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "report_type": report_type,
                    "source_documents": meta.get("source_documents", []),
                }
            )

        return reports

    @classmethod
    def load_report(cls, path: str) -> str:
        return cls._file_store().read_text(path)

    @classmethod
    def load_report_data(
        cls,
        project_id: str,
        filename: str,
        *,
        markdown_text: str | None = None,
    ) -> ReportData:
        """Load the canonical ReportData object for a saved report."""

        meta = cls.get_report_metadata(project_id, filename)

        if markdown_text is None:
            markdown_text = cls.load_report(cls._report_storage_path(project_id, filename))

        return report_data_from_storage(markdown_text, meta)

    @classmethod
    def _report_storage_path(cls, project_id: str, filename: str) -> str:
        store = cls._file_store()
        safe_name = Path(filename).name
        if store._backend == "local":
            return str(store._local_root(project_id) / "reports" / safe_name)
        return store._storage_key(project_id, "reports", safe_name)

    @classmethod
    def delete_report(cls, project_id: str, filename: str) -> None:
        safe_name = Path(filename).name

        if not safe_name or safe_name in {".", ".."}:
            raise ValueError(f"Invalid filename: {filename!r}")

        storage_path = cls._report_storage_path(project_id, safe_name)

        if not cls._file_store().exists(storage_path):
            raise FileNotFoundError(f"Report not found: {safe_name!r}")

        cls._file_store().delete(storage_path)

        meta_path = cls._metadata_storage_path(project_id, safe_name)
        if cls._file_store().exists(meta_path):
            cls._file_store().delete(meta_path)
