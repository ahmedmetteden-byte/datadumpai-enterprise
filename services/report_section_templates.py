"""
Report-type section templates and narrative filtering for DataDumpAI.

Sections are included or suppressed based on detected report type, visualization
strategy, and whether the source material supports multi-period analysis.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from models.report_data import ReportData
from services.report_markdown_renderer import remove_empty_sections
from services.visualization_engine import (
    ReportIntent,
    ReportType,
    VisualizationStrategy,
    build_data_profile,
    build_visualization_blocks,
    classify_report_intent,
    classify_report_type,
    decide_visualization_strategies,
)

H2_HEADING_PATTERN = re.compile(r"^(## .+)$", re.MULTILINE)
H3_HEADING_PATTERN = re.compile(r"^(### .+)$", re.MULTILINE)

VISUALIZATION_DERIVED_SECTIONS = frozenset(
    {
        "visual summary",
        "cross-period themes",
        "period-over-period comparison",
        "cross-document intelligence",
        "industry benchmark",
        "trends",
    }
)

THEME_FREQUENCY_SUBSECTIONS = frozenset(
    {
        "top discussion topics",
        "theme distribution",
        "theme trends",
    }
)

INTELLIGENCE_DASHBOARD_TITLE = "Executive Intelligence Dashboard"
FULL_REPORT_OVERVIEW_TITLE = "Full Report Overview"


@dataclass
class SectionPlan:
    """Which narrative sections to request from the LLM and retain after generation."""

    detected_report_type: str = ReportType.CUSTOM.value
    report_intent: str = ReportIntent.ANALYTICAL_REPORT.value
    report_format: str = "intelligence"
    allowed_sections: list[str] = field(default_factory=list)
    suppressed_sections: list[str] = field(default_factory=list)
    allowed_dashboard_subsections: list[str] = field(default_factory=list)
    suppressed_dashboard_subsections: list[str] = field(default_factory=list)
    include_visual_summary: bool = False
    include_cross_period_themes: bool = False
    include_period_comparison: bool = False
    include_cross_document_intelligence: bool = False
    include_industry_benchmark: bool = False
    include_trends: bool = False
    include_canonical_theme_metrics: bool = False
    has_visualizations: bool = False
    multi_period: bool = False
    theme_frequency_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> SectionPlan:
        if not payload:
            return cls()
        return cls(**{key: payload[key] for key in cls.__dataclass_fields__ if key in payload})


INTELLIGENCE_SECTION_TEMPLATES: dict[ReportType, list[str]] = {
    ReportType.FINANCIAL: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Key Findings (Ranked by Importance)",
        "Executive Quotations",
        "AI Insights",
        "Detailed Narrative",
    ],
    ReportType.SALES: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Key Findings (Ranked by Importance)",
        "Executive Quotations",
        "AI Insights",
        "Detailed Narrative",
    ],
    ReportType.LEGAL: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Case Timeline and Proceedings",
        "Court Holdings and Orders",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.MEETING: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Decisions and Resolutions",
        "Action Items and Owners",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.POLICY: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Policy Objectives and Scope",
        "Stakeholder and Implementation Map",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.REGULATORY: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Compliance Obligations",
        "Regulatory Gaps and Exposure",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.RISK: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Risk Register Summary",
        "Mitigation Priorities",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.RESEARCH: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Methodology and Evidence",
        "Findings and Analysis",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.PROJECT: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Project Status and Milestones",
        "Dependencies and Blockers",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.AUDIT: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Audit Findings Summary",
        "Control Gaps and Remediation",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.OPERATIONS: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Operational Performance",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.HR: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Workforce Summary",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.PROCUREMENT: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Sourcing and Vendor Summary",
        "Executive Quotations",
        "Key Findings (Ranked by Importance)",
        "Detailed Narrative",
    ],
    ReportType.CUSTOM: [
        INTELLIGENCE_DASHBOARD_TITLE,
        "Key Findings (Ranked by Importance)",
        "Executive Quotations",
        "AI Insights",
        "Detailed Narrative",
    ],
}

DASHBOARD_SUBSECTION_TEMPLATES: dict[ReportType, list[str]] = {
    ReportType.FINANCIAL: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Overall Health Score",
        "Top Risks",
        "Key Opportunities",
    ],
    ReportType.LEGAL: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Timeline Highlights",
        "Top Risks",
        "Key Implications",
    ],
    ReportType.MEETING: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Decisions",
        "Action Items",
        "Deadlines",
    ],
    ReportType.POLICY: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Policy Objectives",
        "Stakeholders",
        "Implementation Priorities",
    ],
    ReportType.RISK: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Top Risks",
        "Mitigation Priorities",
        "Risk Outlook",
    ],
    ReportType.RESEARCH: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Methodology",
        "Evidence Summary",
        "Research Confidence",
    ],
    ReportType.PROJECT: [
        "Executive Summary Card",
        "Executive Snapshot",
        "Milestone Status",
        "Top Risks",
        "Next Steps",
    ],
}

FULL_REPORT_SECTION_TEMPLATES: dict[ReportType, list[str]] = {
    ReportType.FINANCIAL: [
        FULL_REPORT_OVERVIEW_TITLE,
        "Period Narrative",
        "Consolidated Key Findings",
        "Consolidated Risks",
        "Consolidated Opportunities",
        "Executive Quotations",
    ],
    ReportType.LEGAL: [
        FULL_REPORT_OVERVIEW_TITLE,
        "Period Narrative",
        "Case Timeline and Proceedings",
        "Consolidated Key Findings",
        "Executive Quotations",
    ],
    ReportType.MEETING: [
        FULL_REPORT_OVERVIEW_TITLE,
        "Period Narrative",
        "Decisions and Resolutions",
        "Action Items and Owners",
        "Consolidated Key Findings",
    ],
    ReportType.CUSTOM: [
        FULL_REPORT_OVERVIEW_TITLE,
        "Period Narrative",
        "Consolidated Key Findings",
        "Consolidated Risks",
        "Consolidated Opportunities",
        "Executive Quotations",
    ],
}


def _is_multi_period(
    *,
    source_document_count: int | None,
    report_context: dict[str, Any] | None,
) -> bool:
    context = report_context or {}
    count = source_document_count or len(context.get("source_documents") or [])

    if count > 1:
        return True

    return bool(context.get("has_prior_reports"))


def _is_theme_frequency_only(report_data: ReportData, data_profile: Any) -> bool:
    has_topics = bool(report_data.charts.get("topics"))
    return has_topics and not data_profile.has_quantitative_signal()


def _predict_visualizations(
    report_data: ReportData,
    *,
    detected_type: ReportType,
    intent: ReportIntent,
    data_profile: Any,
    document_text: str,
    include_charts: bool,
) -> bool:
    if not include_charts:
        return False

    existing = report_data.charts.get("visualizations")
    if existing is not None:
        return bool(existing)

    strategies = decide_visualization_strategies(detected_type, data_profile, intent)
    if strategies == [VisualizationStrategy.NONE]:
        return False

    blocks = build_visualization_blocks(
        detected_type,
        data_profile,
        strategies,
        report_data,
        document_text=document_text,
    )
    exportable_types = {
        VisualizationStrategy.BAR_CHART,
        VisualizationStrategy.LINE_CHART,
        VisualizationStrategy.PIE_CHART,
        VisualizationStrategy.KPI_CARDS,
    }
    return any(block.type in exportable_types for block in blocks)


def build_report_section_plan(
    report_data: ReportData,
    *,
    user_report_type: str = "",
    document_text: str = "",
    report_context: dict[str, Any] | None = None,
    include_charts: bool = True,
    source_document_count: int | None = None,
    report_format: str = "intelligence",
) -> SectionPlan:
    """Build the section inclusion plan for prompts and post-generation filtering."""

    detected_type = classify_report_type(
        report_data,
        document_text=document_text,
        user_report_type=user_report_type or report_data.report_type,
    )
    intent = classify_report_intent(user_report_type or report_data.report_type)
    data_profile = build_data_profile(report_data, document_text=document_text)
    multi_period = _is_multi_period(
        source_document_count=source_document_count,
        report_context=report_context,
    )
    theme_frequency_only = _is_theme_frequency_only(report_data, data_profile)
    has_visualizations = _predict_visualizations(
        report_data,
        detected_type=detected_type,
        intent=intent,
        data_profile=data_profile,
        document_text=document_text,
        include_charts=include_charts,
    )

    if report_format == "full_report":
        base_sections = list(
            FULL_REPORT_SECTION_TEMPLATES.get(
                detected_type,
                FULL_REPORT_SECTION_TEMPLATES[ReportType.CUSTOM],
            )
        )
    else:
        base_sections = list(
            INTELLIGENCE_SECTION_TEMPLATES.get(
                detected_type,
                INTELLIGENCE_SECTION_TEMPLATES[ReportType.CUSTOM],
            )
        )

    dashboard_subsections = list(
        DASHBOARD_SUBSECTION_TEMPLATES.get(
            detected_type,
            DASHBOARD_SUBSECTION_TEMPLATES.get(
                ReportType.FINANCIAL,
                [
                    "Executive Summary Card",
                    "Executive Snapshot",
                    "Overall Health Score",
                    "Top Risks",
                    "Key Opportunities",
                ],
            ),
        )
    )

    suppressed_sections: set[str] = set()
    suppressed_dashboard: set[str] = set()

    include_cross_period_themes = (
        multi_period and not theme_frequency_only and report_format == "full_report"
    )
    include_period_comparison = multi_period and report_format == "full_report"
    include_cross_document_intelligence = (
        multi_period and not theme_frequency_only and report_format == "intelligence"
    )
    include_industry_benchmark = multi_period and report_format == "intelligence"
    include_trends = multi_period and bool((report_context or {}).get("has_prior_reports"))
    include_visual_summary = has_visualizations
    include_canonical_theme_metrics = has_visualizations and not theme_frequency_only

    if not include_visual_summary:
        suppressed_sections.add("Visual Summary")
        suppressed_dashboard.update(THEME_FREQUENCY_SUBSECTIONS)

    if not include_cross_period_themes:
        suppressed_sections.add("Cross-Period Themes")

    if not include_period_comparison:
        suppressed_sections.add("Period-over-Period Comparison")

    if not include_cross_document_intelligence:
        suppressed_sections.add("Cross-Document Intelligence")

    if not include_industry_benchmark:
        suppressed_sections.add("Industry Benchmark")

    if not include_trends:
        suppressed_sections.add("Trends")

    if theme_frequency_only:
        suppressed_dashboard.update(THEME_FREQUENCY_SUBSECTIONS)

    if include_cross_period_themes and "Cross-Period Themes" not in base_sections:
        base_sections.insert(2, "Cross-Period Themes")

    if include_period_comparison and "Period-over-Period Comparison" not in base_sections:
        insert_at = 3 if include_cross_period_themes else 2
        base_sections.insert(insert_at, "Period-over-Period Comparison")

    if include_cross_document_intelligence and "Cross-Document Intelligence" not in base_sections:
        base_sections.insert(1, "Cross-Document Intelligence")

    if include_industry_benchmark and "Industry Benchmark" not in base_sections:
        base_sections.insert(2, "Industry Benchmark")

    if include_trends and "Trends" not in base_sections:
        base_sections.append("Trends")

    if include_visual_summary and "Visual Summary" not in base_sections:
        base_sections.append("Visual Summary")

    allowed_dashboard_subsections = [
        subsection
        for subsection in dashboard_subsections
        if subsection.lower() not in suppressed_dashboard
    ]

    allowed_sections = [
        section for section in base_sections if section not in suppressed_sections
    ]

    return SectionPlan(
        detected_report_type=detected_type.value,
        report_intent=intent.value,
        report_format=report_format,
        allowed_sections=allowed_sections,
        suppressed_sections=sorted(suppressed_sections),
        allowed_dashboard_subsections=allowed_dashboard_subsections,
        suppressed_dashboard_subsections=sorted(suppressed_dashboard),
        include_visual_summary=include_visual_summary,
        include_cross_period_themes=include_cross_period_themes,
        include_period_comparison=include_period_comparison,
        include_cross_document_intelligence=include_cross_document_intelligence,
        include_industry_benchmark=include_industry_benchmark,
        include_trends=include_trends,
        include_canonical_theme_metrics=include_canonical_theme_metrics,
        has_visualizations=has_visualizations,
        multi_period=multi_period,
        theme_frequency_only=theme_frequency_only,
    )


def build_intelligence_structure_prompt(section_plan: SectionPlan) -> str:
    """Render the ## section structure block for executive intelligence prompts."""

    lines = ["REQUIRED REPORT STRUCTURE (use these exact ## headings in order)", ""]

    for section in section_plan.allowed_sections:
        lines.append(f"## {section}")

        if section == INTELLIGENCE_DASHBOARD_TITLE:
            lines.append("")
            lines.append("Include only these ### dashboard subsections:")
            for subsection in section_plan.allowed_dashboard_subsections:
                lines.append(f"### {subsection}")
            lines.append("")
            lines.append(
                "Do NOT include a ### Top Discussion Topics subsection unless explicitly listed above."
            )

        lines.append("")

    if not section_plan.include_canonical_theme_metrics:
        lines.append(
            "Do NOT quantify themes as frequency percentages or create theme distribution content."
        )

    if not section_plan.include_cross_document_intelligence:
        lines.append(
            "Do NOT include a Cross-Document Intelligence section or cross-document theme frequency statements."
        )

    if not section_plan.include_visual_summary:
        lines.append("Do NOT include a Visual Summary section.")

    return "\n".join(lines).strip()


def build_full_report_structure_prompt(section_plan: SectionPlan) -> str:
    """Render the ## section structure block for full report prompts."""

    lines = ["REQUIRED REPORT STRUCTURE (use these exact ## headings in order)", ""]

    for section in section_plan.allowed_sections:
        lines.append(f"## {section}")

        if section == FULL_REPORT_OVERVIEW_TITLE:
            lines.append("")
            lines.append("Include ### Executive Summary Card and ### Period Snapshot tables.")
            lines.append("")

        lines.append("")

    if not section_plan.include_cross_period_themes:
        lines.append(
            "Do NOT include a Cross-Period Themes section based on keyword or theme frequency alone."
        )

    if not section_plan.include_period_comparison:
        lines.append("Do NOT include a Period-over-Period Comparison section.")

    if not section_plan.include_visual_summary:
        lines.append("Do NOT include a Visual Summary section.")

    return "\n".join(lines).strip()


def _split_h2_sections(text: str) -> list[tuple[str | None, str]]:
    parts = H2_HEADING_PATTERN.split(text)
    sections: list[tuple[str | None, str]] = [(None, parts[0])]

    index = 1
    while index < len(parts):
        heading = parts[index].replace("##", "").strip()
        body = parts[index + 1] if index + 1 < len(parts) else ""
        sections.append((heading, body))
        index += 2

    return sections


def _remove_h3_subsections(body: str, suppressed: set[str]) -> str:
    if not body.strip() or not suppressed:
        return body

    parts = H3_HEADING_PATTERN.split(body)
    rebuilt: list[str] = [parts[0]]

    index = 1
    while index < len(parts):
        heading = parts[index].replace("###", "").strip()
        section_body = parts[index + 1] if index + 1 < len(parts) else ""

        if heading.lower() not in suppressed:
            rebuilt.append(f"### {heading}\n{section_body}")

        index += 2

    return "\n\n".join(part.strip() for part in rebuilt if part and part.strip()).strip()


def _is_theme_frequency_section(title: str, body: str) -> bool:
    if title.lower() != "cross-period themes":
        return False

    lowered = body.lower()
    theme_markers = (
        "frequency:",
        "of ",
        " documents",
        "theme",
        "appeared in",
        "keyword",
    )
    return any(marker in lowered for marker in theme_markers)


def filter_report_narrative(narrative: str, section_plan: SectionPlan | None) -> str:
    """Remove visualization-derived or report-type-irrelevant sections from narrative."""

    if not narrative.strip() or section_plan is None:
        return narrative

    suppressed_h2 = {title.lower() for title in section_plan.suppressed_sections}
    suppressed_h3 = {title.lower() for title in section_plan.suppressed_dashboard_subsections}

    if not section_plan.has_visualizations:
        suppressed_h2.add("visual summary")
        suppressed_h3.update(THEME_FREQUENCY_SUBSECTIONS)

    if not section_plan.include_cross_period_themes:
        suppressed_h2.add("cross-period themes")

    if not section_plan.include_period_comparison:
        suppressed_h2.add("period-over-period comparison")

    if not section_plan.include_cross_document_intelligence:
        suppressed_h2.add("cross-document intelligence")

    if not section_plan.include_industry_benchmark:
        suppressed_h2.add("industry benchmark")

    if not section_plan.include_trends:
        suppressed_h2.add("trends")

    if not section_plan.include_visual_summary:
        suppressed_h2.add("visual summary")

    rebuilt: list[str] = []

    for title, body in _split_h2_sections(narrative):
        if title is None:
            if body.strip():
                rebuilt.append(body.strip())
            continue

        title_lower = title.lower()

        if title_lower in suppressed_h2:
            continue

        if _is_theme_frequency_section(title, body) and (
            section_plan.theme_frequency_only or not section_plan.multi_period
        ):
            continue

        cleaned_body = body

        if "dashboard" in title_lower or title == INTELLIGENCE_DASHBOARD_TITLE:
            cleaned_body = _remove_h3_subsections(body, suppressed_h3)

        if cleaned_body.strip():
            rebuilt.append(f"## {title}\n\n{cleaned_body.strip()}")

    filtered = "\n\n".join(part for part in rebuilt if part).strip()
    return remove_empty_sections(filtered)
