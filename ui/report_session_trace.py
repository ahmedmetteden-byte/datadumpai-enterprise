"""
Diagnostic logging for report generation → session_state → preview rendering.

Used to verify which report keys are populated after OpenAI returns and whether
any are cleared across Streamlit reruns.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)

# Keys historically suspected of holding the generated report — plus the ones
# this app actually uses (`draft_report`, `selected_report`).
SUSPECTED_REPORT_KEYS = (
    "current_report",
    "current_report_content",
    "saved_reports",
    "generated_report",
    "report_preview",
    "draft_report",
    "selected_report",
)


def _draft_summary(draft: Any) -> dict[str, Any] | None:
    if not isinstance(draft, dict):
        return None

    report = draft.get("report") or {}
    if not isinstance(report, dict):
        report = {}

    narrative = report.get("narrative") or ""
    return {
        "report_type": report.get("report_type"),
        "narrative_chars": len(narrative),
        "source_documents": list(draft.get("source_documents") or []),
        "has_workspace": bool(draft.get("workspace")),
        "processing_mode": draft.get("processing_mode"),
    }


def log_report_session_state(stage: str) -> None:
    """Log presence/absence of report-related session_state keys at a pipeline stage."""

    present = {key: key in st.session_state for key in SUSPECTED_REPORT_KEYS}
    populated = [key for key, exists in present.items() if exists]
    missing_suspected = [
        key
        for key in (
            "current_report",
            "current_report_content",
            "saved_reports",
            "generated_report",
            "report_preview",
        )
        if key not in st.session_state
    ]

    draft = st.session_state.get("draft_report")
    selected = st.session_state.get("selected_report")
    selected_summary = None
    if isinstance(selected, dict):
        selected_summary = {
            "filename": selected.get("filename"),
            "name": selected.get("name") or selected.get("report_type"),
        }

    logger.info(
        "Report session_state at %s: populated=%s missing_suspected=%s "
        "draft_report=%s selected_report=%s",
        stage,
        populated,
        missing_suspected,
        _draft_summary(draft),
        selected_summary,
    )
