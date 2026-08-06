"""
Document indexing pipeline: extract → chunk → embed → Qdrant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.current_user import CurrentUser, current_user_scope
from models.user import User
from services.document_chunking import DocumentChunk, chunk_combined_source_text
from services.document_service import DocumentService
from services.embedding_service import EmbeddingService
from services.project_service import ProjectService
from services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_document(project: dict[str, Any], document_id: str) -> dict[str, Any] | None:
    for document in project.get("documents") or []:
        if str(document.get("id")) == document_id:
            return document
    return None


def _chunk_document_text(filename: str, text: str) -> list[dict[str, Any]]:
    """Build retrieval chunks from extracted text."""

    if not text.strip():
        return []

    wrapped = f"=== SOURCE DOCUMENT: {filename} ===\n\n{text}\n"
    chunks: list[DocumentChunk] = chunk_combined_source_text(
        wrapped,
        chunk_size=1800,
    )
    # Cap extremely large docs for this sprint
    limited = chunks[:200]
    return [
        {
            "chunk_index": chunk.chunk_index,
            "heading": chunk.heading,
            "text": chunk.text,
        }
        for chunk in limited
        if chunk.text.strip()
    ]


class IndexingService:
    def __init__(
        self,
        *,
        user: User | CurrentUser,
        access_token: str | None = None,
    ) -> None:
        self._user = user if isinstance(user, CurrentUser) else CurrentUser.from_user(user)
        self._access_token = access_token

    def _services(self) -> tuple[ProjectService, DocumentService]:
        ps = ProjectService(
            current_user=self._user,
            access_token=self._access_token,
        )
        ds = DocumentService(
            current_user=self._user,
            access_token=self._access_token,
        )
        return ps, ds

    def _persist_document(
        self,
        project_service: ProjectService,
        project: dict[str, Any],
        document: dict[str, Any],
    ) -> None:
        # Scoped to this one document row so a still-running indexing job
        # for an earlier document can't clobber a document another upload
        # added to the same project in the meantime (see
        # ProjectService.upsert_document).
        project_service.upsert_document(
            project["id"],
            document,
            last_activity=_utc_now(),
        )

    def update_status(
        self,
        *,
        workspace_id: str,
        document_id: str,
        status: str,
        stage: str,
        progress_percent: int,
        error_message: str | None = None,
        chunk_count: int | None = None,
        indexed: bool = False,
    ) -> dict[str, Any]:
        with current_user_scope(self._user):
            project_service, _ = self._services()
            project = project_service.get_project(workspace_id)
            document = _find_document(project, document_id)
            if document is None:
                raise ValueError(f"Document not found: {document_id}")
            document["status"] = status
            document["index_stage"] = stage
            document["progress_percent"] = progress_percent
            document["error_message"] = error_message
            document["updated_at"] = _utc_now()
            if chunk_count is not None:
                document["chunk_count"] = chunk_count
            if indexed:
                document["indexed_at"] = _utc_now()
            self._persist_document(project_service, project, document)
            return document

    def index_document(self, workspace_id: str, document_id: str) -> dict[str, Any]:
        with current_user_scope(self._user):
            project_service, document_service = self._services()
            project = project_service.get_project(workspace_id)
            document = _find_document(project, document_id)
            if document is None:
                raise ValueError(f"Document not found: {document_id}")

            filename = str(document.get("filename") or "")
            try:
                # Upload → Extract text → Chunk → Embeddings → Qdrant → Indexed
                self.update_status(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    status="extracting",
                    stage="extracting",
                    progress_percent=22,
                )

                text = document_service.read_document_text(workspace_id, filename)
                if not text.strip():
                    raise ValueError("No extractable text found in document.")

                self.update_status(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    status="processing",
                    stage="chunking",
                    progress_percent=34,
                )
                chunks = _chunk_document_text(filename, text)
                if not chunks:
                    raise ValueError("Document produced no chunks.")

                self.update_status(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    status="processing",
                    stage="embedding",
                    progress_percent=58,
                    chunk_count=len(chunks),
                )
                embeddings = EmbeddingService().embed_texts(
                    [chunk["text"] for chunk in chunks]
                )

                self.update_status(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    status="processing",
                    stage="upserting",
                    progress_percent=82,
                    chunk_count=len(chunks),
                )
                QdrantService().upsert_chunks(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=self._user.id,
                    filename=filename,
                    chunks=chunks,
                    vectors=embeddings,
                )

                return self.update_status(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    status="indexed",
                    stage="indexed",
                    progress_percent=100,
                    chunk_count=len(chunks),
                    indexed=True,
                )
            except Exception as exc:
                logger.exception(
                    "Indexing failed workspace=%s document=%s",
                    workspace_id,
                    document_id,
                )
                return self.update_status(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    status="failed",
                    stage="failed",
                    progress_percent=100,
                    error_message=str(exc)[:500],
                )

    def reindex_document(self, workspace_id: str, document_id: str) -> dict[str, Any]:
        try:
            QdrantService().delete_document(document_id)
        except Exception:
            pass
        self.update_status(
            workspace_id=workspace_id,
            document_id=document_id,
            status="uploaded",
            stage="queued",
            progress_percent=0,
            error_message=None,
            chunk_count=0,
        )
        return self.index_document(workspace_id, document_id)


def run_index_job(
    *,
    user_id: str,
    email: str,
    full_name: str | None,
    access_token: str | None,
    workspace_id: str,
    document_id: str,
    reindex: bool = False,
) -> None:
    """Background task entrypoint (no request context)."""

    user = User(
        id=user_id,
        email=email,
        full_name=full_name,
        email_verified=True,
    )
    service = IndexingService(user=user, access_token=access_token)
    if reindex:
        service.reindex_document(workspace_id, document_id)
    else:
        service.index_document(workspace_id, document_id)
