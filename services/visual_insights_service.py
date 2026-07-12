"""
On-demand visual insights enrichment for completed reports.
"""

from __future__ import annotations

from models.report_data import ReportData
from services.visualization_decision import (
    VisualizationDecision,
    evaluate_visualization_decision,
    low_confidence_user_message,
)
from services.visualization_engine import apply_visualizations


def get_stored_decision(report_data: ReportData) -> VisualizationDecision | None:
    charts = report_data.charts or {}
    return VisualizationDecision.from_dict(charts.get("visualization_decision"))


def explore_visual_insights(
    report_data: ReportData,
    *,
    user_report_type: str = "",
    document_text: str = "",
    reporting_period: str = "",
    append_only: bool = False,
) -> tuple[ReportData, VisualizationDecision, str | None]:
    """
    Analyse a completed report and attach visualizations when appropriate.

    Returns the updated report, the decision record, and an optional friendly
    message when no meaningful visuals could be added.
    """

    resolved_type = user_report_type or report_data.report_type
    existing_blocks = list((report_data.charts or {}).get("visualizations") or [])
    updated = apply_visualizations(
        report_data,
        user_report_type=resolved_type,
        document_text=document_text or report_data.narrative,
        include_charts=True,
        force_generate=True,
        append_only=append_only and bool(existing_blocks),
        reporting_period=reporting_period,
    )

    decision = get_stored_decision(updated) or evaluate_visualization_decision(
        report_data,
        user_report_type=resolved_type,
        document_text=document_text or report_data.narrative,
        reporting_period=reporting_period,
    )

    new_blocks = list((updated.charts or {}).get("visualizations") or [])
    if append_only and existing_blocks and len(new_blocks) <= len(existing_blocks):
        message = low_confidence_user_message()
        decision.user_message = message
        return updated, decision, message

    if not new_blocks:
        message = decision.user_message or low_confidence_user_message()
        return updated, decision, message

    return updated, decision, None
