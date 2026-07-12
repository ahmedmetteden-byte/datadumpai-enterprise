"""
Report insights panel and Explore Visual Insights action.
"""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

from models.report_data import ReportData
from services.plan_service import PlanService
from services.report_chart_figures import has_chart_visuals
from services.visual_insights_service import explore_visual_insights, get_stored_decision
from services.visualization_decision import (
    VisualizationConfidenceLevel,
    VisualizationDecision,
    evaluate_visualization_decision,
)
from ui.feedback import loading


def _plan_service() -> PlanService:
    return PlanService()


def _confidence_label(level: VisualizationConfidenceLevel) -> str:
    return {
        VisualizationConfidenceLevel.HIGH: "High",
        VisualizationConfidenceLevel.MEDIUM: "Medium",
        VisualizationConfidenceLevel.LOW: "Low",
    }[level]


def _resolve_decision(report: ReportData, *, reporting_period: str = "") -> VisualizationDecision:
    stored = get_stored_decision(report)
    if stored:
        return stored

    return evaluate_visualization_decision(
        report,
        user_report_type=report.report_type,
        document_text=report.narrative,
        reporting_period=reporting_period,
    )


def render_report_insights_panel(
    report: ReportData,
    *,
    reporting_period: str = "",
) -> None:
    """Show how the AI classified the report and which visuals are recommended."""

    decision = _resolve_decision(report, reporting_period=reporting_period)
    has_charts = has_chart_visuals(report.charts)

    recommended = decision.suggested_visualizations or []
    if has_charts and not recommended:
        recommended = [
            str(block.get("title", "Chart"))
            for block in (report.charts or {}).get("visualizations") or []
            if block.get("title")
        ]

    items = "".join(
        f"<li>{html.escape(label)}</li>"
        for label in recommended[:6]
    ) or "<li>No chart recommendations yet</li>"

    status = "Generated" if has_charts else "Available on request"

    st.markdown(
        f"""
<div class="dde-report-insights">
<div class="dde-report-insights-title">Report Insights</div>
<div class="dde-report-insights-grid">
<div><span class="dde-report-insights-label">Document Type</span>{html.escape(decision.document_type)}</div>
<div><span class="dde-report-insights-label">Visualization Confidence</span>{_confidence_label(decision.level)} ({decision.confidence}%)</div>
<div><span class="dde-report-insights-label">Chart Status</span>{status}</div>
</div>
<div class="dde-report-insights-recommended">
<div class="dde-report-insights-label">Recommended Visuals</div>
<ul>{items}</ul>
</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_explore_visual_insights(
    report: ReportData,
    *,
    key_prefix: str,
    reporting_period: str = "",
    on_report_updated: Callable[[ReportData], None] | None = None,
) -> ReportData:
    """
    Render the Explore Visual Insights action and return the latest report state.
    """

    message_key = f"{key_prefix}_visual_insights_message"
    stored_message = st.session_state.pop(message_key, None)

    if stored_message:
        st.info(stored_message)

    if not _plan_service().include_professional_charts():
        st.caption("Visual insights are available on the Professional plan.")
        return report

    has_charts = has_chart_visuals(report.charts)
    button_label = (
        "Explore More Visual Insights"
        if has_charts
        else "Explore Visual Insights"
    )

    if st.button(
        button_label,
        use_container_width=True,
        key=f"{key_prefix}_explore_visual_insights",
    ):
        with loading("Analysing report for visual insights…"):
            updated, decision, message = explore_visual_insights(
                report,
                user_report_type=report.report_type,
                document_text=report.narrative,
                reporting_period=reporting_period,
                append_only=has_charts,
            )

        if message:
            st.session_state[message_key] = message
        elif decision.level == VisualizationConfidenceLevel.HIGH and has_charts:
            st.session_state[message_key] = (
                "Additional visual insights were added where they improve understanding."
            )
        else:
            st.session_state[message_key] = (
                "Visual insights were added to this report."
            )

        if on_report_updated:
            on_report_updated(updated)

        st.rerun()

    return report
