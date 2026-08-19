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
from services.quantitative_analysis_service import (
    extract_metric_tables,
    format_metrics_for_evidence,
)
from services.report_retrieval_service import build_facet_queries, retrieve_grouped_sources
from services.report_service import ReportService
from services.visualization_engine import apply_visualizations

logger = logging.getLogger(__name__)

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

# Kill switch: instant rollback to the whole-document fallback via config,
# no deploy needed, if retrieval-based source selection is ever in question.
REPORT_RETRIEVAL_ENABLED = os.getenv("REPORT_RETRIEVAL_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}

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


_TABLE_ROW = re.compile(r"^\|.*\|$")


def _clip(text: str, limit: int = 3500) -> str:
    """Collapse whitespace to normalize messy extraction artifacts (PDF
    line-wraps, repeated spaces) while preserving markdown table
    structure — collapsing a table's one-row-per-line layout onto a
    single line makes it unparseable by report_markdown_renderer.
    parse_markdown_blocks(), which quantitative_analysis_service.py
    depends on to find real tables in retrieved evidence. Mirrors
    services/report_retrieval_service.py's identical fix."""

    segments: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        kind = "table" if _TABLE_ROW.match(line.strip()) else "prose"
        if segments and segments[-1][0] == kind:
            segments[-1][1].append(line)
        else:
            segments.append((kind, [line]))

    rendered: list[str] = []
    for kind, lines in segments:
        if kind == "table":
            rendered.append("\n".join(line.strip() for line in lines))
        else:
            collapsed = re.sub(r"\s+", " ", " ".join(lines)).strip()
            if collapsed:
                rendered.append(collapsed)

    cleaned = "\n\n".join(rendered).strip()

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

    def _gather_sources_legacy(
        self, workspace_id: str, docs: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Read each document's full text directly, in storage order, up to
        a hard cap. This is the pre-retrieval behavior, kept verbatim as
        the safety-net fallback for _gather_sources — used whenever
        retrieval can't help (nothing indexed yet for this project, an
        embedding/Qdrant failure, or REPORT_RETRIEVAL_ENABLED=false). It
        can never make a report worse than before retrieval existed."""

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

    def _find_previous_report(
        self, workspace_id: str, template_id: str
    ) -> dict[str, Any] | None:
        """Most recent previously-saved SPA report for this workspace+template,
        or None if there isn't one (brand-new workspace, first report of this
        template, or only legacy/non-SPA reports exist). Must run before the
        report currently being generated is saved, so it can never match
        itself.

        Note: ReportService.get_reports()'s top-level "created_at" is computed
        at call time, not the report's actual creation time — ordering must
        use report_data["createdAt"] instead, which is written once by
        generate() and never touched again.
        """

        try:
            entries = ReportService.get_reports(
                workspace_id, access_token=self._access_token
            )
        except Exception:
            logger.exception(
                "Failed to load prior reports for comparison workspace=%s",
                workspace_id,
            )
            return None

        candidates: list[dict[str, Any]] = []
        for entry in entries:
            data = entry.get("report_data")
            if not isinstance(data, dict):
                continue  # legacy Streamlit report, no report_data sidecar
            if data.get("templateId") != template_id:
                continue
            content = data.get("content")
            created_at = data.get("createdAt")
            if not isinstance(content, str) or not content.strip():
                continue
            if not isinstance(created_at, str) or not created_at:
                continue
            candidates.append(data)

        if not candidates:
            return None

        candidates.sort(key=lambda d: d["createdAt"], reverse=True)
        return candidates[0]

    def _gather_sources(
        self,
        workspace_id: str,
        project: dict[str, Any],
        *,
        template: dict[str, str],
        period: dict[str, str],
        instructions: str | None = None,
    ) -> list[dict[str, str]]:
        docs = list(project.get("documents") or [])
        if not docs:
            return []

        if REPORT_RETRIEVAL_ENABLED:
            try:
                queries = build_facet_queries(
                    template_name=template["name"],
                    template_description=template.get("description", ""),
                    period_name=period["name"],
                    instructions=instructions,
                )
                sources = retrieve_grouped_sources(workspace_id, queries)
                if sources:
                    return sources
            except Exception:
                logger.exception(
                    "Retrieval-based source gathering failed workspace=%s; "
                    "falling back to whole-document read",
                    workspace_id,
                )

        return self._gather_sources_legacy(workspace_id, docs)

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
        previous_report: dict[str, Any] | None = None,
        metric_tables: list[dict[str, Any]] | None = None,
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
        calculated_metrics_context = format_metrics_for_evidence(metric_tables or [])
        calculated_metrics_requirement = (
            "Where the evidence includes a 'Verified Calculations' block, treat those figures "
            "as ground truth — cite them exactly as given rather than re-deriving or estimating "
            "your own percentage or growth figures from the raw numbers in the source text.\n\n"
            if calculated_metrics_context
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
        comparison_context = ""
        comparison_requirement = ""
        if (
            previous_report
            and isinstance(previous_report.get("content"), str)
            and previous_report["content"].strip()
        ):
            previous_excerpt = _clip(previous_report["content"], 4000)
            previous_created = previous_report.get("createdAt") or "an earlier date"
            comparison_context = (
                f"\n\n### Previous Report (for comparison only — {previous_created})\n"
                "This is the most recent prior report of the same type in this workspace. "
                "It is provided ONLY so you can identify what has changed since it was written. "
                "Do not treat it as evidence for new facts, and do not cite it as a source for "
                "findings in any other section — only the 'Changes Since Last Report' section "
                f"should reference it.\n{previous_excerpt}"
            )
            comparison_requirement = (
                "## Changes Since Last Report\n"
                "Compare this report against the previous report supplied above. Call out: "
                "what is new since then, what has been resolved or is no longer present, and "
                "how any key figures moved (cite both the old and new number when both reports "
                "state one). If nothing material changed, say so plainly rather than inventing "
                "a difference. Do not use this section to introduce findings that belong in "
                "Key Findings — its purpose is strictly the delta between the two reports.\n\n"
            )
        prompt = (
            f"Write a {template_name} titled \"{title}\" covering the period '{period_name}', "
            "using only the evidence provided below.\n"
            f"{instructions_line}\n"
            f"{synthesis_requirement}"
            f"{calculated_metrics_requirement}"
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
            f"{comparison_requirement}"
            "## Conclusion\n"
            "2-3 sentences closing the report and restating what should happen next.\n\n"
            "Do not wrap your answer in a code fence. Output raw markdown starting directly with the "
            "## Executive Summary heading.\n\n"
            f"Evidence:\n{evidence}{calculated_metrics_context}{comparison_context}"
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
        previous_report = self._find_previous_report(workspace_id, template_id)
        sources = self._gather_sources(
            workspace_id,
            project,
            template=template,
            period=period,
            instructions=instructions,
        )
        metric_tables = extract_metric_tables(sources)
        markdown = self._generate_markdown(
            title=report_title,
            period_name=period["name"],
            template_name=template["name"],
            sources=sources,
            instructions=instructions,
            previous_report=previous_report,
            metric_tables=metric_tables,
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
            metrics={"tables": metric_tables} if metric_tables else {},
            executive_summary={"text": _clip(markdown, 500)},
        )

        report = apply_visualizations(
            report,
            user_report_type=template["name"],
            document_text=markdown,
            reporting_period=period["name"],
            force_generate=True,
        )
        markdown = report.to_markdown()

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
