"""
Workspace (project) routes for the product API.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_jwt import AuthenticatedPrincipal
from api.deps import get_current_user, get_principal, user_request_scope
from api.mappers import project_to_workspace
from api.schemas import (
    ActivityLogOut,
    ContinueWorkingOut,
    CreateWorkspaceBody,
    OrgIntelligenceSignalOut,
    TeamMemberOut,
    UpdateWorkspaceBody,
    WorkspaceHealthOut,
    WorkspaceInsightsOverviewOut,
    WorkspaceMembershipOut,
    WorkspaceOut,
)
from models.user import User
from services.project_service import ProjectService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _svc(principal: AuthenticatedPrincipal) -> ProjectService:
    return ProjectService(access_token=principal.access_token)


def _is_archived(project: dict) -> bool:
    return bool(project.get("archived_at"))


def _get_active(principal: AuthenticatedPrincipal, workspace_id: str) -> dict:
    with user_request_scope(principal):
        try:
            project = _svc(principal).get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if _is_archived(project):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
        return project


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[WorkspaceOut]:
    with user_request_scope(principal):
        projects = _svc(principal).get_projects()
    return [
        project_to_workspace(p)
        for p in projects
        if not _is_archived(p)
    ]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: CreateWorkspaceBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    with user_request_scope(principal):
        svc = _svc(principal)
        try:
            project = svc.create_project(body.name)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if body.description:
            project["description"] = body.description.strip()
            svc.update_project(project)
            project = svc.get_project(project["id"])
    return project_to_workspace(project)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    return project_to_workspace(_get_active(principal, workspace_id))


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: str,
    body: UpdateWorkspaceBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> WorkspaceOut:
    with user_request_scope(principal):
        svc = _svc(principal)
        try:
            project = svc.get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if _is_archived(project):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
        try:
            if body.name is not None and body.name.strip() != project.get("name"):
                project = svc.rename_project(workspace_id, body.name)
            if body.description is not None:
                project["description"] = body.description.strip()
                svc.update_project(project)
                project = svc.get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return project_to_workspace(project)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> None:
    with user_request_scope(principal):
        svc = _svc(principal)
        try:
            svc.get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        try:
            from services.qdrant_service import QdrantService

            QdrantService().delete_workspace(workspace_id)
        except Exception:
            pass
        try:
            svc.delete_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{workspace_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_workspace(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> None:
    with user_request_scope(principal):
        svc = _svc(principal)
        try:
            project = svc.get_project(workspace_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        project["archived_at"] = datetime.now(timezone.utc).isoformat()
        project["updated_at"] = project["archived_at"]
        svc.update_project(project)


@router.get("/{workspace_id}/memberships/me", response_model=WorkspaceMembershipOut)
def my_membership(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> WorkspaceMembershipOut:
    project = _get_active(principal, workspace_id)
    return WorkspaceMembershipOut(
        user_id=principal.user.id,
        workspace_id=str(project["id"]),
        role="owner",
    )


@router.get("/{workspace_id}/health", response_model=WorkspaceHealthOut)
def workspace_health(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> WorkspaceHealthOut:
    project = _get_active(principal, workspace_id)
    docs = project.get("documents") or []
    indexed = sum(1 for d in docs if str(d.get("status")) == "indexed")
    total = len(docs)
    percent = int((indexed / total) * 100) if total else 100
    overall = "ready" if total == 0 or indexed == total else "warning"
    return WorkspaceHealthOut(
        overall_percent=percent,
        status=overall,
        indicators=[
            {
                "status": overall,
                "icon": "docs",
                "message": f"{indexed}/{total} documents indexed",
            }
        ],
        last_updated=str(project.get("last_activity") or project.get("updated_at") or ""),
    )


@router.get(
    "/{workspace_id}/insights/overview",
    response_model=WorkspaceInsightsOverviewOut,
)
def insights_overview(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> WorkspaceInsightsOverviewOut:
    project = _get_active(principal, workspace_id)
    docs = project.get("documents") or []
    indexed = sum(1 for d in docs if str(d.get("status")) == "indexed")
    total = len(docs)
    percent = int((indexed / total) * 100) if total else 100
    return WorkspaceInsightsOverviewOut(
        health_percent=percent,
        new_insight_count=0,
        reports_awaiting_review=0,
        last_updated=str(project.get("last_activity") or ""),
    )


@router.get("/{workspace_id}/team", response_model=list[TeamMemberOut])
def workspace_team(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[TeamMemberOut]:
    _get_active(principal, workspace_id)
    return [
        TeamMemberOut(
            id=principal.user.id,
            name=principal.user.display_name,
            role="owner",
            status="online",
        )
    ]


@router.get(
    "/{workspace_id}/organizational-intelligence",
    response_model=list[OrgIntelligenceSignalOut],
)
def org_intelligence(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[OrgIntelligenceSignalOut]:
    _get_active(principal, workspace_id)
    return []


@router.get("/{workspace_id}/activity", response_model=list[ActivityLogOut])
def recent_activity(
    workspace_id: str,
    limit: int = 20,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[ActivityLogOut]:
    _get_active(principal, workspace_id)
    return []


@router.get(
    "/{workspace_id}/continue-working",
    response_model=list[ContinueWorkingOut],
)
def continue_working(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[ContinueWorkingOut]:
    project = _get_active(principal, workspace_id)
    items: list[ContinueWorkingOut] = []
    for doc in (project.get("documents") or [])[:5]:
        doc_id = str(doc.get("id") or "")
        if not doc_id:
            continue
        items.append(
            ContinueWorkingOut(
                id=doc_id,
                title=str(doc.get("filename") or "Document"),
                subtitle=str(doc.get("status") or "uploaded"),
                kind="document",
                updated_at=str(doc.get("uploaded_at") or ""),
                href=f"/knowledge/{doc_id}",
            )
        )
    return items
