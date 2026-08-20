"""
Parse executive intelligence reports into structured sections for export.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.report_chart_data import (
    extract_chart_data,
    extract_executive_summary_card,
    strip_chart_data,
)
from services.report_markdown_renderer import remove_empty_sections, strip_inline_markdown

SECTION_SPLIT_PATTERN = re.compile(r"^(## .+)$", re.MULTILINE)
TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|$")
BULLET_PATTERN = re.compile(r"^[-*] (.+)$", re.MULTILINE)
FINDING_PATTERN = re.compile(
    r"#### (.+?)\n(.*?)(?=\n#### |\n### |\n## |\Z)",
    re.DOTALL,
)


@dataclass
class ReportSection:
    title: str
    body: str


@dataclass
class ParsedIntelligenceReport:
    summary_card: dict[str, str] = field(default_factory=dict)
    snapshot: dict[str, str] = field(default_factory=dict)
    chart_data: dict[str, Any] = field(default_factory=dict)
    sections: list[ReportSection] = field(default_factory=list)
    appendix_sections: list[ReportSection] = field(default_factory=list)
    source_documents: list[str] = field(default_factory=list)
    raw_body: str = ""

APPENDIX_SECTION_TITLES = {
    "detailed narrative",
    "appendix",
    "source references",
    "supporting evidence",
}

MAIN_SECTION_ORDER = [
    "Executive Intelligence Dashboard",
    "Cross-Document Intelligence",
    "Industry Benchmark",
    "Executive Quotations",
    "Key Findings (Ranked by Importance)",
    "AI Insights",
    "Trends",
    "Visual Summary",
    "Strategic Recommendations",
    "Detailed Narrative",
]


def _parse_markdown_table(table_text: str) -> dict[str, str]:
    rows = [line.strip() for line in table_text.splitlines() if "|" in line]

    if len(rows) < 3:
        return {}

    parsed: dict[str, str] = {}

    for row in rows[2:]:
        cells = [cell.strip() for cell in row.strip("|").split("|")]

        if len(cells) >= 2:
            parsed[cells[0]] = cells[1]

    return parsed


def _extract_subsection(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"### {re.escape(heading)}\s*\n(.*?)(?=\n### |\n## |\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(body)

    return match.group(1).strip() if match else ""


def _split_sections(report_text: str) -> list[ReportSection]:
    chunks = SECTION_SPLIT_PATTERN.split(report_text)
    sections: list[ReportSection] = []

    if chunks and chunks[0].strip():
        sections.append(ReportSection(title="Introduction", body=chunks[0].strip()))

    index = 1

    while index < len(chunks):
        title = chunks[index].replace("##", "").strip()
        body = chunks[index + 1].strip() if index + 1 < len(chunks) else ""
        sections.append(ReportSection(title=title, body=body))
        index += 2

    return sections


_NEGATIVE_LEAD = re.compile(r"^(no|none|not\s+applicable|n/a)\b", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _prose_fallback_items(text: str) -> list[str]:
    """Split a non-bulleted prose paragraph into sentence-level items.

    The LLM sometimes writes Risks/Opportunities/AI Insights as flowing
    prose instead of markdown bullets even when real content is present —
    without this fallback, dashboard extraction (which only recognizes
    "- "/"* " bullets) silently returns nothing and the dashboard claims
    "none identified" while the report body genuinely discusses items. A
    paragraph that itself states there's nothing to report (e.g. "No
    material risks were identified in the evidence provided") is left
    alone — it must not be turned into a fake single item."""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    joined = strip_inline_markdown(" ".join(lines))

    if not joined or _NEGATIVE_LEAD.match(joined):
        return []

    return [sentence.strip() for sentence in _SENTENCE_SPLIT.split(joined) if sentence.strip()]


def _bullets_from_text(text: str) -> list[str]:
    bullets = [
        strip_inline_markdown(match.group(1).strip())
        for match in BULLET_PATTERN.finditer(text)
    ]

    return bullets if bullets else _prose_fallback_items(text)


def _risk_cards(text: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []

    for bullet in _bullets_from_text(text):
        severity = "Medium"

        if "🔴" in bullet or "critical" in bullet.lower():
            severity = "High"
        elif "🟠" in bullet:
            severity = "Medium"
        elif "🟡" in bullet:
            severity = "Medium"

        cleaned = (
            bullet.replace("🔴", "")
            .replace("🟠", "")
            .replace("🟡", "")
            .replace("🟢", "")
            .strip()
        )

        # By this point strip_inline_markdown() (applied in
        # _bullets_from_text()) has already removed any "**" markers, so
        # the title/detail boundary is whichever separator survives: the
        # legacy dashboard format uses an em-dash ("Title — detail"),
        # Step B's Risks & Issues/Opportunities prompt uses a colon
        # ("Title: detail"). Neither present just means no clean title.
        if "—" in cleaned:
            title, _, detail = cleaned.partition("—")
        elif ":" in cleaned:
            title, _, detail = cleaned.partition(":")
        else:
            title, detail = cleaned, ""
        title = title.strip(" -")

        cards.append(
            {
                "title": title.strip(),
                "detail": detail.strip(" —-"),
                "severity": severity,
            }
        )

    return cards


def parse_intelligence_report(
    report_text: str,
    *,
    source_documents: list[str] | None = None,
    pack_type: str = "executive",
) -> ParsedIntelligenceReport:
    """Structure a report for premium export."""

    chart_data = extract_chart_data(report_text)
    body = remove_empty_sections(strip_chart_data(report_text))
    summary_card, body = extract_executive_summary_card(body)

    sections = _split_sections(body)
    dashboard = next(
        (section for section in sections if "dashboard" in section.title.lower()),
        None,
    )

    snapshot: dict[str, str] = {}

    if dashboard:
        snapshot_table = _extract_subsection(dashboard.body, "Executive Snapshot")

        if snapshot_table:
            snapshot = _parse_markdown_table(snapshot_table)

    main_sections: list[ReportSection] = []
    appendix_sections: list[ReportSection] = []

    for section in sections:
        title_lower = section.title.lower()

        if title_lower in APPENDIX_SECTION_TITLES and pack_type == "executive":
            appendix_sections.append(section)
            continue

        if section.title == "Introduction" and not section.body:
            continue

        main_sections.append(section)

    if source_documents:
        appendix_sections.append(
            ReportSection(
                title="Source References",
                body="\n".join(f"- {name}" for name in source_documents),
            )
        )

    return ParsedIntelligenceReport(
        summary_card=summary_card,
        snapshot=snapshot,
        chart_data=chart_data,
        sections=main_sections,
        appendix_sections=appendix_sections,
        source_documents=source_documents or [],
        raw_body=body,
    )


def table_of_contents(sections: list[ReportSection], *, include_appendix: bool) -> list[str]:
    entries = [section.title for section in sections if section.title != "Introduction"]

    if include_appendix:
        entries.append("Appendix")

    return entries


def is_available(value: Any) -> bool:
    """True when a dashboard_metrics() value is genuinely known, not the
    "—" placeholder it falls back to for a report format that doesn't
    carry that signal (e.g. an SPA-format report has no synthetic health
    score). Export renderers use this to skip a row/line entirely rather
    than showing a visibly broken placeholder like "🟢 —/100"."""

    return bool(value) and str(value).strip() not in ("", "—")


def estimated_reading_minutes(report_text: str) -> int:
    words = len(re.findall(r"\w+", report_text))
    return max(1, round(words / 200))


def dashboard_metrics(parsed: ParsedIntelligenceReport) -> dict[str, str]:
    card = parsed.summary_card
    snapshot = parsed.snapshot
    health = parsed.chart_data.get("health_score")

    return {
        "health_score": str(health or snapshot.get("AI confidence", "—")).replace("%", ""),
        "outlook": card.get("Industry Status", snapshot.get("Overall outlook", "—")),
        "confidence": card.get("Confidence", snapshot.get("AI confidence", "—")),
        "documents": snapshot.get("Documents analyzed", str(len(parsed.source_documents)) or "—"),
        "key_risks": snapshot.get("Critical risks", "—"),
        "recommendations": snapshot.get("Recommendations", "—"),
        "priority": card.get("Priority", "—"),
        "trend": card.get("Overall Trend", "—"),
    }


def top_risks(parsed: ParsedIntelligenceReport) -> list[dict[str, str]]:
    dashboard = next(
        (section for section in parsed.sections if "dashboard" in section.title.lower()),
        None,
    )

    if dashboard:
        cards = _risk_cards(_extract_subsection(dashboard.body, "Top Risks"))
        if cards:
            return cards

    # SPA-format reports have no "dashboard" section — risks live in
    # their own top-level "Risks & Issues" section instead.
    risks_section = next(
        (section for section in parsed.sections if "risk" in section.title.lower()),
        None,
    )
    return _risk_cards(risks_section.body) if risks_section else []


def first_ai_insight(parsed: ParsedIntelligenceReport) -> str:
    insight_section = next(
        (section for section in parsed.sections if section.title.lower() == "ai insights"),
        None,
    )

    if not insight_section:
        return ""

    bullets = _bullets_from_text(insight_section.body)

    return bullets[0] if bullets else insight_section.body.split("\n")[0][:180]


def top_opportunities(parsed: ParsedIntelligenceReport) -> list[str]:
    dashboard = next(
        (section for section in parsed.sections if "dashboard" in section.title.lower()),
        None,
    )

    if dashboard:
        bullets = _bullets_from_text(_extract_subsection(dashboard.body, "Key Opportunities"))
        if bullets:
            return bullets

    # SPA-format reports have no "dashboard" section — opportunities
    # live in their own top-level "Opportunities" section instead.
    opportunities_section = next(
        (section for section in parsed.sections if "opportunit" in section.title.lower()),
        None,
    )
    return _bullets_from_text(opportunities_section.body) if opportunities_section else []


def strategic_recommendation(parsed: ParsedIntelligenceReport) -> str:
    recommendations = next(
        (
            section
            for section in parsed.sections
            if "strategic recommendation" in section.title.lower()
        ),
        None,
    )

    if recommendations:
        action_match = re.search(r"\*\*Action:\*\*\s*(.+)", recommendations.body)

        if action_match:
            return strip_inline_markdown(action_match.group(1).strip())

        first_line = recommendations.body.split("\n")[0].strip()

        if first_line:
            return first_line.lstrip("#").strip()

    card = parsed.summary_card

    return card.get("Priority", "") or card.get("Overall Trend", "")


def ai_insight_bullets(parsed: ParsedIntelligenceReport) -> list[str]:
    insight_section = next(
        (section for section in parsed.sections if section.title.lower() == "ai insights"),
        None,
    )

    if not insight_section:
        return []

    return _bullets_from_text(insight_section.body)
