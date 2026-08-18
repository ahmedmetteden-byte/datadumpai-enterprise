"""
Knowledge / document library routes.
"""

from __future__ import annotations

import io
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from api.auth_jwt import AuthenticatedPrincipal
from models.user import User
from api.deps import get_current_user, get_principal, user_request_scope
from api.mappers import (
    document_processing_status,
    document_to_knowledge_detail,
    document_to_knowledge_item,
    ensure_document_id,
    mime_for_filename,
)
from api.schemas import (
    KnowledgeDetailOut,
    KnowledgeFilterOptionsOut,
    KnowledgeListItemOut,
    KnowledgeListResultOut,
    KnowledgePreviewOut,
    KnowledgeProcessingStatusOut,
)
from services.document_service import DocumentService
from services.indexing_service import run_index_job
from services.project_service import ProjectService
from services.qdrant_service import QdrantService
from services.usage_service import UsageLimitError, UsageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".txt"}


class _UploadAdapter:
    """Adapt FastAPI UploadFile bytes to DocumentService.save_document shape."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._buffer = io.BytesIO(content)

    def read(self) -> bytes:
        return self._buffer.read()

    def seek(self, pos: int) -> None:
        self._buffer.seek(pos)


def _svc(principal: AuthenticatedPrincipal) -> ProjectService:
    return ProjectService(access_token=principal.access_token)


def _doc_svc(principal: AuthenticatedPrincipal) -> DocumentService:
    return DocumentService(access_token=principal.access_token)


def _get_project(principal: AuthenticatedPrincipal, workspace_id: str) -> dict[str, Any]:
    with user_request_scope(principal):
        try:
            project = _svc(principal).get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if project.get("archived_at"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
        return project


def _find_doc(project: dict[str, Any], knowledge_id: str) -> dict[str, Any]:
    for document in project.get("documents") or []:
        if str(document.get("id")) == knowledge_id:
            return document
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found.")


def _author_name(principal: AuthenticatedPrincipal) -> str:
    return principal.user.display_name


def _list_items(
    project: dict[str, Any],
    principal: AuthenticatedPrincipal,
) -> list[KnowledgeListItemOut]:
    workspace_id = str(project["id"])
    workspace_name = str(project.get("name") or "")
    items: list[KnowledgeListItemOut] = []
    for document in project.get("documents") or []:
        ensure_document_id(document)
        items.append(
            document_to_knowledge_item(
                document,
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                author_id=principal.user.id,
                author_name=_author_name(principal),
            )
        )
    return items


def _filter_sort(
    items: list[KnowledgeListItemOut],
    *,
    q: str | None,
    status_filter: list[str] | None,
    sort: str | None,
    limit: int,
    offset: int,
) -> KnowledgeListResultOut:
    filtered = items
    if q:
        needle = q.lower()
        filtered = [
            item
            for item in filtered
            if needle in item.title.lower()
            or needle in (item.filename or "").lower()
            or needle in (item.summary or "").lower()
        ]
    if status_filter:
        allowed = set(status_filter)
        filtered = [item for item in filtered if item.status in allowed]

    reverse = True
    key_fn = lambda item: item.updated_at  # noqa: E731
    if sort == "created_at":
        key_fn = lambda item: item.created_at  # noqa: E731
    elif sort == "title":
        key_fn = lambda item: item.title.lower()  # noqa: E731
        reverse = False
    elif sort == "relevance" and q:
        key_fn = lambda item: (  # noqa: E731
            0 if q.lower() in item.title.lower() else 1,
            item.updated_at,
        )
        reverse = False

    filtered = sorted(filtered, key=key_fn, reverse=reverse)
    total = len(filtered)
    page = filtered[offset : offset + limit]
    return KnowledgeListResultOut(items=page, total=total, limit=limit, offset=offset)


@router.get("/knowledge", response_model=KnowledgeListResultOut)
@router.get("/knowledge/search", response_model=KnowledgeListResultOut)
def list_or_search_knowledge(
    workspace_id: str,
    q: str | None = None,
    doc_status: str | None = Query(default=None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    sort: str | None = "updated_at",
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgeListResultOut:
    project = _get_project(principal, workspace_id)
    # Persist any newly assigned document ids
    with user_request_scope(principal):
        changed = False
        for document in project.get("documents") or []:
            before = document.get("id")
            ensure_document_id(document)
            if document.get("id") != before:
                changed = True
        if changed:
            _svc(principal).update_project(project)
            project = _svc(principal).get_project(workspace_id)

    status_filter = (
        [s.strip() for s in doc_status.split(",") if s.strip()] if doc_status else None
    )
    return _filter_sort(
        _list_items(project, principal),
        q=q,
        status_filter=status_filter,
        sort=sort,
        limit=max(1, min(limit, 200)),
        offset=max(0, offset),
    )


@router.get("/knowledge/filters", response_model=KnowledgeFilterOptionsOut)
def knowledge_filters(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgeFilterOptionsOut:
    project = _get_project(principal, workspace_id)
    return KnowledgeFilterOptionsOut(
        tags=[],
        projects=[{"id": str(project["id"]), "name": str(project.get("name") or "")}],
        authors=[
            {"id": principal.user.id, "name": _author_name(principal)},
        ],
        collections=[
            {"id": f"col_{project['id']}", "name": "Library"},
        ],
        types=["document"],
    )


@router.get("/search/suggestions")
def search_suggestions(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    project = _get_project(principal, workspace_id)
    recent = [
        {
            "id": str(doc.get("id") or ensure_document_id(doc)),
            "label": str(doc.get("filename") or ""),
            "href": f"/knowledge/{doc.get('id')}",
        }
        for doc in (project.get("documents") or [])[:8]
    ]
    return {
        "recentSearches": [],
        "suggestedActions": [],
        "recentReports": [],
        "recentWorkspaces": [
            {
                "id": str(project["id"]),
                "label": str(project.get("name") or ""),
                "href": f"/workspaces/{project['id']}/overview",
            }
        ],
        "recentDocuments": recent,
    }


@router.post(
    "/knowledge/upload",
    response_model=KnowledgeListItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgeListItemOut:
    filename = Path(file.filename or "upload.bin").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Empty file.")

    with user_request_scope(principal):
        try:
            UsageService(access_token=principal.access_token).check_can_upload()
        except UsageLimitError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        project = _get_project(principal, workspace_id)
        doc_service = _doc_svc(principal)
        try:
            metadata = doc_service.save_document(
                workspace_id,
                _UploadAdapter(filename, content),
                overwrite=False,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        document = {
            **metadata,
            "id": str(uuid.uuid4()),
            "mime_type": file.content_type or mime_for_filename(filename),
            "title": (title or "").strip() or Path(filename).stem,
            "status": "uploaded",
            "index_stage": "queued",
            "progress_percent": 8,
            "error_message": None,
            "indexed_at": None,
            "chunk_count": 0,
            "updated_at": metadata.get("uploaded_at"),
        }
        _svc(principal).upsert_document(
            workspace_id,
            document,
            size_delta=int(document.get("size") or 0),
            last_activity=document.get("uploaded_at"),
        )
        UsageService(access_token=principal.access_token).record_uploads()

    background_tasks.add_task(
        run_index_job,
        user_id=principal.user.id,
        email=principal.user.email,
        full_name=principal.user.full_name,
        access_token=principal.access_token,
        workspace_id=workspace_id,
        document_id=str(document["id"]),
        reindex=False,
    )

    return document_to_knowledge_item(
        document,
        workspace_id=workspace_id,
        workspace_name=str(project.get("name") or ""),
        author_id=principal.user.id,
        author_name=_author_name(principal),
    )


@router.get("/knowledge/{knowledge_id}", response_model=KnowledgeDetailOut)
def get_knowledge(
    workspace_id: str,
    knowledge_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgeDetailOut:
    project = _get_project(principal, workspace_id)
    document = _find_doc(project, knowledge_id)
    return document_to_knowledge_detail(
        document,
        workspace_id=workspace_id,
        workspace_name=str(project.get("name") or ""),
        author_id=principal.user.id,
        author_name=_author_name(principal),
    )


@router.get("/knowledge/{knowledge_id}/preview", response_model=KnowledgePreviewOut)
def preview_knowledge(
    workspace_id: str,
    knowledge_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgePreviewOut:
    project = _get_project(principal, workspace_id)
    document = _find_doc(project, knowledge_id)
    filename = str(document.get("filename") or "")
    with user_request_scope(principal):
        try:
            text = _doc_svc(principal).read_document_text(workspace_id, filename)
        except Exception as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract preview: {exc}",
            ) from exc
    excerpt = text[:4000] if text else ""
    kind = "pdf" if filename.lower().endswith(".pdf") else "text"
    return KnowledgePreviewOut(
        knowledge_id=knowledge_id,
        kind=kind,
        text_excerpt=excerpt or None,
    )


@router.get("/knowledge/{knowledge_id}/processing", response_model=KnowledgeProcessingStatusOut)
def processing_status(
    workspace_id: str,
    knowledge_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgeProcessingStatusOut:
    project = _get_project(principal, workspace_id)
    document = _find_doc(project, knowledge_id)
    return document_processing_status(document)


@router.post(
    "/knowledge/{knowledge_id}/reindex",
    response_model=KnowledgeProcessingStatusOut,
)
def reindex_knowledge(
    workspace_id: str,
    knowledge_id: str,
    background_tasks: BackgroundTasks,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> KnowledgeProcessingStatusOut:
    project = _get_project(principal, workspace_id)
    document = _find_doc(project, knowledge_id)
    document["status"] = "uploaded"
    document["index_stage"] = "queued"
    document["progress_percent"] = 0
    document["error_message"] = None
    with user_request_scope(principal):
        _svc(principal).update_project(project)

    background_tasks.add_task(
        run_index_job,
        user_id=principal.user.id,
        email=principal.user.email,
        full_name=principal.user.full_name,
        access_token=principal.access_token,
        workspace_id=workspace_id,
        document_id=knowledge_id,
        reindex=True,
    )
    return document_processing_status(document)


@router.get("/knowledge/{knowledge_id}/download")
def download_knowledge(
    workspace_id: str,
    knowledge_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
):
    project = _get_project(principal, workspace_id)
    document = _find_doc(project, knowledge_id)
    filename = str(document.get("filename") or "download.bin")
    with user_request_scope(principal):
        doc_service = _doc_svc(principal)
        storage_path = str(document.get("path") or "")
        try:
            if storage_path:
                data = doc_service._file_store.read_bytes(storage_path)
            else:
                data = doc_service._file_store.read_bytes(
                    doc_service._file_store.resolve_document_path(workspace_id, filename)
                )
        except Exception as exc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {exc}",
            ) from exc

    mime = str(document.get("mime_type") or mime_for_filename(filename))
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/knowledge/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    workspace_id: str,
    knowledge_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> None:
    project = _get_project(principal, workspace_id)
    document = _find_doc(project, knowledge_id)
    filename = str(document.get("filename") or "")

    with user_request_scope(principal):
        try:
            _doc_svc(principal).delete_document(workspace_id, filename)
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception(
                "Failed to delete document from storage workspace=%s filename=%s "
                "storage_path=%s",
                workspace_id,
                filename,
                document.get("path"),
            )
        project["documents"] = [
            d for d in (project.get("documents") or []) if str(d.get("id")) != knowledge_id
        ]
        _svc(principal).update_project(project)

    try:
        QdrantService().delete_document(knowledge_id)
    except Exception:
        pass


@router.get("/knowledge/{knowledge_id}/related")
def related_knowledge(
    workspace_id: str,
    knowledge_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[Any]:
    _get_project(principal, workspace_id)
    _find_doc(_get_project(principal, workspace_id), knowledge_id)
    return []
