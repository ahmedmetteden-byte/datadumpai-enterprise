"""
SPA report generation: gather sources → OpenAI → save markdown report.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from openai import OpenAI

from models.report_data import ReportData
from services.document_service import DocumentService
from services.quantitative_analysis_service import (
    extract_metric_tables,
    format_metrics_for_evidence,
)
from services.report_plan_service import (
    REPORT_PLAN_ENABLED,
    ReportPlan,
    build_report_plan,
    render_plan_for_prompt,
    select_dashboard_items,
)
from services.plan_service import PlanService
from services.report_qc_service import apply_deterministic_corrections, run_qc_pass
from services.report_retrieval_service import (
    build_facet_queries,
    compute_coverage_gaps,
    detect_all_documents_intent,
    retrieve_grouped_sources,
)
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

# Rolling window (relative to generation time) each named period scopes
# source documents to, using upload time as the only period signal that
# exists — documents carry no metadata about which period their content
# covers. "custom" is intentionally absent: ad hoc reports are not windowed.
PERIOD_WINDOW_DAYS: dict[str, int] = {
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "annual": 365,
}

# Which report types are analytical enough to warrant charts (Phase C.1:
# corrects a Phase C regression that had incorrectly added Board Report and
# Management Report here). Executive Summary, Board Report, and Management
# Report are narrative types by design — a 1-3 priority brief, a
# governance-decision memo, and an operational review respectively — none
# of which is meant to carry chart images; selecting one of these must not
# silently produce the same chart-laden output as Financial Analysis / Risk
# Assessment / Full Report.
ANALYTICAL_TEMPLATE_IDS = {"financial_analysis", "risk_assessment", "full_report"}

# Section structure per report type, in output order. This is what makes
# each Report type option actually produce a differently-shaped document
# instead of the same 7-section report with only the title sentence
# changed. "changes_since_last" is inserted dynamically (see
# _generate_markdown) only when a comparable previous report exists.
TEMPLATE_SECTIONS: dict[str, list[str]] = {
    "executive_summary": [
        "executive_summary",
        "key_findings",
        "risks_issues",
        "strategic_recommendations",
    ],
    "board_report": [
        "executive_summary",
        "key_findings",
        "risks_issues",
        "strategic_recommendations",
        "conclusion",
    ],
    "management_report": [
        "executive_summary",
        "key_findings",
        "detailed_analysis",
        "risks_issues",
        "strategic_recommendations",
        "conclusion",
    ],
    "financial_analysis": [
        "executive_summary",
        "key_findings",
        "detailed_analysis",
        "risks_issues",
        "opportunities",
        "strategic_recommendations",
        "conclusion",
    ],
    "risk_assessment": [
        "executive_summary",
        "key_findings",
        "detailed_analysis",
        "risks_issues",
        "strategic_recommendations",
        "conclusion",
    ],
    "full_report": [
        "executive_summary",
        "key_findings",
        "detailed_analysis",
        "risks_issues",
        "opportunities",
        "strategic_recommendations",
        "conclusion",
    ],
}

SECTION_HEADINGS: dict[str, str] = {
    "executive_summary": "## Executive Summary",
    "key_findings": "## Key Findings",
    "detailed_analysis": "## Detailed Analysis",
    "risks_issues": "## Risks & Issues",
    "opportunities": "## Opportunities",
    "strategic_recommendations": "## Strategic Recommendations",
    "changes_since_last": "## Changes Since Last Report",
    "conclusion": "## Conclusion",
}

# Executive Summary and Board Report are meant to be genuinely brief, not
# just differently-sectioned — shrink the two length-bearing sections and
# the completion budget accordingly. Other types keep the original ranges.
EXEC_SUMMARY_LENGTH: dict[str, str] = {
    "executive_summary": "2-3 sentences",
    "board_report": "3-4 sentences",
}
KEY_FINDINGS_COUNT: dict[str, str] = {
    "executive_summary": "2-4 findings",
    "board_report": "3-5 findings",
}
TEMPLATE_MAX_TOKENS: dict[str, int] = {
    "executive_summary": 1600,
    "board_report": 2400,
    "management_report": 3200,
    "financial_analysis": 4096,
    "risk_assessment": 3200,
    "full_report": 4096,
}

# Who reads this report type and what they need it to do for them — the
# report's actual differentiation comes from acting on this, not from
# section headings alone. Injected near the top of the writer prompt.
TEMPLATE_AUDIENCE_PURPOSE: dict[str, str] = {
    "executive_summary": (
        "Audience: a board member or senior executive with a minute to spend. Purpose: give "
        "them only the 1-3 things that matter most right now and what to do about them — this "
        "is the shortest, most selective report type, not a compressed version of every "
        "finding.\n\n"
    ),
    "board_report": (
        "Audience: the board of directors, who govern and oversee but do not run day-to-day "
        "operations. Purpose: surface what the board specifically needs to decide, approve, or "
        "be aware of at a governance level — frame findings in terms of oversight and "
        "accountability, not operational detail a manager would already know.\n\n"
    ),
    "management_report": (
        "Audience: operating managers responsible for day-to-day performance. Purpose: a "
        "working review of performance, issues, and what needs to happen next inside the "
        "business — write for someone who will act on this directly, not for a governance "
        "body one level removed from operations.\n\n"
    ),
    "financial_analysis": (
        "Audience: finance leadership and executives evaluating financial performance. "
        "Purpose: explain WHY the numbers moved — margin, revenue, and variance drivers — not "
        "just restate them; every finding should connect a figure to its underlying financial "
        "driver wherever the evidence supports one.\n\n"
    ),
    "risk_assessment": (
        "Audience: risk owners and leadership accountable for identifying and mitigating "
        "exposure. Purpose: a risk-register-style account of what could go wrong, how material "
        "it is, and what is being done about it — the report exists to surface and size risk, "
        "not to give a balanced overview of performance.\n\n"
    ),
    "full_report": (
        "Audience: readers who need the complete picture in one document — the comprehensive "
        "reference version spanning financial, operational, and risk perspectives together. "
        "Purpose: breadth and completeness, not a narrow focus on any single lens.\n\n"
    ),
}

# Per-template guidance appended to the Strategic Recommendations section
# block — what kind of action each report type's recommendations must be.
TEMPLATE_RECOMMENDATION_STYLE: dict[str, str] = {
    "executive_summary": (
        "List at most 3 recommendations — only the highest-priority ones. Do not pad to fill "
        "more; a short, sharp list is the point of this report type.\n\n"
    ),
    "board_report": (
        "Each `**Action:**` must be phrased as the governance decision itself — start it with "
        "'Approve', 'Authorize', 'Direct management to', or 'Formally note' — never as the "
        "underlying operational task staff would carry out. For example, write 'Approve funding "
        "to expand claims processing capacity in the Western region' rather than 'Enhance claims "
        "processing capacity in the Western region' — the board approves the resourcing decision, "
        "it does not itself perform the operational work.\n\n"
    ),
    "management_report": (
        "Each recommendation must be something a manager can act on directly this reporting "
        "cycle — tie it to a concrete operational lever (staffing, process, vendor, workflow), "
        "not a strategic direction only executive leadership could set.\n\n"
    ),
    "financial_analysis": (
        "Each `**Action:**` sentence must open by naming the financial lever it pulls — pricing "
        "or rate adjustment, underwriting terms, cost/expense reduction, capital allocation, or "
        "product/channel mix — e.g. 'Adjust underwriting terms for the Western region to...' or "
        "'Reallocate claims-handling budget toward...'. A bare operational task with no named "
        "financial lever (e.g. 'Enhance claims processing capacity') is NOT acceptable here, even "
        "if the same finding also motivates the same action in another report type. The "
        "`**Rationale:**` must state the expected effect on a financial metric (margin, loss "
        "ratio, revenue, or cost) in addition to citing the finding.\n\n"
    ),
    "risk_assessment": (
        "Every recommendation must be a mitigation tied to a specific named risk from the "
        "Risks & Issues section above — never a general improvement with no corresponding "
        "stated risk.\n\n"
    ),
    "full_report": (
        "Cover the full range of priorities across findings, ordered by materiality — breadth "
        "across the whole evidence set is the goal for this report type, not a narrow focus.\n\n"
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_uploaded_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _document_period_timestamp(doc: dict[str, Any]) -> datetime | None:
    """The best available signal for which period a document belongs to:
    the user-tagged period_date (the date its content actually covers)
    when present, else uploaded_at as a fallback for untagged documents."""

    tagged = _parse_uploaded_at(str(doc.get("period_date") or ""))
    if tagged is not None:
        return tagged
    return _parse_uploaded_at(str(doc.get("uploaded_at") or ""))


def filter_documents_by_period(
    docs: list[dict[str, Any]], period_id: str
) -> list[dict[str, Any]]:
    """Narrow a workspace's documents to those whose period_date (or,
    absent that, uploaded_at) falls within the selected period's rolling
    window. Falls back to the full document set whenever the window would
    otherwise leave nothing to report on — a period filter must narrow
    evidence, never turn a report into an empty one."""

    window_days = PERIOD_WINDOW_DAYS.get(period_id)
    if window_days is None:  # "custom" / ad hoc, or an unrecognized id
        return docs

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    in_window = [
        doc
        for doc in docs
        if (parsed := _document_period_timestamp(doc)) is not None and parsed >= cutoff
    ]
    return in_window or docs


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
        self, workspace_id: str, template_id: str, period_id: str
    ) -> dict[str, Any] | None:
        """Most recent previously-saved SPA report for this workspace+
        template+period, or None if there isn't one (brand-new workspace,
        first report of this template/period, or only legacy/non-SPA
        reports exist). Must run before the report currently being
        generated is saved, so it can never match itself.

        Matching on period_id too (not just template_id) matters: without
        it, a Weekly report's "previous report" comparison could silently
        pick up the last Quarterly report of the same template, comparing
        against the wrong timeframe entirely.

        Note: ReportService.get_reports()'s top-level "created_at" is computed
        at call time, not the report's actual creation time — ordering must
        use report_data["createdAt"] instead, which is written once by
        generate() and never touched again.

        Phase 3 Step 2: every ad-hoc report shares the single literal
        period_id "custom" (there is no real date-range field for a
        custom period), so period_id matching alone cannot tell whether
        two ad-hoc requests actually cover the same scope — the previous
        ad-hoc report might be about something entirely unrelated. Rather
        than risk a "Changes Since Last Report" section comparing against
        an unrelated prior request, never auto-match a previous report
        for a custom-period report at all. Named periods (e.g. "Q1 2025")
        keep the existing behavior — their period_id genuinely
        differentiates them.
        """

        if period_id == "custom":
            return None

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
            if data.get("periodId") != period_id:
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
        docs: list[dict[str, Any]],
        *,
        template: dict[str, str],
        period: dict[str, str],
        instructions: str | None = None,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, str]]:
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
                # When the user explicitly asked for every document, or
                # explicitly selected a specific set of documents,
                # relevance ranking alone must not be allowed to silently
                # drop one that never scores in any facet query's top-K —
                # guarantee coverage rather than just retrieving the most
                # relevant evidence (see report_retrieval_service.py's
                # _ensure_document_coverage()).
                coverage_docs = (
                    docs if (document_ids or detect_all_documents_intent(instructions)) else None
                )
                sources = retrieve_grouped_sources(
                    workspace_id,
                    queries,
                    documents=coverage_docs,
                    document_ids=document_ids,
                )
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
        template_id: str,
        template_name: str,
        sources: list[dict[str, str]],
        instructions: str | None = None,
        previous_report: dict[str, Any] | None = None,
        metric_tables: list[dict[str, Any]] | None = None,
        report_plan: ReportPlan | None = None,
        coverage_gaps: list[dict[str, str]] | None = None,
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
            "your own percentage or growth figures from the raw numbers in the source text. Each "
            "line in that block is labeled with the EXACT two periods it covers (e.g. 'January "
            "2026 → March 2026 total') — when you state a change for a given period span, you "
            "MUST cite the line labeled with that exact span, never a different line (e.g. a "
            "single month's own 'As-reported change/rate' figure, which covers only that one "
            "month against the month before it) just because it is the nearest or most recent "
            "figure in the evidence. Citing a value under a different period label than the one "
            "you are describing is exactly the mistake this block exists to prevent.\n\n"
            if calculated_metrics_context
            else ""
        )
        growth_terminology_requirement = (
            "Growth-rate terminology must be precise, not just the number: 'CAGR' and 'compound "
            "annual growth rate' describe a rate compounded across three or more periods — never "
            "use either term for a single period-over-period change or a two-point total change, "
            "even when the percentage itself is correct. If the evidence only supports a "
            "year-over-year change or a total change across the period, call it exactly that "
            "('X% year-over-year growth', 'a total increase of X% over the period') rather than "
            "labeling it a compound annual growth rate.\n\n"
        )
        dimension_framing_requirement = (
            "Before describing any metric as having increased, decreased, grown, or declined, "
            "confirm the values being compared represent the SAME thing at two DIFFERENT points "
            "in time (e.g. the same region's retention rate in 2023 vs. 2025). Values that instead "
            "differ by category — different regions, channels, products, segments, departments, "
            "or risk types within the SAME period — are not a change over time, even when they "
            "appear in the same table or as adjacent rows in the evidence. Describe those as a "
            "comparison instead: 'Digital has the highest Premium Share at 38%, while Partners has "
            "the lowest at 7%' — never 'Premium Share decreased by 81.6%' when 38% and 7% are two "
            "different channels in the same period, not the same channel measured twice. A "
            "'Verified Calculations' entry marked as a cross-sectional comparison (highest/lowest) "
            "is exactly this case — cite the highest/lowest figures, never a change between "
            "them. The same caution applies even more strongly when two adjacent rows name two "
            "DIFFERENT metrics rather than two categories of one metric (e.g. 'Operational "
            "Resilience Score: 81' and 'Overall Risk Score: 72' in a scorecard-style table) — these "
            "are not comparable at all, not even as a cross-sectional 'highest/lowest'; never "
            "compute or state any relationship (change, gap, or comparison) between two "
            "differently-named metrics — report each one's own value as its own separate fact.\n\n"
        )
        single_observation_requirement = (
            "Never describe a metric as having 'improved', 'deteriorated', 'gotten better', or "
            "'gotten worse' — or as having increased/decreased/grown/declined — unless the "
            "evidence provides at least two genuinely comparable observations of that SAME metric "
            "(the same metric, at two different points in time, or the same metric compared "
            "across categories as covered above). A single, standalone figure with no such "
            "baseline is a fact, not a trend: 'Direct Digital retention was 86% in 2025' is "
            "correct; 'Direct Digital retention improved to 86%' is not, unless a prior Direct "
            "Digital retention figure is also present in the evidence. A 'Verified Calculations' "
            "entry marked as a single observation is exactly this case — state the value plainly, "
            "never as a directional change.\n\n"
        )
        polarity_requirement = (
            "Whether a metric moving up or down is good or bad news is NOT something you may "
            "infer from the number alone. Where a 'Verified Calculations' entry carries a "
            "'Business direction' line, follow it exactly: it will tell you either that the "
            "metric's direction is established (so you may say 'improved'/'deteriorated' when "
            "that specific direction is met) or that it is NOT established by the evidence — in "
            "that case describe the metric only as having increased/decreased/grown/declined, "
            "and never as having improved, worsened, gotten better, or gotten worse, no matter "
            "how the change looks on its face. A rising number is not inherently good news and a "
            "falling number is not inherently bad news — e.g. rising claims or a rising loss "
            "ratio is a deterioration, not an improvement, and rising premium or retention is an "
            "improvement, not a deterioration; for any metric with no stated business direction, "
            "increased/decreased is the only correct wording.\n\n"
        )
        causal_language_requirement = (
            "Do not state that one trend is CAUSING another (e.g. 'operational inefficiencies are "
            "causing customer attrition') unless a source document explicitly states that causal "
            "mechanism. When two findings coincide without an explicitly stated cause, describe "
            "the association and flag it for investigation instead of asserting causation: "
            "'The increase in complaints coincides with declining retention and warrants "
            "investigation into whether service issues are contributing to customer attrition.'\n\n"
        )
        report_plan_context = render_plan_for_prompt(report_plan) if report_plan else ""
        report_plan_requirement = (
            "A Report Plan is included in the evidence below, ranking findings by materiality "
            "and identifying which metrics warrant a chart. Use it to decide what belongs in the "
            "Executive Summary and which Key Findings to lead with — do not silently ignore it, "
            "and do not present it to the reader as if it were sourced from the documents "
            "themselves.\n\n"
            if report_plan_context
            else ""
        )
        executive_summary_requirement = (
            "Build it from the 3-5 highest-materiality items in the Report Plan above and its key "
            "relationships — do not independently re-derive what matters most. "
            if report_plan_context
            else ""
        )
        recommendations_plan_clause = (
            " Every recommendation must trace back to one of the ranked findings in the Report "
            "Plan above — do not introduce a recommendation with no corresponding finding."
            if report_plan_context
            else ""
        )
        risk_plan_clause = (
            "Reuse the Report Plan ranked findings above where a risk relates to one. "
            if report_plan_context
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
                "This does not mean forcing equal coverage: if one document supplies most of the "
                "material and another contributes only a single relevant point, reflect that "
                "naturally rather than padding the thin one — but never omit a document from the "
                "evidence set entirely, and never fabricate a finding just to make a "
                "lightly-relevant document appear more substantial than the evidence supports. "
                "If a finding is corroborated by more than one document, say so and cite all of "
                "them; that kind of cross-document corroboration is the most valuable thing you "
                "can produce.\n\n"
            )
            if source_count > 1
            else ""
        )
        coverage_gap_requirement = (
            (
                "REPORT SCOPE NOTE (application-generated, not user-authored): the user "
                "explicitly requested a report using every document in this workspace. The "
                "following document(s) were in scope but could not contribute evidence — "
                + "; ".join(
                    f"{gap['filename']} ({gap['reason'].replace('_', ' ')})"
                    for gap in coverage_gaps
                )
                + ". Do not silently omit them from your account of the evidence reviewed: "
                "state plainly, once, that they were reviewed but contained no evidence "
                "relevant to this report — do not invent findings from them to compensate.\n\n"
            )
            if coverage_gaps
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

        section_ids = list(TEMPLATE_SECTIONS.get(template_id, TEMPLATE_SECTIONS["full_report"]))
        if comparison_requirement:
            if "conclusion" in section_ids:
                section_ids.insert(section_ids.index("conclusion"), "changes_since_last")
            else:
                section_ids.append("changes_since_last")

        exec_summary_length = EXEC_SUMMARY_LENGTH.get(template_id, "3-5 sentences")
        key_findings_count = KEY_FINDINGS_COUNT.get(template_id, "4-8 findings")

        section_blocks: dict[str, str] = {
            "executive_summary": (
                "## Executive Summary\n"
                f"{executive_summary_requirement}"
                f"{exec_summary_length} a board member could read alone and understand the whole "
                "picture: the overall situation, the most important finding, and the headline "
                "recommendation. Do not restate sentences that will also appear in Key Findings — "
                "compress and reframe at a higher altitude instead; a reader who reads only this "
                "section and skips the rest should still walk away informed.\n\n"
            ),
            "key_findings": (
                "## Key Findings\n"
                f"{key_findings_count} as sub-headings, drawing across the full set of documents "
                "(not clustered from just one). For each: a bolded one-line finding, then 2-4 "
                "sentences moving from FACT (what the evidence actually shows) to ANALYSIS (what "
                "pattern or relationship it reveals) to IMPLICATION (why it matters for "
                "decision-makers) — do not stop at restating the fact. After that paragraph, on "
                "their OWN separate lines — each starting a brand-new line, never appended to the "
                "end of the paragraph or to each other — write exactly three evidence tags, in "
                "this order:\n"
                "`**Basis:** <value>` where <value> is EXACTLY one of these four literal phrases — "
                "not a paraphrase, not a different label such as 'Verified Calculations' — `Source "
                "fact` (stated directly by a source document), `Calculated result` (computed in the "
                "Verified Calculations block above), `Observation` (a non-causal comparison between "
                "two DIFFERENT measured things, e.g. 'claims grew faster than premium' — describes "
                "a relationship without claiming one caused the other or interpreting what it "
                "means), or `Analytical inference` (your own interpretation of what a fact, "
                "calculation, or observation means — not itself stated or computed anywhere in the "
                "evidence) — never present an inference as if it were a stated fact, and never "
                "present a plain observation as if it were an interpretation.\n"
                "`**Confidence:** High/Medium/Low — <one-clause reason>` on its own line, reflecting "
                "how well-supported the finding is by the evidence (a Calculated-result finding "
                "grounded in the Verified Calculations block is High by default; an inference "
                "resting on a single ambiguous mention is Low).\n"
                "`**Source:** <filename(s), plural if more than one document supports it>` on its "
                "own line.\n"
                "These three tags are metadata, not part of the narrative — never fold them into "
                "the same sentence or line as the FACT/ANALYSIS/IMPLICATION prose above them.\n\n"
            ),
            "detailed_analysis": (
                "## Detailed Analysis\n"
                "The narrative connective tissue between findings — trends across documents, "
                "recurring themes, contradictions or inconsistencies between sources, what changed "
                "over time if the documents span a period, and context a reader needs to interpret "
                "the findings correctly. This section is where cross-document synthesis should be "
                "most visible. Do not restate findings from Key Findings to lengthen this section — "
                "every sentence here should add something Key Findings didn't already say. If the "
                "evidence doesn't support a particular analytical thread (e.g. no time-series data "
                "to discuss a trend), omit it rather than speculating.\n\n"
            ),
            "risks_issues": (
                "## Risks & Issues\n"
                "Concrete risks or open problems surfaced by the evidence — never a generic category "
                "label like 'Operational Bottlenecks' or 'Customer Dissatisfaction'; name the "
                "specific metric or figure behind it instead, e.g. 'Claims backlog escalation — "
                "backlog increased from 14 to 31 cases (+121.4%), concentrated in the West region.' "
                f"{risk_plan_clause}"
                "Format each one as its own markdown bullet — `- **<specific title>:** <brief note "
                "on likely impact>` — one risk per bullet, never combined into a single paragraph. "
                "Immediately after each bullet, on its own line, add `**Basis:** <value>` using "
                "exactly the same four literal values as Key Findings (`Source fact`, `Calculated "
                "result`, `Observation`, or `Analytical inference`) — never assert a likely cause as "
                "if it were a proven one. If the evidence surfaces no material risks, write one "
                "sentence starting with 'No risks were identified in the evidence reviewed' — not "
                "'no risks exist', which is a stronger claim the absence of evidence doesn't support "
                "— rather than manufacturing a generic risk.\n\n"
            ),
            "opportunities": (
                "## Opportunities\n"
                "Positive openings, efficiencies, or strategic options the evidence points to — "
                "grounded the same way as Risks & Issues above: a specific metric or figure, never a "
                "generic label, and with the same restraint against overclaiming — a cross-sectional "
                "observation (one category ranks highest among several) is not itself an "
                "'improvement' unless the evidence also shows a prior comparable observation of that "
                "SAME thing. Prefer: 'Direct Digital recorded the highest reported retention rate "
                "among the channels at 86%, indicating an opportunity to investigate and potentially "
                "replicate the practices associated with stronger digital retention' — never 'Direct "
                "Digital retention improved to 86%' when no prior Direct Digital figure exists in "
                "the evidence. Format each one as its own markdown bullet — `- **<specific title>:** "
                "<detail>` — one opportunity per bullet, never combined into a single paragraph, "
                "with a `**Basis:**` line immediately after each bullet using the same convention as "
                "Risks & Issues. If the evidence contains none, write one sentence starting with 'No "
                "opportunities were identified in the evidence reviewed' rather than inventing "
                "one.\n\n"
            ),
            "strategic_recommendations": (
                "## Strategic Recommendations\n"
                "A markdown numbered list of specific, actionable next steps, ordered by priority — "
                "not generic advice, but recommendations that follow directly from the findings "
                "above. Each recommendation MUST start a new line with '1. ', '2. ', etc. — never "
                "run multiple recommendations together in one paragraph. Within each numbered item, "
                "structure it as three clauses: `**Action:**` (what should be done, specific enough "
                "to act on — never a bare instruction like 'invest in technology'), `**Rationale:**` "
                "(why — must cite a specific finding, metric, or figure from the evidence above, not "
                "a generic justification), and `**Measurement:**` (how success would be assessed — "
                "reference a metric from the Verified Calculations or Report Plan above where one "
                "exists, rather than inventing a target the evidence doesn't "
                f"support).{recommendations_plan_clause}\n"
                f"{TEMPLATE_RECOMMENDATION_STYLE.get(template_id, '')}\n"
            ),
            "changes_since_last": comparison_requirement,
            "conclusion": (
                "## Conclusion\n"
                "2-3 sentences closing the report and restating what should happen next.\n\n"
            ),
        }
        sections_text = "".join(section_blocks[sid] for sid in section_ids if section_blocks.get(sid))
        first_heading = SECTION_HEADINGS.get(section_ids[0], "## Executive Summary")

        prompt = (
            f"Write a {template_name} titled \"{title}\" covering the period '{period_name}', "
            "using only the evidence provided below.\n"
            f"{instructions_line}\n"
            f"{TEMPLATE_AUDIENCE_PURPOSE.get(template_id, '')}"
            f"{synthesis_requirement}"
            f"{coverage_gap_requirement}"
            f"{calculated_metrics_requirement}"
            f"{growth_terminology_requirement}"
            f"{dimension_framing_requirement}"
            f"{single_observation_requirement}"
            f"{polarity_requirement}"
            f"{causal_language_requirement}"
            f"{report_plan_requirement}"
            "Go beyond summarizing — synthesize. For every major point, explain not just what "
            "happened but why it matters, what pattern or trend it fits into, what changed since "
            "prior context (if evidence shows it), and what the implication is for decision-makers. "
            "Every non-obvious claim should be traceable to a specific source document by name.\n\n"
            "Write like an analyst, not a promoter: prefer exact figures and specific evidence over "
            "adjectives. Avoid words like 'remarkable', 'robust', 'significant', 'pivotal', "
            "'dynamic', 'transformative', 'compelling', and 'impressive' unless the evidence "
            "specifically justifies that word — a number in context communicates more than an "
            "adjective describing it. Do not draw a conclusion the evidence doesn't support (e.g. "
            "two metrics both rising does not by itself mean profitability improved) — state what "
            "the data shows and stop there unless the evidence explicitly supports going further.\n\n"
            "Structure the report in GitHub-flavoured markdown with exactly these sections, in order "
            f"— a {template_name} must contain ONLY these sections, no others. Do not include a "
            "top-level title heading — start directly at the first section below; the document "
            "title is rendered separately by the export layer.\n\n"
            f"{sections_text}"
            "Do not wrap your answer in a code fence. Output raw markdown starting directly with the "
            f"{first_heading} heading.\n\n"
            f"Evidence:\n{evidence}{calculated_metrics_context}{report_plan_context}{comparison_context}"
        )
        try:
            response = self._client.chat.completions.create(
                model=CHAT_MODEL,
                temperature=0.3,
                max_tokens=TEMPLATE_MAX_TOKENS.get(template_id, 4096),
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
                            "board-appropriate prose that favors exact figures and specific evidence "
                            "over adjectives — you are an analyst, not a promoter. Never fabricate a "
                            "figure, name, date, or claim that isn't in the evidence — if the evidence "
                            "is thin on a section, say so briefly rather than padding with generic "
                            "text."
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
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        template = template_by_id(template_id)
        period = period_by_id(period_id)
        workspace_name = str(project.get("name") or "Workspace")
        report_title = (title or "").strip() or f"{template['name']} — {period['name']}"
        previous_report = self._find_previous_report(workspace_id, template_id, period_id)

        all_docs = list(project.get("documents") or [])
        selected_ids = [str(doc_id) for doc_id in (document_ids or []) if doc_id]
        if selected_ids:
            selected_id_set = set(selected_ids)
            docs_in_scope = [
                doc for doc in all_docs if str(doc.get("id") or "") in selected_id_set
            ]
            # An explicit document selection is a stronger, more specific
            # scope than the period window — it must not be silently
            # narrowed further by a date filter the user never asked for.
            scoped_docs = docs_in_scope
        else:
            scoped_docs = filter_documents_by_period(all_docs, period_id)
        sources = self._gather_sources(
            workspace_id,
            scoped_docs,
            template=template,
            period=period,
            instructions=instructions,
            document_ids=selected_ids or None,
        )

        source_coverage: dict[str, Any] = {}
        if selected_ids or detect_all_documents_intent(instructions):
            gaps = compute_coverage_gaps(sources, scoped_docs)
            source_coverage = {
                "all_documents_requested": not selected_ids,
                "documents_in_scope": len(scoped_docs),
                "documents_covered": len(sources),
                "gaps": gaps,
            }

        document_periods = {
            str(document.get("filename") or ""): {
                "period_date": document.get("period_date"),
                "uploaded_at": document.get("uploaded_at"),
            }
            for document in all_docs
            if document.get("filename")
        }
        metric_tables = extract_metric_tables(sources, document_periods=document_periods)
        report_plan = (
            build_report_plan(
                metric_tables=metric_tables,
                sources=sources,
                template_id=template_id,
                template_name=template["name"],
                period_name=period["name"],
            )
            if REPORT_PLAN_ENABLED
            else None
        )
        dashboard_selection = (
            select_dashboard_items(report_plan, metric_tables) if report_plan else None
        )
        markdown = self._generate_markdown(
            title=report_title,
            period_name=period["name"],
            template_id=template_id,
            template_name=template["name"],
            sources=sources,
            instructions=instructions,
            previous_report=previous_report,
            metric_tables=metric_tables,
            report_plan=report_plan,
            coverage_gaps=source_coverage.get("gaps"),
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
                "documents_in_workspace": len(all_docs),
                "documents_in_period": len(scoped_docs),
                **(
                    {"report_plan": report_plan.to_dict()}
                    if report_plan and not report_plan.is_empty()
                    else {}
                ),
                **(
                    {"dashboard_selection": dashboard_selection.to_dict()}
                    if dashboard_selection and not dashboard_selection.is_empty()
                    else {}
                ),
                **({"source_coverage": source_coverage} if source_coverage else {}),
            },
            metrics={"tables": metric_tables} if metric_tables else {},
            executive_summary={"text": _clip(markdown, 500)},
        )

        # "Professional charts & trend analysis" is a Professional+ pricing
        # bullet — Starter reports still get the analytical template's other
        # sections, just not the generated chart blocks.
        plan_service = PlanService(access_token=self._access_token)
        charts_plan_eligible = plan_service.include_professional_charts()
        is_analytical_template = (
            template_id in ANALYTICAL_TEMPLATE_IDS and charts_plan_eligible
        )
        # WARNING, not INFO: the app has no logging.basicConfig() anywhere,
        # so the root logger sits at Python's default WARNING level with no
        # configured handler — an .info() call here is silently dropped in
        # production regardless of this module's own logger. Confirmed via
        # `docker compose logs api | grep "Chart eligibility"` coming back
        # empty after a real request that should have hit this line.
        logger.warning(
            "Chart eligibility template_id=%s in_analytical_set=%s plan_id=%s "
            "charts_plan_eligible=%s is_analytical_template=%s",
            template_id,
            template_id in ANALYTICAL_TEMPLATE_IDS,
            plan_service.get_plan_id(),
            charts_plan_eligible,
            is_analytical_template,
        )
        report = apply_visualizations(
            report,
            user_report_type=template["name"],
            document_text=markdown,
            reporting_period=period["name"],
            include_charts=is_analytical_template,
            force_generate=is_analytical_template,
        )
        logger.warning(
            "Chart result report_id=%s has_visualizations=%s visualization_count=%s",
            report.metadata.get("template_id"),
            bool((report.charts or {}).get("visualizations")),
            len((report.charts or {}).get("visualizations") or []),
        )

        # Phase C.1: correct a detected direction/sentiment contradiction
        # BEFORE the reader ever sees it, rather than only flagging it in
        # qc_report below — "deterministic result -> grounded narrative",
        # never "LLM answer -> verification warning" left for the reader
        # to notice on their own (Section 7). A surgical word-level fix
        # using the same detection check_direction_consistency already
        # runs; run_qc_pass below therefore sees the CORRECTED narrative.
        corrected_narrative, _correction_remaining = apply_deterministic_corrections(
            report.narrative, metric_tables
        )
        if corrected_narrative != report.narrative:
            report.narrative = corrected_narrative
            report.metadata["narrative_auto_corrected"] = True

        qc_report = run_qc_pass(
            report.narrative,
            report.source_documents,
            metric_tables=metric_tables,
            chart_requirements=(report.metadata.get("report_plan") or {}).get(
                "chart_requirements"
            ),
            visualizations=report.charts.get("visualizations"),
            previous_report=previous_report,
            period_id=period_id,
            evidence="\n\n".join(f"{src['filename']}\n{src['excerpt']}" for src in sources),
            source_coverage=source_coverage or None,
            llm_client=self._client,
        )
        if qc_report.issues:
            report.metadata["qc_report"] = qc_report.to_dict()

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
            # Phase C.1: the narrower SPA-shaped fields above are what
            # get_report()/list_reports() need, but this record OVERWRITES
            # the metadata sidecar save_report() just wrote (see comment
            # below) — without this field, everything save_report() put in
            # report.to_dict() (metrics["tables"], the deterministic metric
            # series; charts; metadata["report_plan"]) was silently lost
            # the moment this second write landed, leaving export-time
            # chart/data access with nothing but the bare markdown text.
            "reportData": report.to_dict(),
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
