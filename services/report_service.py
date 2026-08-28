"""
DataDumpAI
Report Service
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage.file_store import FileStore
from core.project_access import assert_project_access
from core.runtime_investigation import investigation_enabled
from models.report_data import ReportData
from services.report_document import report_data_from_storage

logger = logging.getLogger(__name__)


class ReportService:
    """Handles report persistence and metadata."""

    @classmethod
    def _file_store(cls, access_token: str | None = None) -> FileStore:
        return FileStore.for_current_user(access_token=access_token)

    @classmethod
    def _reports_dir(cls, project_id: str) -> Path:
        return cls._file_store()._local_root(project_id) / "reports"

    @classmethod
    def _metadata_filename(cls, filename: str) -> str:
        stem = Path(filename).stem
        return f"{stem}.meta.json"

    @classmethod
    def _slugify_report_name(cls, report_name: str) -> str:
        # Storage keys must be ASCII-safe and free of path separators —
        # drop accents/em-dashes/slashes/etc. (NFKD + ascii-ignore) rather
        # than only replacing spaces, which let characters like "—" and
        # "/" through and made Supabase Storage reject the upload outright.
        normalized = (
            unicodedata.normalize("NFKD", report_name)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        slug = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").lower()
        return slug or "report"

    @classmethod
    def _metadata_storage_path(
        cls, project_id: str, filename: str, *, access_token: str | None = None
    ) -> str:
        store = cls._file_store(access_token)
        meta_name = cls._metadata_filename(filename)
        if store._backend == "local":
            return str(store._local_root(project_id) / "reports" / meta_name)
        return store._storage_key(project_id, "reports", meta_name)

    @classmethod
    def _load_metadata(
        cls, project_id: str, filename: str, *, access_token: str | None = None
    ) -> dict[str, Any]:
        storage_path = cls._metadata_storage_path(
            project_id, filename, access_token=access_token
        )
        store = cls._file_store(access_token)

        try:
            data = json.loads(store.read_text(storage_path))
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
        access_token: str | None = None,
    ) -> None:
        meta_name = cls._metadata_filename(filename)
        payload = {
            "report_type": report_type,
            "source_documents": source_documents,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if report_data:
            payload["report_data"] = report_data
        cls._file_store(access_token).write(
            project_id,
            "reports",
            meta_name,
            json.dumps(payload, indent=2).encode("utf-8") + b"\n",
        )

    @classmethod
    def get_report_metadata(
        cls, project_id: str, filename: str, *, access_token: str | None = None
    ) -> dict[str, Any]:
        try:
            cls._require_project_access(project_id, access_token=access_token)
        except PermissionError:
            return {}
        return cls._load_metadata(project_id, filename, access_token=access_token)

    @classmethod
    def _require_project_access(
        cls, project_id: str, *, access_token: str | None = None
    ) -> str:
        return assert_project_access(project_id, access_token=access_token)

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
        access_token: str | None = None,
    ) -> dict:
        cls._require_project_access(project_id, access_token=access_token)
        if report is not None:
            report_text = report.to_markdown()
            report_data = report.to_dict()
        elif report_text is None:
            raise ValueError("save_report requires report or report_text")

        filename = f"{cls._slugify_report_name(report_name)}.md"
        created_at = datetime.now(timezone.utc).isoformat()
        content = report_text.encode("utf-8")
        storage_path = cls._file_store(access_token).write(
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
                access_token=access_token,
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

        try:
            TimelineService(access_token=access_token).record_report_generated(
                project_id=project_id,
                report_name=report_name,
                timestamp=created_at,
            )
        except Exception:
            logger.exception(
                "Failed to record timeline event for report generation project=%s",
                project_id,
            )

        try:
            from services.activity_service import ActivityService

            ActivityService(access_token=access_token).log(
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

            project = ProjectService(access_token=access_token).get_project(
                project_id
            )
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
        access_token: str | None = None,
    ) -> dict:
        cls._require_project_access(project_id, access_token=access_token)
        if report is not None:
            report_text = report.to_markdown()
            report_data = report.to_dict()
        elif report_text is None:
            raise ValueError("update_report requires report or report_text")

        safe_name = Path(filename).name
        store = cls._file_store(access_token)

        if store._backend == "local":
            storage_path = str(store._local_root(project_id) / "reports" / safe_name)
        else:
            storage_path = store._storage_key(project_id, "reports", safe_name)

        if not store.exists(storage_path):
            raise FileNotFoundError(f"Report not found: {safe_name!r}")

        content = report_text.encode("utf-8")
        storage_path = cls._file_store(access_token).write(
            project_id,
            "reports",
            safe_name,
            content,
        )
        updated_at = datetime.now(timezone.utc).isoformat()

        existing_meta = cls.get_report_metadata(
            project_id, safe_name, access_token=access_token
        )
        report_type = existing_meta.get("report_type", safe_name.replace("_", " ").title())
        documents = source_documents or existing_meta.get("source_documents", [])

        cls.save_report_metadata(
            project_id,
            safe_name,
            report_type=report_type,
            source_documents=documents,
            report_data=report_data if report_data is not None else existing_meta.get("report_data"),
            access_token=access_token,
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
    def get_reports(
        cls, project_id: str, *, access_token: str | None = None
    ) -> list[dict]:
        try:
            cls._require_project_access(project_id, access_token=access_token)
        except PermissionError:
            return []

        store = cls._file_store(access_token)

        # One listing call gets every filename AND its byte size (Supabase
        # Storage reports size in list() metadata) — this used to be a
        # separate list_files() call followed by a full read_bytes() download
        # of each report's content just to compute len(), which meant every
        # home-dashboard load re-downloaded the full text of every report in
        # every workspace across the network.
        sized_entries = store.list_files_with_size(project_id, "reports")
        md_entries = [(name, size) for name, size in sized_entries if name.endswith(".md")]

        if investigation_enabled():
            from core.runtime_investigation import log_report_load

            try:
                if store._backend == "local":
                    filesystem_path = str(store._local_root(project_id) / "reports")
                else:
                    filesystem_path = f"{store._user_id}/{project_id}/reports"
                log_report_load(
                    user_id=store._user_id,
                    project_id=project_id,
                    filesystem_path=filesystem_path,
                    report_count=len(md_entries),
                    filenames=[name for name, _ in md_entries],
                )
            except Exception:
                pass

        reports: list[dict] = []

        for filename, size in md_entries:
            if store._backend == "local":
                storage_path = str(store._local_root(project_id) / "reports" / filename)
            else:
                storage_path = store._storage_key(project_id, "reports", filename)

            meta = cls.get_report_metadata(
                project_id, filename, access_token=access_token
            )
            report_type = meta.get("report_type") or Path(filename).stem.replace("_", " ").title()

            reports.append(
                {
                    "filename": filename,
                    "name": report_type,
                    "size": size,
                    "path": storage_path,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "report_type": report_type,
                    "source_documents": meta.get("source_documents", []),
                    "report_data": meta.get("report_data"),
                }
            )

        return reports

    @classmethod
    def load_report(cls, path: str, *, access_token: str | None = None) -> str:
        return cls._file_store(access_token).read_text(path)

    @classmethod
    def load_report_for_project(
        cls, project_id: str, filename: str, *, access_token: str | None = None
    ) -> str:
        """Load report markdown after validating project ownership via FileStore."""

        cls._require_project_access(project_id, access_token=access_token)
        return cls.load_report(
            cls._report_storage_path(project_id, filename, access_token=access_token),
            access_token=access_token,
        )

    @classmethod
    def load_report_data(
        cls,
        project_id: str,
        filename: str,
        *,
        markdown_text: str | None = None,
        access_token: str | None = None,
    ) -> ReportData:
        """Load the canonical ReportData object for a saved report."""

        cls._require_project_access(project_id, access_token=access_token)
        meta = cls.get_report_metadata(project_id, filename, access_token=access_token)

        if markdown_text is None:
            markdown_text = cls.load_report_for_project(
                project_id, filename, access_token=access_token
            )

        return report_data_from_storage(markdown_text, meta)

    @classmethod
    def _report_storage_path(
        cls, project_id: str, filename: str, *, access_token: str | None = None
    ) -> str:
        store = cls._file_store(access_token)
        safe_name = Path(filename).name
        if store._backend == "local":
            return str(store._local_root(project_id) / "reports" / safe_name)
        return store._storage_key(project_id, "reports", safe_name)

    @classmethod
    def delete_report(
        cls, project_id: str, filename: str, *, access_token: str | None = None
    ) -> None:
        cls._require_project_access(project_id, access_token=access_token)
        safe_name = Path(filename).name

        if not safe_name or safe_name in {".", ".."}:
            raise ValueError(f"Invalid filename: {filename!r}")

        storage_path = cls._report_storage_path(
            project_id, safe_name, access_token=access_token
        )
        store = cls._file_store(access_token)

        if not store.exists(storage_path):
            raise FileNotFoundError(f"Report not found: {safe_name!r}")

        store.delete(storage_path)

        meta_path = cls._metadata_storage_path(
            project_id, safe_name, access_token=access_token
        )
        if store.exists(meta_path):
            store.delete(meta_path)
