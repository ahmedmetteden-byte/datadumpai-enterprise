"""
Parse machine-readable chart metadata embedded in intelligence reports.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from models.report_data import ReportData
from services.report_markdown_renderer import remove_empty_sections

CHART_BLOCK_OPENER = re.compile(r"<!--\s*REPORT_?CHARTS\s*", re.IGNORECASE)
CHART_BLOCK_PATTERN = re.compile(r"<!--\s*REPORT_?CHARTS\s*[\s\S]*?-->", re.IGNORECASE)

SUMMARY_CARD_PATTERN = re.compile(
    r"### Executive Summary Card\s*\n+"
    r"(\|[^\n]+\|\n\|[-| :]+\|\n(?:\|[^\n]+\|\n?)+)",
    re.IGNORECASE,
)


def is_intelligence_report(report_text: str) -> bool:
    return (
        "## Executive Intelligence Dashboard" in report_text
        or "## Executive Dashboard" in report_text
    )


def extract_chart_data(report_text: str) -> dict[str, Any]:
    opener = CHART_BLOCK_OPENER.search(report_text)

    if not opener:
        return {}

    closer = report_text.find("-->", opener.end())

    if closer == -1:
        return {}

    try:
        payload = json.loads(report_text[opener.end() : closer].strip())
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


def strip_chart_data(report_text: str) -> str:
    return CHART_BLOCK_PATTERN.sub("", report_text).strip()


@dataclass(frozen=True)
class PreparedReport:
    """User-facing report text with chart metadata extracted for rendering."""

    text: str
    chart_data: dict[str, Any]


def prepare_report_for_output(
    report_text: str,
    report_data: ReportData | None = None,
) -> PreparedReport:
    """Parse internal chart metadata and return cleaned report text for display/export."""

    canonical_charts = report_data.charts if report_data and report_data.charts else {}
    embedded_charts = extract_chart_data(report_text)
    chart_data = canonical_charts or embedded_charts

    return PreparedReport(
        text=remove_empty_sections(strip_chart_data(report_text)),
        chart_data=chart_data,
    )


def extract_executive_summary_card(report_text: str) -> tuple[dict[str, str], str]:
    """Pull the executive summary card table out of the report body."""

    match = SUMMARY_CARD_PATTERN.search(report_text)

    if not match:
        return {}, report_text

    table_text = match.group(1)
    rows = [line.strip() for line in table_text.splitlines() if line.strip()]

    if len(rows) < 3:
        return {}, report_text

    card: dict[str, str] = {}

    for row in rows[2:]:
        cells = [cell.strip() for cell in row.strip("|").split("|")]

        if len(cells) >= 2 and cells[0] and cells[1]:
            card[cells[0]] = cells[1]

    remaining = report_text[: match.start()] + report_text[match.end() :]

    return card, remaining.strip()


def normalize_intelligence_title(report_text: str) -> str:
    return report_text.replace(
        "## Executive Dashboard",
        "## Executive Intelligence Dashboard",
        1,
    )
