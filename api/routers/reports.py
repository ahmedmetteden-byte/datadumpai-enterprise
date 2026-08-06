"""
Reports routes — generate, save, export (Word / PDF / PowerPoint).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from api.auth_jwt import AuthenticatedPrincipal
from models.user import User
from api.deps import get_current_user, get_principal, user_request_scope
from api.schemas import (
    GenerateReportBody,
    ReportDetailOut,
    ReportPeriodOut,
    ReportTemplateOut,
    SaveReportBody,
)
from services.export_service import ExportService
from services.premium_export_service import PremiumExportService, ReportExportContext
from services.project_service import ProjectService
from services.report_document import report_data_from_markdown
from services.report_service import ReportService
from services.spa_report_generation_service import (
    PERIODS,
    TEMPLATES,
    SpaReportGenerationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["reports"])


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


def _reports(
    workspace_id: str, principal: AuthenticatedPrincipal
) -> list[dict[str, Any]]:
    """Reports generated via the SPA, sourced from their persisted metadata
    sidecar (not `project["reports"]`, which is the legacy Streamlit path)."""

    with user_request_scope(principal):
        entries = ReportService.get_reports(
            workspace_id, access_token=principal.access_token
        )
    return [
        entry["report_data"]
        for entry in entries
        if isinstance(entry.get("report_data"), dict)
    ]


def _find_report(
    workspace_id: str, principal: AuthenticatedPrincipal, report_id: str
) -> dict[str, Any]:
    for report in _reports(workspace_id, principal):
        if str(report.get("id")) == report_id:
            return report
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found.")


def _report_out(raw: dict[str, Any]) -> ReportDetailOut:
    return ReportDetailOut(
        id=str(raw["id"]),
        filename=str(raw.get("filename") or ""),
        name=str(raw.get("name") or "Report"),
        path=str(raw.get("path") or ""),
        size=int(raw.get("size") or 0),
        created_at=str(raw.get("createdAt") or ""),
        updated_at=raw.get("updatedAt"),
        report_type=raw.get("reportType"),
        template_id=raw.get("templateId"),
        period_id=raw.get("periodId"),
        period_name=raw.get("periodName"),
        status=raw.get("status") or "draft",
        content=raw.get("content"),
        source_documents=list(raw.get("sourceDocuments") or []),
        instructions=raw.get("instructions"),
    )


@router.get("/report-templates", response_model=list[ReportTemplateOut])
def list_templates(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[ReportTemplateOut]:
    _get_project(principal, workspace_id)
    return [ReportTemplateOut(**item) for item in TEMPLATES]


@router.get("/report-periods", response_model=list[ReportPeriodOut])
def list_periods(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[ReportPeriodOut]:
    _get_project(principal, workspace_id)
    return [ReportPeriodOut(**item) for item in PERIODS]


@router.get("/reports", response_model=list[ReportDetailOut])
def list_reports(
    workspace_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[ReportDetailOut]:
    _get_project(principal, workspace_id)
    items = [_report_out(item) for item in _reports(workspace_id, principal)]
    if status_filter == "awaiting_review":
        items = [item for item in items if item.status == "awaiting_review"]
    return items


@router.post(
    "/reports/generate",
    response_model=ReportDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_report(
    workspace_id: str,
    body: GenerateReportBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> ReportDetailOut:
    project = _get_project(principal, workspace_id)
    with user_request_scope(principal):
        try:
            record = SpaReportGenerationService(
                access_token=principal.access_token
            ).generate(
                workspace_id=workspace_id,
                project=project,
                template_id=body.template_id,
                period_id=body.period_id,
                title=body.title,
                instructions=body.instructions,
            )
        except Exception as exc:
            logger.exception("Report generation failed workspace=%s", workspace_id)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Report generation failed: {exc}",
            ) from exc
    return _report_out(record)


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def get_report(
    workspace_id: str,
    report_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> ReportDetailOut:
    _get_project(principal, workspace_id)
    return _report_out(_find_report(workspace_id, principal, report_id))


@router.post("/reports/{report_id}/save", response_model=ReportDetailOut)
def save_report(
    workspace_id: str,
    report_id: str,
    body: SaveReportBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> ReportDetailOut:
    _get_project(principal, workspace_id)
    report = _find_report(workspace_id, principal, report_id)
    report["status"] = body.status
    from datetime import datetime, timezone

    report["updatedAt"] = datetime.now(timezone.utc).isoformat()
    with user_request_scope(principal):
        ReportService.save_report_metadata(
            workspace_id,
            str(report["filename"]),
            report_type=str(report.get("reportType") or ""),
            source_documents=list(report.get("sourceDocuments") or []),
            report_data=report,
            access_token=principal.access_token,
        )
    return _report_out(report)


@router.get("/reports/{report_id}/export")
def export_report(
    workspace_id: str,
    report_id: str,
    format: Literal["docx", "pdf", "pptx"] = Query(default="docx"),
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> Response:
    project = _get_project(principal, workspace_id)
    report = _find_report(workspace_id, principal, report_id)
    content = str(report.get("content") or "").strip()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Report has no content.")

    report_data = report_data_from_markdown(
        content,
        report_type=str(report.get("reportType") or report.get("name") or "Report"),
        title=str(report.get("name") or "Report"),
    )

    context = ReportExportContext(
        project_id=workspace_id,
        project_name=str(project.get("name") or "Workspace"),
        report=report_data,
        reporting_period=str(report.get("periodName") or "Not specified"),
    )

    with user_request_scope(principal):
        premium = PremiumExportService(
            ExportService(access_token=principal.access_token)
        )
        try:
            if format == "pdf":
                result = premium.export_executive_pdf(context)
            elif format == "pptx":
                result = premium.export_presentation(context)
            else:
                result = premium.export_docx(context)
        except Exception as exc:
            logger.exception("Export failed report=%s format=%s", report_id, format)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    data = result.get("data") or b""
    filename = str(result.get("filename") or f"report.{format}")
    mime = str(result.get("mime_type") or "application/octet-stream")
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
