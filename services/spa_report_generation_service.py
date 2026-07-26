"""
SPA report generation: gather sources → OpenAI → save markdown report.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

from models.report_data import ReportData
from services.document_service import DocumentService
from services.report_service import ReportService

logger = logging.getLogger(__name__)

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

TEMPLATES: list[dict[str, str]] = [
    {
        "id": "executive_summary",
        "name": "Executive Summary",
        "description": "Concise leadership brief with key findings and actions.",
    },
    {
        "id": "board_report",
        "name": "Board Report",
        "description": "Board-ready narrative with risks, KPIs, and recommendations.",
    },
    {
        "id": "management_report",
        "name": "Management Report",
        "description": "Operating review covering performance, issues, and next steps.",
    },
    {
        "id": "financial_analysis",
        "name": "Financial Analysis",
        "description": "Margin, revenue, and variance analysis from workspace evidence.",
    },
    {
        "id": "risk_assessment",
        "name": "Risk Assessment Report",
        "description": "Risk register style summary with mitigations.",
    },
    {
        "id": "full_report",
        "name": "Full Report",
        "description": "Comprehensive multi-section report across the corpus.",
    },
]

PERIODS: list[dict[str, str]] = [
    {"id": "weekly", "name": "Weekly Report"},
    {"id": "monthly", "name": "Monthly Report"},
    {"id": "quarterly", "name": "Quarterly Report"},
    {"id": "annual", "name": "Annual Report"},
    {"id": "custom", "name": "Custom / Ad hoc"},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(text: str, limit: int = 3500) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def template_by_id(template_id: str) -> dict[str, str]:
    for item in TEMPLATES:
        if item["id"] == template_id:
            return item
    return TEMPLATES[0]


def period_by_id(period_id: str) -> dict[str, str]:
    for item in PERIODS:
        if item["id"] == period_id:
            return item
    return PERIODS[2]


class SpaReportGenerationService:
    def __init__(self, *, access_token: str | None = None) -> None:
        self._access_token = access_token
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._client = OpenAI(api_key=api_key) if api_key else None

    def _gather_sources(
        self, workspace_id: str, project: dict[str, Any]
    ) -> list[dict[str, str]]:
        docs = list(project.get("documents") or [])
        service = DocumentService(access_token=self._access_token)
        sources: list[dict[str, str]] = []
        for document in docs[:12]:
            filename = str(document.get("filename") or "")
            if not filename:
                continue
            try:
                text = service.read_document_text(workspace_id, filename)
            except Exception:
                text = ""
            if not text.strip():
                continue
            sources.append({"filename": filename, "excerpt": _clip(text, 2500)})
        return sources

    def _fallback_markdown(
        self,
        *,
        title: str,
        period_name: str,
        template_name: str,
        sources: list[dict[str, str]],
    ) -> str:
        bullets = "\n".join(
            f"- {src['filename']}: {_clip(src['excerpt'], 180)}" for src in sources[:6]
        ) or "- No indexed source text was available."
        return (
            f"# {title}\n\n"
            f"**Template:** {template_name}  \n"
            f"**Period:** {period_name}\n\n"
            "## Executive Summary\n\n"
            "This draft was generated from the active workspace library. "
            "Review findings below and export when ready.\n\n"
            "## Key Findings\n\n"
            f"{bullets}\n\n"
            "## Recommendations\n\n"
            "1. Validate priority findings with owners.\n"
            "2. Confirm open actions and deadlines.\n"
            "3. Refresh source documents if material context is missing.\n"
        )

    def _generate_markdown(
        self,
        *,
        title: str,
        period_name: str,
        template_name: str,
        sources: list[dict[str, str]],
    ) -> str:
        if not self._client or not sources:
            return self._fallback_markdown(
                title=title,
                period_name=period_name,
                template_name=template_name,
                sources=sources,
            )

        evidence = "\n\n".join(
            f"### {src['filename']}\n{src['excerpt']}" for src in sources
        )
        prompt = (
            f"Write a {template_name} for period '{period_name}'.\n"
            f"Title: {title}\n"
            "Use ONLY the evidence. Output GitHub-flavoured markdown with:\n"
            "- Executive Summary\n"
            "- Key Findings\n"
            "- Analysis\n"
            "- Risks / Issues\n"
            "- Recommendations\n"
            "- Sources\n\n"
            f"Evidence:\n{evidence}"
        )
        try:
            response = self._client.chat.completions.create(
                model=CHAT_MODEL,
                temperature=0.3,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are DataDumpAI Reports. Produce clear executive markdown."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            logger.exception("OpenAI report generation failed; using fallback")

        return self._fallback_markdown(
            title=title,
            period_name=period_name,
            template_name=template_name,
            sources=sources,
        )

    def generate(
        self,
        *,
        workspace_id: str,
        project: dict[str, Any],
        template_id: str,
        period_id: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        template = template_by_id(template_id)
        period = period_by_id(period_id)
        workspace_name = str(project.get("name") or "Workspace")
        report_title = (title or "").strip() or f"{template['name']} — {period['name']}"
        sources = self._gather_sources(workspace_id, project)
        markdown = self._generate_markdown(
            title=report_title,
            period_name=period["name"],
            template_name=template["name"],
            sources=sources,
        )
        report = ReportData(
            report_type=template["name"],
            title=report_title,
            narrative=markdown,
            source_documents=[src["filename"] for src in sources],
            metadata={
                "period_id": period_id,
                "period_name": period["name"],
                "template_id": template_id,
                "template_name": template["name"],
                "workspace_name": workspace_name,
            },
            executive_summary={"text": _clip(markdown, 500)},
        )

        saved = ReportService.save_report(
            workspace_id,
            report_title,
            report=report,
            source_documents=report.source_documents,
        )

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        record = {
            "id": report_id,
            "filename": saved["filename"],
            "name": report_title,
            "path": saved["path"],
            "size": saved["size"],
            "createdAt": now,
            "updatedAt": now,
            "reportType": template["name"],
            "templateId": template_id,
            "periodId": period_id,
            "periodName": period["name"],
            "status": "draft",
            "content": markdown,
            "sourceDocuments": report.source_documents,
        }

        reports = list(project.get("spa_reports") or [])
        reports.insert(0, record)
        project["spa_reports"] = reports
        return record
