"""
Reports routes — generate, save, export (Word / PDF / PowerPoint).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

import config
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from api.auth_jwt import AuthenticatedPrincipal
from models.report_data import ReportData
from models.user import User
from api.deps import get_current_user, get_principal, user_request_scope
from api.schemas import (
    GenerateReportBody,
    ReportDetailOut,
    ReportPeriodOut,
    ReportTemplateOut,
    SaveReportBody,
)
from services.branding_service import BrandingService
from services.export_service import ExportService
from services.plan_service import PlanService
from services.premium_export_service import PremiumExportService, ReportExportContext
from services.profile_service import ProfileService
from services.project_service import ProjectService
from services.report_chart_data import extract_chart_data
from services.report_document import report_data_from_markdown
from services.report_service import ReportService
from services.spa_report_generation_service import (
    PERIODS,
    TEMPLATES,
    SpaReportGenerationService,
    template_by_id,
)
from services.usage_service import UsageLimitError, UsageService

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


_FIND_REPORT_RETRY_DELAYS_SECONDS = (0.3, 0.6, 1.0)


def _find_report(
    workspace_id: str, principal: AuthenticatedPrincipal, report_id: str
) -> dict[str, Any]:
    """The frontend's golden path calls save (this helper) immediately
    after generate() returns. Both reads go through a fresh storage
    listing (ReportService.get_reports -> FileStore.list_files), which on
    an eventually-consistent storage backend can briefly lag behind a
    write that already succeeded — retry a few times before surfacing a
    404, rather than failing a report that was, in fact, just created."""

    for delay in (0.0, *_FIND_REPORT_RETRY_DELAYS_SECONDS):
        if delay:
            time.sleep(delay)
        for report in _reports(workspace_id, principal):
            if str(report.get("id")) == report_id:
                return report
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found.")


def _locked_export_formats(principal: AuthenticatedPrincipal) -> dict[str, str]:
    with user_request_scope(principal):
        return PlanService(access_token=principal.access_token).locked_export_formats()


def _report_out(
    raw: dict[str, Any],
    *,
    locked_export_formats: dict[str, str] | None = None,
) -> ReportDetailOut:
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
        locked_export_formats=locked_export_formats or {},
    )


@router.get("/report-templates", response_model=list[ReportTemplateOut])
def list_templates(
    workspace_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[ReportTemplateOut]:
    _get_project(principal, workspace_id)
    with user_request_scope(principal):
        available = set(
            PlanService(access_token=principal.access_token).get_available_report_types()
        )
    return [
        ReportTemplateOut(
            **item,
            locked=item["name"] not in available,
            required_plan=(
                config.REPORT_TYPE_MIN_PLAN.get(item["name"])
                if item["name"] not in available
                else None
            ),
        )
        for item in TEMPLATES
    ]


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
    locked = _locked_export_formats(principal)
    items = [
        _report_out(item, locked_export_formats=locked)
        for item in _reports(workspace_id, principal)
    ]
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
            UsageService(access_token=principal.access_token).check_can_generate_report()
        except UsageLimitError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        template = template_by_id(body.template_id)
        plans = PlanService(access_token=principal.access_token)
        if template["name"] not in plans.get_available_report_types():
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=(
                    f'"{template["name"]}" requires a higher plan. '
                    f"Your current plan is {plans.get_plan_config()['label']}."
                ),
            )

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
        UsageService(access_token=principal.access_token).record_report_generated()
    return _report_out(record, locked_export_formats=_locked_export_formats(principal))


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def get_report(
    workspace_id: str,
    report_id: str,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> ReportDetailOut:
    _get_project(principal, workspace_id)
    report = _find_report(workspace_id, principal, report_id)
    return _report_out(report, locked_export_formats=_locked_export_formats(principal))


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
    return _report_out(report, locked_export_formats=_locked_export_formats(principal))


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

    # Phase C.1: reload the full ReportData saved at generation time
    # (metrics["tables"], charts, metadata["report_plan"]) rather than
    # reconstructing a bare-bones one from markdown text alone — without
    # this, export-time chart/data logic saw an empty report.metrics and
    # could fall back to less trustworthy narrative-derived chart data.
    # Older reports saved before this field existed simply have no
    # "reportData" key, so `stored` is None and behavior is unchanged.
    stored = ReportData.from_dict(report.get("reportData")) if report.get("reportData") else None
    report_data = report_data_from_markdown(
        content,
        report_type=str(report.get("reportType") or report.get("name") or "Report"),
        title=str(report.get("name") or "Report"),
        source_documents=list(report.get("sourceDocuments") or []),
        stored=stored,
    )
    # Diagnostic (see spa_report_generation_service.py's chart-eligibility
    # logging): a real Financial Analysis report confirmed generating charts
    # correctly (visualizations present in the saved markdown's embedded
    # REPORT_CHARTS block) still exported with zero chart images. Logging
    # each candidate charts source here to see exactly where between
    # generation and export the visualizations get dropped.
    embedded_for_diagnostic = extract_chart_data(content)
    logger.warning(
        "Export chart source report_id=%s has_reportData=%s "
        "stored_viz_count=%s embedded_viz_count=%s final_viz_count=%s",
        report_id,
        report.get("reportData") is not None,
        len((stored.charts or {}).get("visualizations") or []) if stored else None,
        len(embedded_for_diagnostic.get("visualizations") or []),
        len((report_data.charts or {}).get("visualizations") or []),
    )

    with user_request_scope(principal):
        plans = PlanService(access_token=principal.access_token)
        if format == "docx" and not plans.has_feature("word_export"):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Word export requires the Starter plan or higher.",
            )
        if format == "pptx" and not plans.can_use_pptx_export():
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="PowerPoint export requires the Professional plan or higher.",
            )

        custom_logo_bytes: bytes | None = None
        if plans.can_use_custom_branding():
            logo_key = ProfileService(
                access_token=principal.access_token
            ).get_branding_logo_key()
            if logo_key:
                custom_logo_bytes = BrandingService(
                    access_token=principal.access_token
                ).load_logo_bytes(logo_key)

        context = ReportExportContext(
            project_id=workspace_id,
            project_name=str(project.get("name") or "Workspace"),
            report=report_data,
            reporting_period=str(report.get("periodName") or "Not specified"),
            show_watermark=plans.show_watermark(),
            custom_logo_bytes=custom_logo_bytes,
        )

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
