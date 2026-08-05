"""
Home / dashboard aggregate for the React SPA.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from api.auth_jwt import AuthenticatedPrincipal
from models.user import User
from api.deps import get_current_user, get_principal, user_request_scope
from api.mappers import project_to_workspace
from api.schemas import (
    ContinueWorkingOut,
    DashboardMetricOut,
    DashboardRecentItemOut,
    HomeDashboardOut,
    HomePageOut,
    NotificationOut,
    UserOut,
    WorkspaceInsightsOverviewOut,
)
from services.project_service import ProjectService

router = APIRouter(prefix="/home", tags=["home"])


def _svc(principal: AuthenticatedPrincipal) -> ProjectService:
    return ProjectService(access_token=principal.access_token)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_archived(project: dict[str, Any]) -> bool:
    return bool(project.get("archived_at"))


def _doc_status(document: dict[str, Any]) -> str:
    return str(document.get("status") or "uploaded")


def _is_indexed(document: dict[str, Any]) -> bool:
    return _doc_status(document) in {"indexed", "linked", "verified"}


def _greeting(name: str) -> str:
    hour = datetime.now().hour
    if hour < 12:
        lead = "Good morning"
    elif hour < 18:
        lead = "Good afternoon"
    else:
        lead = "Good evening"
    first = (name or "there").strip().split()[0] or "there"
    return f"{lead}, {first}"


def _sort_key(value: str | None) -> str:
    return str(value or "")


def build_dashboard(projects: list[dict[str, Any]]) -> dict[str, Any]:
    active = [p for p in projects if not _is_archived(p)]
    docs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    reports: list[tuple[dict[str, Any], dict[str, Any]]] = []
    conversations: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for project in active:
        for document in project.get("documents") or []:
            docs.append((project, document))
        for report in project.get("spa_reports") or []:
            reports.append((project, report))
        for conversation in project.get("studio_conversations") or []:
            conversations.append((project, conversation))

    indexed = sum(1 for _, document in docs if _is_indexed(document))
    total_docs = len(docs)
    indexed_percent = int(round((indexed / total_docs) * 100)) if total_docs else 100

    metrics = [
        DashboardMetricOut(id="workspaces", label="Workspaces", value=len(active)),
        DashboardMetricOut(id="documents", label="Documents", value=total_docs),
        DashboardMetricOut(id="reports", label="Reports", value=len(reports)),
        DashboardMetricOut(
            id="indexed",
            label="Indexed",
            value=indexed_percent,
            unit="percent",
        ),
    ]

    recent_uploads: list[DashboardRecentItemOut] = []
    for project, document in sorted(
        docs,
        key=lambda pair: _sort_key(
            str(pair[1].get("uploaded_at") or pair[1].get("created_at") or "")
        ),
        reverse=True,
    )[:6]:
        filename = str(document.get("filename") or document.get("title") or "Document")
        recent_uploads.append(
            DashboardRecentItemOut(
                id=str(document.get("id") or filename),
                title=filename,
                subtitle=str(project.get("name") or "Workspace"),
                href="/knowledge",
                kind="document",
                at=str(
                    document.get("uploaded_at")
                    or document.get("created_at")
                    or _utc_now()
                ),
                meta=_doc_status(document),
            )
        )

    recent_reports: list[DashboardRecentItemOut] = []
    for project, report in sorted(
        reports,
        key=lambda pair: _sort_key(
            str(pair[1].get("updatedAt") or pair[1].get("createdAt") or "")
        ),
        reverse=True,
    )[:6]:
        report_id = str(report.get("id") or "")
        recent_reports.append(
            DashboardRecentItemOut(
                id=report_id or str(report.get("filename") or "report"),
                title=str(report.get("name") or "Report"),
                subtitle=str(project.get("name") or "Workspace"),
                href=f"/reports/{report_id}" if report_id else "/reports",
                kind="report",
                at=str(report.get("updatedAt") or report.get("createdAt") or _utc_now()),
                meta=str(report.get("status") or "draft"),
            )
        )

    recent_conversations: list[DashboardRecentItemOut] = []
    for project, conversation in sorted(
        conversations,
        key=lambda pair: _sort_key(str(pair[1].get("updatedAt") or "")),
        reverse=True,
    )[:6]:
        conv_id = str(conversation.get("id") or "")
        messages = conversation.get("messages") or []
        preview = ""
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content"):
                preview = str(message["content"])[:120]
                break
            if message.get("role") == "assistant" and message.get("answer"):
                preview = str(message["answer"])[:120]
                break
        recent_conversations.append(
            DashboardRecentItemOut(
                id=conv_id or "conversation",
                title=str(conversation.get("title") or "Conversation"),
                subtitle=preview or str(project.get("name") or "Workspace"),
                href="/copilot",
                kind="conversation",
                at=str(conversation.get("updatedAt") or _utc_now()),
                meta=str(project.get("name") or ""),
            )
        )

    return {
        "metrics": metrics,
        "recent_uploads": recent_uploads,
        "recent_reports": recent_reports,
        "recent_conversations": recent_conversations,
        "document_count": total_docs,
        "report_count": len(reports),
        "indexed_percent": indexed_percent,
        "workspace_count": len(active),
    }


@router.get("", response_model=HomePageOut)
def get_home(
    workspace_id: str | None = Query(default=None),
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> HomePageOut:
    with user_request_scope(principal):
        projects = _svc(principal).get_projects()

    active_projects = [p for p in projects if not _is_archived(p)]
    if not active_projects:
        # Empty shell — frontend can redirect to create workspace
        dash = build_dashboard([])
        user = UserOut(
            id=principal.user.id,
            email=principal.user.email,
            full_name=principal.user.display_name,
            email_verified=True,
        )
        return HomePageOut(
            user=user,
            greeting=_greeting(principal.user.display_name),
            active_workspace=None,
            workspaces=[],
            notifications=[],
            unread_notification_count=0,
            quick_actions=[
                {
                    "id": "qa_upload",
                    "label": "Upload documents",
                    "description": "Add files to the library",
                    "icon": "upload",
                    "href": "/knowledge?upload=1",
                },
                {
                    "id": "qa_report",
                    "label": "Generate report",
                    "description": "Create a workspace report",
                    "icon": "report",
                    "href": "/reports/new",
                },
                {
                    "id": "qa_studio",
                    "label": "Ask Intelligence Studio",
                    "description": "Question your corpus",
                    "icon": "copilot",
                    "href": "/copilot",
                },
            ],
            continue_working=[],
            insights_overview=WorkspaceInsightsOverviewOut(
                health_percent=100,
                new_insight_count=0,
                reports_awaiting_review=0,
                last_updated=_utc_now(),
            ),
            dashboard=HomeDashboardOut(**{
                "metrics": dash["metrics"],
                "recent_uploads": dash["recent_uploads"],
                "recent_reports": dash["recent_reports"],
                "recent_conversations": dash["recent_conversations"],
            }),
            search={
                "recentSearches": [],
                "suggestedActions": [],
                "recentReports": [],
                "recentWorkspaces": [],
            },
            reports_awaiting_review=[],
            insights={
                "brief": {
                    "date": _utc_now(),
                    "greeting": "Welcome",
                    "items": [],
                },
                "recommendations": [],
                "recentActivity": [],
                "health": {
                    "overallPercent": 100,
                    "status": "ready",
                    "indicators": [],
                    "lastUpdated": _utc_now(),
                },
                "team": [],
                "organizationalIntelligence": [],
                "items": [],
            },
        )

    selected = None
    if workspace_id:
        selected = next(
            (p for p in active_projects if str(p.get("id")) == workspace_id),
            None,
        )
    if selected is None:
        selected = sorted(
            active_projects,
            key=lambda p: str(p.get("last_activity") or p.get("updated_at") or ""),
            reverse=True,
        )[0]

    dash = build_dashboard(active_projects)
    workspace_out = project_to_workspace(selected)
    workspaces_out = [project_to_workspace(p) for p in active_projects]

    docs = list(selected.get("documents") or [])
    indexed = sum(1 for d in docs if _is_indexed(d))
    total = len(docs)
    health_percent = int(round((indexed / total) * 100)) if total else 100
    awaiting = sum(
        1
        for r in (selected.get("spa_reports") or [])
        if str(r.get("status")) == "awaiting_review"
    )

    continue_working: list[ContinueWorkingOut] = []
    for document in sorted(
        docs,
        key=lambda d: str(d.get("uploaded_at") or d.get("updated_at") or ""),
        reverse=True,
    )[:3]:
        continue_working.append(
            ContinueWorkingOut(
                id=str(document.get("id") or document.get("filename")),
                title=str(document.get("filename") or "Document"),
                subtitle="Recent upload",
                kind="document",
                progress_percent=int(document.get("progress_percent") or 0) or None,
                updated_at=str(
                    document.get("uploaded_at") or document.get("updated_at") or _utc_now()
                ),
                href="/knowledge",
            )
        )
    for report in (selected.get("spa_reports") or [])[:2]:
        continue_working.append(
            ContinueWorkingOut(
                id=str(report.get("id")),
                title=str(report.get("name") or "Report"),
                subtitle=str(report.get("periodName") or "Report"),
                kind="report",
                updated_at=str(report.get("updatedAt") or report.get("createdAt") or _utc_now()),
                href=f"/reports/{report.get('id')}",
            )
        )

    user = UserOut(
        id=principal.user.id,
        email=principal.user.email,
        full_name=principal.user.display_name,
        email_verified=True,
    )

    return HomePageOut(
        user=user,
        greeting=_greeting(principal.user.display_name),
        active_workspace=workspace_out,
        workspaces=workspaces_out,
            notifications=[
            NotificationOut(
                id="n_dash",
                message=(
                    f"{dash['workspace_count']} workspaces · "
                    f"{dash['document_count']} documents · "
                    f"{dash['indexed_percent']}% indexed"
                ),
                level="info",
                created_at=_utc_now(),
                read=False,
            )
        ],
        unread_notification_count=1 if dash["document_count"] else 0,
        quick_actions=[
            {
                "id": "qa_upload",
                "label": "Upload documents",
                "description": "Add files to the library",
                "icon": "upload",
                "href": "/knowledge?upload=1",
            },
            {
                "id": "qa_report",
                "label": "Generate report",
                "description": "Create a workspace report",
                "icon": "report",
                "href": "/reports/new",
            },
            {
                "id": "qa_studio",
                "label": "Ask Intelligence Studio",
                "description": "Question your corpus",
                "icon": "copilot",
                "href": "/copilot",
            },
            {
                "id": "qa_export",
                "label": "Open reports",
                "description": "Export Word, PDF, or PowerPoint",
                "icon": "export",
                "href": "/reports",
            },
        ],
        continue_working=continue_working,
        insights_overview=WorkspaceInsightsOverviewOut(
            health_percent=health_percent,
            new_insight_count=len(dash["recent_conversations"]),
            reports_awaiting_review=awaiting,
            last_updated=_utc_now(),
        ),
        dashboard=HomeDashboardOut(
            metrics=dash["metrics"],
            recent_uploads=dash["recent_uploads"],
            recent_reports=dash["recent_reports"],
            recent_conversations=dash["recent_conversations"],
        ),
        search={
            "recentSearches": [],
            "suggestedActions": [
                {
                    "id": "sa1",
                    "label": "Generate a board report",
                    "href": "/reports/new",
                },
                {
                    "id": "sa2",
                    "label": "Ask Intelligence Studio",
                    "href": "/copilot",
                },
            ],
            "recentReports": [
                {
                    "id": item.id,
                    "label": item.title,
                    "meta": item.meta,
                    "href": item.href,
                }
                for item in dash["recent_reports"][:4]
            ],
            "recentWorkspaces": [
                {
                    "id": str(p.get("id")),
                    "label": str(p.get("name") or "Workspace"),
                    "href": f"/workspaces/{p.get('id')}/overview",
                }
                for p in active_projects[:4]
            ],
        },
        reports_awaiting_review=[],
        insights={
            "brief": {
                "date": _utc_now(),
                "greeting": "Here is what matters today",
                "items": [
                    {
                        "id": "b1",
                        "headline": (
                            f"{dash['document_count']} documents across "
                            f"{dash['workspace_count']} workspaces"
                        ),
                        "detail": (
                            f"{dash['indexed_percent']}% indexed and ready "
                            "for Intelligence Studio."
                        ),
                        "priority": "high",
                        "href": "/knowledge",
                    }
                ],
            },
            "recommendations": [],
            "recentActivity": [],
            "health": {
                "overallPercent": health_percent,
                "status": "ready" if health_percent >= 80 else "warning",
                "indicators": [
                    {
                        "status": "ready" if health_percent >= 80 else "warning",
                        "icon": "index",
                        "message": f"{indexed}/{total} documents indexed",
                    }
                ],
                "lastUpdated": _utc_now(),
            },
            "team": [],
            "organizationalIntelligence": [],
            "items": [],
        },
    )
