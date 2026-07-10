"""
Render executive intelligence reports with visual styling in Streamlit.
"""

from __future__ import annotations

import html
import re

import streamlit as st

from services.report_chart_data import (
    extract_chart_data,
    extract_executive_summary_card,
    is_intelligence_report,
    normalize_intelligence_title,
    strip_chart_data,
)
from ui.report_charts import render_report_charts

CONFIDENCE_PATTERN = re.compile(
    r"\*\*Confidence:\*\*\s*(\d{1,3})%",
    re.IGNORECASE,
)

HEALTH_SCORE_PATTERN = re.compile(
    r"\*\*Score:\*\*\s*(\d{1,3})/100",
    re.IGNORECASE,
)

QUOTE_BLOCK_PATTERN = re.compile(
    r"(^> .+(?:\n> .+)*)",
    re.MULTILINE,
)


def _confidence_badge(value: str) -> str:
    try:
        score = int(value)
    except ValueError:
        return value

    if score >= 85:
        level = "high"
    elif score >= 60:
        level = "medium"
    else:
        level = "low"

    return (
        f'<span class="dde-confidence dde-confidence-{level}">'
        f"Confidence: {score}%</span>"
    )


def _health_gauge_html(score: int) -> str:
    safe_score = max(0, min(score, 100))

    return (
        f'<div class="dde-health-visual">'
        f'<div class="dde-health-gauge" style="--score:{safe_score}">'
        f'<div class="dde-health-gauge-inner">{safe_score}%</div>'
        f"</div>"
        f'<div class="dde-health-bar-wrap">'
        f'<div class="dde-health-bar-track">'
        f'<div class="dde-health-bar-fill" style="width:{safe_score}%"></div>'
        f"</div>"
        f'<div class="dde-health-bar-label">Overall health · {safe_score}/100</div>'
        f"</div>"
        f"</div>"
    )


def _render_summary_card_html(card: dict[str, str]) -> str:
    cells = []

    for label, value in card.items():
        cells.append(
            f'<div class="dde-summary-card-item">'
            f'<div class="dde-summary-card-label">{html.escape(label)}</div>'
            f'<div class="dde-summary-card-value">{html.escape(value)}</div>'
            f"</div>"
        )

    return (
        '<div class="dde-executive-summary-card">'
        '<div class="dde-executive-summary-card-title">Executive Summary</div>'
        f'<div class="dde-executive-summary-card-grid">{"".join(cells)}</div>'
        "</div>"
    )


def _style_quote_blocks(markdown_text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        lines = [
            line.lstrip("> ").strip()
            for line in match.group(1).splitlines()
            if line.strip()
        ]

        if not lines:
            return match.group(0)

        quote = html.escape(lines[0].strip('"'))
        attribution = ""

        if len(lines) > 1:
            attribution = (
                f'<div class="dde-quote-attribution">'
                f"{html.escape(lines[-1])}"
                f"</div>"
            )

        return (
            f'<div class="dde-executive-quote">'
            f'<div class="dde-quote-mark">“</div>'
            f'<div class="dde-quote-text">{quote}</div>'
            f"{attribution}"
            f"</div>"
        )

    return QUOTE_BLOCK_PATTERN.sub(_replace, markdown_text)


def _style_benchmark_tables(markdown_text: str) -> str:
    return markdown_text.replace(
        "## Industry Benchmark",
        '## Industry Benchmark <span class="dde-section-tag">Current vs Previous</span>',
        1,
    )


def enhance_report_markdown(markdown_text: str) -> str:
    """Add inline HTML styling to executive intelligence report markdown."""

    if not markdown_text.strip():
        return markdown_text

    enhanced = markdown_text
    enhanced = CONFIDENCE_PATTERN.sub(
        lambda match: _confidence_badge(match.group(1)),
        enhanced,
    )
    enhanced = HEALTH_SCORE_PATTERN.sub(
        lambda match: _health_gauge_html(int(match.group(1))),
        enhanced,
    )
    enhanced = _style_quote_blocks(enhanced)
    enhanced = _style_benchmark_tables(enhanced)

    return enhanced


def render_report_content(report_text: str) -> None:
    """Render a report with executive intelligence styling when applicable."""

    if not is_intelligence_report(report_text):
        st.markdown(report_text)
        return

    chart_data = extract_chart_data(report_text)
    body = strip_chart_data(report_text)
    body = normalize_intelligence_title(body)

    summary_card, body = extract_executive_summary_card(body)

    if summary_card:
        st.markdown(_render_summary_card_html(summary_card), unsafe_allow_html=True)

    if chart_data:
        render_report_charts(chart_data)

    styled = enhance_report_markdown(body)
    st.markdown(
        f'<div class="dde-intelligence-report">{styled}</div>',
        unsafe_allow_html=True,
    )
