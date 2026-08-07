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


_FENCE_RE = re.compile(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", re.DOTALL)


def _strip_wrapping_code_fence(text: str) -> str:
    """Chat models sometimes wrap an entire markdown answer in a single
    ```markdown ... ``` fence — strip that wrapper so the fence markers
    don't end up rendered as literal text in the report."""

    match = _FENCE_RE.match(text.strip())
    return match.group(1).strip() if match else text


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
            sources.append({"filename": filename, "excerpt": _clip(text, 6000)})
        return sources

    def _fallback_markdown(
        self,
        *,
        title: str,
        period_name: str,
        template_name: str,
        sources: list[dict[str, str]],
        instructions: str | None = None,
    ) -> str:
        bullets = "\n".join(
            f"- {src['filename']}: {_clip(src['excerpt'], 180)}" for src in sources[:6]
        ) or "- No indexed source text was available."
        instructions_section = (
            f"## User Instructions\n\n{instructions.strip()}\n\n" if instructions and instructions.strip() else ""
        )
        return (
            f"**Template:** {template_name}  \n"
            f"**Period:** {period_name}\n\n"
            f"{instructions_section}"
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
        instructions: str | None = None,
    ) -> str:
        if not self._client or not sources:
            return self._fallback_markdown(
                title=title,
                period_name=period_name,
                template_name=template_name,
                sources=sources,
                instructions=instructions,
            )

        source_count = len(sources)
        evidence = "\n\n".join(
            f"### Document {index} of {source_count} — {src['filename']}\n{src['excerpt']}"
            for index, src in enumerate(sources, start=1)
        )
        source_filenames = ", ".join(f'"{src["filename"]}"' for src in sources)
        instructions_line = (
            f"\nThe user specifically asked for: {instructions.strip()}\n"
            "Prioritize this request while still grounding every claim in the evidence below.\n"
            if instructions and instructions.strip()
            else ""
        )
        synthesis_requirement = (
            (
                f"This workspace contains {source_count} documents ({source_filenames}). "
                "Your central job is to COMBINE them into one coherent picture, not summarize "
                "them one at a time. Explicitly identify what is consistent across multiple "
                "documents, what changed between the earliest and the most recent, what recurs "
                "across several sources versus what appears in only one, and any contradictions "
                "between sources. A report that meaningfully engages with only one document while "
                "glossing over the rest has failed the task — every one of the "
                f"{source_count} documents must be referenced by name at least once. "
                "If a finding is corroborated by more than one document, say so and cite all of "
                "them; that kind of cross-document corroboration is the most valuable thing you "
                "can produce.\n\n"
            )
            if source_count > 1
            else ""
        )
        prompt = (
            f"Write a {template_name} titled \"{title}\" covering the period '{period_name}', "
            "using only the evidence provided below.\n"
            f"{instructions_line}\n"
            f"{synthesis_requirement}"
            "Go beyond summarizing — synthesize. For every major point, explain not just what "
            "happened but why it matters, what pattern or trend it fits into, what changed since "
            "prior context (if evidence shows it), and what the implication is for decision-makers. "
            "Every non-obvious claim should be traceable to a specific source document by name.\n\n"
            "Structure the report in GitHub-flavoured markdown with exactly these sections, in order. "
            "Do not include a top-level title heading — start directly at the first section below; "
            "the document title is rendered separately by the export layer.\n\n"
            "## Executive Summary\n"
            "3-5 sentences a board member could read alone and understand the whole picture: "
            "the overall situation, the most important finding, and the headline recommendation.\n\n"
            "## Key Findings\n"
            "4-8 findings as sub-headings, drawing across the full set of documents (not "
            "clustered from just one). For each: a bolded one-line finding, then 2-4 sentences of "
            "explanation, then a line `**Confidence:** High/Medium/Low — <one-clause reason>` reflecting "
            "how well-supported the finding is by the evidence, then `**Source:** <filename(s), "
            "plural if more than one document supports it>`.\n\n"
            "## Detailed Analysis\n"
            "The narrative connective tissue between findings — trends across documents, recurring "
            "themes, contradictions or inconsistencies between sources, what changed over time if "
            "the documents span a period, and context a reader needs to interpret the findings "
            "correctly. This section is where cross-document synthesis should be most visible.\n\n"
            "## Risks & Issues\n"
            "Concrete risks or open problems surfaced by the evidence, each with a brief note on "
            "likely impact.\n\n"
            "## Opportunities\n"
            "Positive openings, efficiencies, or strategic options the evidence points to. If the "
            "evidence contains none, state that plainly rather than inventing any.\n\n"
            "## Strategic Recommendations\n"
            "A markdown numbered list of specific, actionable next steps, ordered by priority — not "
            "generic advice, but recommendations that follow directly from the findings above. Each "
            "recommendation MUST start a new line with '1. ', '2. ', etc. — never run multiple "
            "recommendations together in one paragraph.\n\n"
            "## Conclusion\n"
            "2-3 sentences closing the report and restating what should happen next.\n\n"
            "Do not wrap your answer in a code fence. Output raw markdown starting directly with the "
            "## Executive Summary heading.\n\n"
            f"Evidence:\n{evidence}"
        )
        try:
            response = self._client.chat.completions.create(
                model=CHAT_MODEL,
                temperature=0.3,
                max_tokens=4096,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are DataDumpAI's executive reporting analyst. Organizations bring "
                            "you raw documents — meeting minutes, board papers, policies, financials — "
                            "and you turn them into executive intelligence, not summaries. Your "
                            "signature skill is multi-document synthesis: when given several "
                            "documents, you connect them — recurring issues across meetings, "
                            "positions that shifted over time, findings corroborated by more than one "
                            "source — rather than writing about each document in isolation or letting "
                            "one document dominate. For every point you make, answer not just 'what "
                            "happened' but 'why it matters', 'what pattern it's part of', and 'what "
                            "management should do about it'. Write in clear, confident, "
                            "board-appropriate prose. Never fabricate a figure, name, date, or claim "
                            "that isn't in the evidence — if the evidence is thin on a section, say so "
                            "briefly rather than padding with generic text."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                return _strip_wrapping_code_fence(text)
        except Exception:
            logger.exception("OpenAI report generation failed; using fallback")

        return self._fallback_markdown(
            title=title,
            period_name=period_name,
            template_name=template_name,
            sources=sources,
            instructions=instructions,
        )

    def generate(
        self,
        *,
        workspace_id: str,
        project: dict[str, Any],
        template_id: str,
        period_id: str,
        title: str | None = None,
        instructions: str | None = None,
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
            instructions=instructions,
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
            access_token=self._access_token,
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
            "instructions": instructions,
        }

        # Persist the full SPA-shaped record into the report's metadata
        # sidecar so it survives past this request — save_report() above
        # already wrote a narrower metadata file; this overwrites it with
        # everything get_report()/list_reports() need (id, status, etc).
        ReportService.save_report_metadata(
            workspace_id,
            saved["filename"],
            report_type=template["name"],
            source_documents=report.source_documents,
            report_data=record,
            access_token=self._access_token,
        )

        return record
