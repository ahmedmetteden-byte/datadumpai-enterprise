"""
DataDumpAI Enterprise
Document Service
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.current_user import CurrentUser, require_current_user
from core.project_access import assert_project_access
from services.timeline_service import TimelineService
from storage.file_store import FileStore

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Manages document storage for DataDumpAI Enterprise.

    Files are stored locally or in Supabase Storage depending on configuration.
    """

    def __init__(
        self,
        *,
        file_store: FileStore | None = None,
        current_user: CurrentUser | None = None,
    ) -> None:
        self._current_user = current_user or require_current_user()
        self._file_store = file_store or FileStore(self._current_user)

    @property
    def current_user(self) -> CurrentUser:
        return self._current_user

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _safe_filename(self, filename: str) -> str:
        safe_name = Path(filename).name

        if not safe_name or safe_name in {".", ".."}:
            raise ValueError(f"Invalid filename: {filename!r}")

        return safe_name

    def _build_metadata(
        self,
        *,
        filename: str,
        storage_path: str,
        size: int,
        uploaded_at: str | None = None,
    ) -> dict[str, Any]:
        return {
            "filename": filename,
            "size": size,
            "uploaded_at": uploaded_at or self._utc_now(),
            "path": storage_path,
        }

    def create_project_folders(self, project_id: str) -> None:
        self._file_store.ensure_project_folders(project_id)

    def save_document(
        self,
        project_id: str,
        uploaded_file: Any,
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        assert_project_access(project_id)
        filename = self._safe_filename(uploaded_file.name)

        if not overwrite:
            existing = self.get_documents(project_id)
            if any(document["filename"] == filename for document in existing):
                raise ValueError(f"Document already exists: {filename!r}")

        content = uploaded_file.read()

        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        uploaded_at = self._utc_now()
        storage_path = self._file_store.write(
            project_id,
            "documents",
            filename,
            content,
        )

        metadata = self._build_metadata(
            filename=filename,
            storage_path=storage_path,
            size=len(content),
            uploaded_at=uploaded_at,
        )

        TimelineService().record_document_uploaded(
            project_id=project_id,
            filename=filename,
            timestamp=uploaded_at,
        )

        try:
            from services.activity_service import ActivityService

            ActivityService().log(
                "document.uploaded",
                f"Uploaded {filename}",
                metadata={"project_id": project_id, "filename": filename},
            )
        except Exception:
            pass

        return metadata

    def get_documents(self, project_id: str) -> list[dict[str, Any]]:
        try:
            from core.runtime_investigation import log_document_load

            store = self._file_store
            try:
                if store._backend == "local":
                    filesystem_path = str(store._local_root(project_id) / "documents")
                else:
                    filesystem_path = f"{store._user_id}/{project_id}/documents"
                raw_filenames = store.list_files(project_id, "documents")
            except Exception:
                filesystem_path = f"(unresolved:{project_id})"
                raw_filenames = []

            log_document_load(
                user_id=self._current_user.id,
                project_id=project_id,
                filesystem_path=filesystem_path,
                document_count=len(raw_filenames),
                filenames=list(raw_filenames),
            )
        except Exception:
            pass

        try:
            assert_project_access(project_id)
        except PermissionError:
            return []

        documents: list[dict[str, Any]] = []

        for filename in self._file_store.list_files(project_id, "documents"):
            if self._file_store._backend == "local":
                storage_path = str(
                    self._file_store._local_root(project_id) / "documents" / filename
                )
            else:
                storage_path = self._file_store._storage_key(
                    project_id,
                    "documents",
                    filename,
                )

            try:
                size = len(self._file_store.read_bytes(storage_path))
            except Exception:
                continue

            documents.append(
                self._build_metadata(
                    filename=filename,
                    storage_path=storage_path,
                    size=size,
                )
            )

        return documents

    def read_document_text(self, project_id: str, filename: str, **kwargs) -> str:
        assert_project_access(project_id)
        safe_name = self._safe_filename(filename)
        document = next(
            (item for item in self.get_documents(project_id) if item["filename"] == safe_name),
            None,
        )

        if document is None:
            logger.error(
                "Document metadata not found project_id=%s filename=%s",
                project_id,
                safe_name,
            )
            raise FileNotFoundError(f"Document not found: {safe_name!r}")

        from services.document_processor import DocumentProcessor

        storage_path = document["path"]
        backend = getattr(self._file_store, "backend", None) or getattr(
            self._file_store, "_backend", "unknown"
        )
        metadata_size = document.get("size")

        logger.info(
            "Reading document text project_id=%s filename=%s backend=%s "
            "storage_path=%s metadata_size=%s",
            project_id,
            safe_name,
            backend,
            storage_path,
            metadata_size,
        )

        try:
            with self._file_store.readable_path(storage_path) as path:
                resolved_path = str(path)
                try:
                    file_size = path.stat().st_size
                except OSError:
                    file_size = None

                logger.info(
                    "Opened readable path for %s resolved_path=%s file_size=%s backend=%s",
                    safe_name,
                    resolved_path,
                    file_size,
                    backend,
                )

                text = DocumentProcessor.extract_text_from_path(str(path), **kwargs)
        except Exception:
            logger.exception(
                "Failed reading/extracting document project_id=%s filename=%s "
                "backend=%s storage_path=%s",
                project_id,
                safe_name,
                backend,
                storage_path,
            )
            raise

        char_count = len(text or "")
        stripped_count = len((text or "").strip())
        logger.info(
            "Document extraction finished project_id=%s filename=%s backend=%s "
            "storage_path=%s success=%s char_count=%s stripped_char_count=%s",
            project_id,
            safe_name,
            backend,
            storage_path,
            stripped_count > 0,
            char_count,
            stripped_count,
        )

        if stripped_count == 0:
            logger.warning(
                "Document extraction returned empty text project_id=%s filename=%s "
                "backend=%s storage_path=%s file_size=%s",
                project_id,
                safe_name,
                backend,
                storage_path,
                metadata_size,
            )

        return text

    def delete_document(self, project_id: str, filename: str) -> None:
        assert_project_access(project_id)
        safe_name = self._safe_filename(filename)
        document = next(
            (item for item in self.get_documents(project_id) if item["filename"] == safe_name),
            None,
        )

        if document is None:
            raise FileNotFoundError(f"Document not found: {safe_name!r}")

        self._file_store.delete(document["path"])

    def get_document_path(self, project_id: str, filename: str) -> Path:
        assert_project_access(project_id)
        safe_name = self._safe_filename(filename)
        document = next(
            (item for item in self.get_documents(project_id) if item["filename"] == safe_name),
            None,
        )

        if document is None:
            raise FileNotFoundError(f"Document not found: {safe_name!r}")

        path = Path(document["path"])
        if path.is_file():
            return path

        raise FileNotFoundError(
            f"Document is stored remotely. Use read_document_text() for {safe_name!r}."
        )
