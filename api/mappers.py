"""
Shared mappers between Python project/document dicts and SPA DTOs.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Any

from api.schemas import (
    KnowledgeDetailOut,
    KnowledgeListItemOut,
    KnowledgeProcessingStatusOut,
    WorkspaceOut,
)

STAGE_LABELS = {
    "queued": "Indexing...",
    "extracting": "Extract text",
    "chunking": "Chunk",
    "embedding": "Embeddings",
    "upserting": "Qdrant",
    "indexed": "Done",
    "failed": "Indexing failed",
}


def mime_for_filename(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def project_to_workspace(project: dict[str, Any]) -> WorkspaceOut:
    return WorkspaceOut(
        id=str(project["id"]),
        owner_id=str(project.get("owner_id") or ""),
        name=str(project.get("name") or ""),
        description=str(project.get("description") or ""),
        created_at=str(project.get("created_at") or ""),
        updated_at=str(project.get("updated_at") or ""),
        last_activity=str(project.get("last_activity") or project.get("updated_at") or ""),
        storage_used=int(project.get("storage_used") or 0),
    )


def ensure_document_id(document: dict[str, Any]) -> str:
    doc_id = str(document.get("id") or "").strip()
    if doc_id:
        return doc_id
    doc_id = str(uuid.uuid4())
    document["id"] = doc_id
    return doc_id


def document_to_knowledge_item(
    document: dict[str, Any],
    *,
    workspace_id: str,
    workspace_name: str,
    author_id: str,
    author_name: str,
) -> KnowledgeListItemOut:
    ensure_document_id(document)
    filename = str(document.get("filename") or "document")
    uploaded = str(document.get("uploaded_at") or document.get("created_at") or "")
    updated = str(
        document.get("indexed_at")
        or document.get("updated_at")
        or uploaded
    )
    status = str(document.get("status") or "uploaded")
    mime = str(document.get("mime_type") or mime_for_filename(filename))
    title = str(document.get("title") or Path(filename).stem or filename)

    tags = document.get("tags")
    if isinstance(tags, list):
        tag_labels = [str(tag) for tag in tags if str(tag).strip()]
    else:
        tag_labels = []

    collection_name = str(
        document.get("collection_name")
        or document.get("collection")
        or "Library"
    ).strip() or "Library"
    collection_id = str(document.get("collection_id") or f"col_{workspace_id}")

    return KnowledgeListItemOut(
        id=str(document["id"]),
        workspace_id=workspace_id,
        type="document",
        title=title,
        summary=str(document.get("summary") or "") or None,
        status=status,
        tag_ids=list(document.get("tag_ids") or []),
        tags=tag_labels,
        project_id=workspace_id,
        project_name=workspace_name,
        author_id=author_id,
        author_name=author_name,
        updated_at=updated,
        created_at=uploaded,
        collection_ids=[collection_id],
        collection_name=collection_name,
        filename=filename,
        mime_type=mime,
        size_bytes=int(document.get("size") or 0),
        indexed_at=document.get("indexed_at"),
        progress_percent=int(document.get("progress_percent") or 0),
        index_stage=str(document.get("index_stage") or "") or None,
    )


def document_to_knowledge_detail(
    document: dict[str, Any],
    *,
    workspace_id: str,
    workspace_name: str,
    author_id: str,
    author_name: str,
) -> KnowledgeDetailOut:
    item = document_to_knowledge_item(
        document,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        author_id=author_id,
        author_name=author_name,
    )
    return KnowledgeDetailOut(
        **item.model_dump(),
        metadata={
            "filename": item.filename,
            "mimeType": item.mime_type,
            "sizeBytes": item.size_bytes,
            "status": item.status,
            "indexStage": document.get("index_stage") or "queued",
            "chunkCount": int(document.get("chunk_count") or 0),
        },
        storage_path=str(document.get("path") or "") or None,
        relationships=[],
        related=[],
        referenced_by=[],
        timeline=[],
        versions_placeholder="",
    )


def document_processing_status(document: dict[str, Any]) -> KnowledgeProcessingStatusOut:
    ensure_document_id(document)
    status = str(document.get("status") or "uploaded")
    stage_key = str(document.get("index_stage") or "queued")
    if status == "failed":
        stage_key = "failed"
    elif status == "indexed":
        stage_key = "indexed"
    return KnowledgeProcessingStatusOut(
        knowledge_id=str(document["id"]),
        status=status,
        stage=STAGE_LABELS.get(stage_key, stage_key),
        index_stage=stage_key,
        progress_percent=int(document.get("progress_percent") or 0),
        error_message=document.get("error_message"),
        updated_at=str(
            document.get("indexed_at")
            or document.get("updated_at")
            or document.get("uploaded_at")
            or ""
        ),
    )
