"""
DataDumpAI Enterprise
Document Service
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.current_user import CurrentUser, require_current_user
from core.project_access import assert_project_access
from services.timeline_service import TimelineService
from storage.file_store import FileStore


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
            raise FileNotFoundError(f"Document not found: {safe_name!r}")

        from services.document_processor import DocumentProcessor

        with self._file_store.readable_path(document["path"]) as path:
            return DocumentProcessor.extract_text_from_path(str(path), **kwargs)

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
