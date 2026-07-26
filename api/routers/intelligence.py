"""
Intelligence Studio routes — conversations + RAG answers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.auth_jwt import AuthenticatedPrincipal
from api.deps import get_principal, user_request_scope
from api.schemas import (
    IntelligenceCitationOut,
    IntelligenceConversationOut,
    IntelligenceConversationSummaryOut,
    IntelligenceMessageOut,
    IntelligenceSourceOut,
    RenameConversationBody,
    SendMessageBody,
    StartConversationBody,
    StudioReadinessOut,
)
from services.intelligence_rag_service import IntelligenceRagService
from services.project_service import ProjectService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/intelligence", tags=["intelligence"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _svc(principal: AuthenticatedPrincipal) -> ProjectService:
    return ProjectService(access_token=principal.access_token)


def _get_project(principal: AuthenticatedPrincipal, workspace_id: str) -> dict[str, Any]:
    with user_request_scope(principal):
        try:
            project = _svc(principal).get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if project.get("archived_at"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
        return project


def _save_project(principal: AuthenticatedPrincipal, project: dict[str, Any]) -> None:
    with user_request_scope(principal):
        project["updated_at"] = _utc_now()
        project["last_activity"] = project["updated_at"]
        _svc(principal).update_project(project)


def _conversations(project: dict[str, Any]) -> list[dict[str, Any]]:
    raw = project.get("studio_conversations")
    if not isinstance(raw, list):
        raw = []
        project["studio_conversations"] = raw
    return raw


def _find_conversation(
    project: dict[str, Any], conversation_id: str
) -> dict[str, Any]:
    for conversation in _conversations(project):
        if str(conversation.get("id")) == conversation_id:
            return conversation
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversation not found.")


def _source_out(raw: dict[str, Any]) -> IntelligenceSourceOut:
    return IntelligenceSourceOut(
        id=str(raw.get("id") or uuid.uuid4()),
        kind=str(raw.get("kind") or "document"),
        title=str(raw.get("title") or "Source"),
        location=raw.get("location"),
        excerpt=raw.get("excerpt"),
        preview_url=raw.get("previewUrl") or raw.get("preview_url"),
        document_id=raw.get("documentId") or raw.get("document_id"),
        score=raw.get("score"),
    )


def _citation_out(raw: dict[str, Any]) -> IntelligenceCitationOut:
    return IntelligenceCitationOut(
        id=str(raw.get("id") or uuid.uuid4()),
        index=int(raw.get("index") or 0),
        source_id=str(raw.get("sourceId") or raw.get("source_id") or ""),
        label=str(raw.get("label") or "Source"),
        quote=str(raw.get("quote") or ""),
        location=raw.get("location"),
    )


def _message_out(raw: dict[str, Any]) -> IntelligenceMessageOut:
    return IntelligenceMessageOut(
        id=str(raw["id"]),
        conversation_id=str(raw["conversationId"]),
        role=raw.get("role") or "assistant",
        content=str(raw.get("content") or ""),
        answer=raw.get("answer"),
        evidence=raw.get("evidence"),
        confidence=raw.get("confidence"),
        follow_ups=list(raw.get("followUps") or []),
        sources=[_source_out(item) for item in (raw.get("sources") or [])],
        citations=[_citation_out(item) for item in (raw.get("citations") or [])],
        linked_documents=[
            _source_out(item) for item in (raw.get("linkedDocuments") or [])
        ],
        notice=raw.get("notice"),
        status=raw.get("status") or "complete",
        created_at=str(raw.get("createdAt") or _utc_now()),
        mode=raw.get("mode"),
    )


def _conversation_out(raw: dict[str, Any]) -> IntelligenceConversationOut:
    return IntelligenceConversationOut(
        id=str(raw["id"]),
        workspace_id=str(raw["workspaceId"]),
        title=str(raw.get("title") or "Conversation"),
        pinned=bool(raw.get("pinned")),
        updated_at=str(raw.get("updatedAt") or _utc_now()),
        messages=[_message_out(item) for item in (raw.get("messages") or [])],
    )


def _summary_out(raw: dict[str, Any]) -> IntelligenceConversationSummaryOut:
    messages = raw.get("messages") or []
    preview = ""
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("answer"):
            preview = str(message["answer"])[:160]
            break
        if message.get("role") == "user" and message.get("content"):
            preview = str(message["content"])[:160]
            break
    return IntelligenceConversationSummaryOut(
        id=str(raw["id"]),
        workspace_id=str(raw["workspaceId"]),
        title=str(raw.get("title") or "Conversation"),
        pinned=bool(raw.get("pinned")),
        updated_at=str(raw.get("updatedAt") or _utc_now()),
        preview=preview,
    )


def _indexed_documents(project: dict[str, Any]) -> list[dict[str, Any]]:
    docs = []
    for document in project.get("documents") or []:
        status_value = str(document.get("status") or "")
        if status_value in {"indexed", "linked", "verified"}:
            docs.append(document)
    return docs


@router.get("/readiness", response_model=StudioReadinessOut)
def check_readiness(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> StudioReadinessOut:
    project = _get_project(principal, workspace_id)
    docs = list(project.get("documents") or [])
    indexed = _indexed_documents(project)
    can_ask = len(docs) > 0
    if not docs:
        status_text = "Upload documents to the Library to enable asking."
    elif not indexed:
        status_text = "Documents are indexing — answers improve once status is Done."
    else:
        status_text = f"Ready · {len(indexed)} indexed document(s)"
    return StudioReadinessOut(
        ready=bool(indexed),
        status=status_text,
        document_count=len(docs),
        report_count=0,
        can_ask=can_ask,
        web_research_available=False,
    )


@router.get("/suggestions", response_model=list[str])
def list_suggestions(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> list[str]:
    _get_project(principal, workspace_id)
    return [
        "What are the key risks in this workspace?",
        "Summarise the latest uploaded documents",
        "Which actions are still unresolved?",
        "Compare themes across the indexed sources",
        "Recommend next steps for leadership",
    ]


@router.get("/conversations", response_model=list[IntelligenceConversationSummaryOut])
def list_conversations(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> list[IntelligenceConversationSummaryOut]:
    project = _get_project(principal, workspace_id)
    conversations = sorted(
        _conversations(project),
        key=lambda item: str(item.get("updatedAt") or ""),
        reverse=True,
    )
    return [_summary_out(item) for item in conversations]


@router.post(
    "/conversations",
    response_model=IntelligenceConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def start_conversation(
    workspace_id: str,
    body: StartConversationBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> IntelligenceConversationOut:
    project = _get_project(principal, workspace_id)
    now = _utc_now()
    conversation = {
        "id": f"conv_{uuid.uuid4().hex[:12]}",
        "workspaceId": workspace_id,
        "title": (body.title or "").strip() or "New conversation",
        "pinned": False,
        "updatedAt": now,
        "messages": [],
    }
    _conversations(project).insert(0, conversation)
    _save_project(principal, project)

    if body.initial_message and body.initial_message.strip():
        return send_message(
            workspace_id,
            conversation["id"],
            SendMessageBody(
                content=body.initial_message.strip(),
                mode=body.mode or "ask",
            ),
            principal,
        )

    return _conversation_out(conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=IntelligenceConversationOut,
)
def get_conversation(
    workspace_id: str,
    conversation_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> IntelligenceConversationOut:
    project = _get_project(principal, workspace_id)
    return _conversation_out(_find_conversation(project, conversation_id))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=IntelligenceConversationOut,
)
def send_message(
    workspace_id: str,
    conversation_id: str,
    body: SendMessageBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> IntelligenceConversationOut:
    content = body.content.strip()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Message content required.")

    project = _get_project(principal, workspace_id)
    conversation = _find_conversation(project, conversation_id)
    now = _utc_now()

    user_message = {
        "id": f"msg_{uuid.uuid4().hex[:10]}",
        "conversationId": conversation_id,
        "role": "user",
        "content": content,
        "status": "complete",
        "createdAt": now,
        "mode": body.mode,
    }
    conversation.setdefault("messages", []).append(user_message)

    if conversation.get("title") in {"", "New conversation"}:
        conversation["title"] = content[:48]

    try:
        rag = IntelligenceRagService()
        result = rag.answer(
            workspace_id=workspace_id,
            question=content,
            mode=body.mode or "ask",
        )
        assistant = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "conversationId": conversation_id,
            "role": "assistant",
            "content": "",
            "answer": result.get("answer"),
            "evidence": result.get("evidence"),
            "confidence": result.get("confidence"),
            "followUps": result.get("followUps") or [],
            "sources": result.get("sources") or [],
            "citations": result.get("citations") or [],
            "linkedDocuments": result.get("linkedDocuments") or [],
            "notice": result.get("notice"),
            "status": "complete",
            "createdAt": _utc_now(),
            "mode": body.mode,
        }
    except Exception as exc:
        logger.exception("Intelligence Studio RAG failed workspace=%s", workspace_id)
        assistant = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "conversationId": conversation_id,
            "role": "assistant",
            "content": "",
            "answer": "Something went wrong while analysing this workspace.",
            "evidence": None,
            "confidence": 0.0,
            "followUps": [],
            "sources": [],
            "citations": [],
            "linkedDocuments": [],
            "notice": str(exc)[:300],
            "status": "error",
            "createdAt": _utc_now(),
            "mode": body.mode,
        }

    conversation["messages"].append(assistant)
    conversation["updatedAt"] = _utc_now()
    _save_project(principal, project)
    return _conversation_out(conversation)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=IntelligenceConversationSummaryOut,
)
def rename_conversation(
    workspace_id: str,
    conversation_id: str,
    body: RenameConversationBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> IntelligenceConversationSummaryOut:
    title = body.title.strip()
    if not title:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Title required.")
    project = _get_project(principal, workspace_id)
    conversation = _find_conversation(project, conversation_id)
    conversation["title"] = title
    conversation["updatedAt"] = _utc_now()
    _save_project(principal, project)
    return _summary_out(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    workspace_id: str,
    conversation_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> Response:
    project = _get_project(principal, workspace_id)
    conversations = _conversations(project)
    next_list = [item for item in conversations if str(item.get("id")) != conversation_id]
    if len(next_list) == len(conversations):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    project["studio_conversations"] = next_list
    _save_project(principal, project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/pin",
    response_model=IntelligenceConversationSummaryOut,
)
def toggle_pin(
    workspace_id: str,
    conversation_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> IntelligenceConversationSummaryOut:
    project = _get_project(principal, workspace_id)
    conversation = _find_conversation(project, conversation_id)
    conversation["pinned"] = not bool(conversation.get("pinned"))
    conversation["updatedAt"] = _utc_now()
    _save_project(principal, project)
    return _summary_out(conversation)
