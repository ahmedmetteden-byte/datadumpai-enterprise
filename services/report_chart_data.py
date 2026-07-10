"""
Parse machine-readable chart metadata embedded in intelligence reports.
"""

from __future__ import annotations

import json
import re
from typing import Any

CHART_DATA_PATTERN = re.compile(
    r"<!--\s*REPORT_CHARTS\s*(\{[\s\S]*?\})\s*-->",
    re.IGNORECASE,
)

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
    match = CHART_DATA_PATTERN.search(report_text)

    if not match:
        return {}

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


def strip_chart_data(report_text: str) -> str:
    return CHART_DATA_PATTERN.sub("", report_text).strip()


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
