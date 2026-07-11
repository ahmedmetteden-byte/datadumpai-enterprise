"""
Shared Plotly chart builders for browser preview and document export.

REPORT_CHARTS JSON is parsed upstream in services.report_chart_data. This module
turns that structured data into Plotly figures used by both Streamlit and export.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go

CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#1D4ED8", "#1E40AF"]
RISK_COLORS = ["#DC2626", "#F97316", "#F59E0B"]
VISUAL_SUMMARY_HEADINGS = {"visual summary", "visual analytics"}


def has_chart_visuals(chart_data: dict[str, Any] | None) -> bool:
    if not chart_data:
        return False

    return bool(
        chart_data.get("topics")
        or chart_data.get("trends")
        or chart_data.get("risk_distribution")
    )


def is_visual_summary_heading(title: str) -> bool:
    return title.strip().lower() in VISUAL_SUMMARY_HEADINGS


def chart_layout(**extra: Any) -> dict[str, Any]:
    layout = {
        "margin": dict(l=20, r=20, t=40, b=20),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, sans-serif", "color": "#0F172A"},
        "height": 280,
    }
    layout.update(extra)
    return layout


def build_report_chart_figures(chart_data: dict[str, Any]) -> list[tuple[str, go.Figure]]:
    """Build the Plotly figures shown in Visual Analytics."""

    if not has_chart_visuals(chart_data):
        return []

    figures: list[tuple[str, go.Figure]] = []
    topics = chart_data.get("topics") or []
    trends = chart_data.get("trends") or []
    risk_distribution = chart_data.get("risk_distribution") or []

    if topics:
        labels = [item.get("label", "") for item in topics]
        values = [float(item.get("value", 0)) for item in topics]

        bar_figure = px.bar(
            x=labels,
            y=values,
            labels={"x": "Theme", "y": "Share (%)"},
            title="Top Discussion Topics",
            color_discrete_sequence=CHART_COLORS,
        )
        bar_figure.update_layout(**chart_layout())
        bar_figure.update_traces(marker_line_width=0)
        figures.append(("Top Discussion Topics", bar_figure))

        pie_figure = px.pie(
            names=labels,
            values=values,
            title="Theme Distribution",
            color_discrete_sequence=CHART_COLORS,
            hole=0.42,
        )
        pie_figure.update_layout(**chart_layout())
        figures.append(("Theme Distribution", pie_figure))

    if trends:
        labels = [item.get("label", "") for item in trends]
        prior = [float(item.get("prior", 0)) for item in trends]
        current = [float(item.get("current", 0)) for item in trends]

        trend_figure = go.Figure()
        trend_figure.add_trace(
            go.Scatter(
                x=labels,
                y=prior,
                mode="lines+markers",
                name="Previous",
                line={"color": "#94A3B8", "width": 2},
            )
        )
        trend_figure.add_trace(
            go.Scatter(
                x=labels,
                y=current,
                mode="lines+markers",
                name="Current",
                line={"color": "#2563EB", "width": 3},
            )
        )
        trend_figure.update_layout(
            **chart_layout(title="Theme Trends"),
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        )
        figures.append(("Theme Trends", trend_figure))

    if risk_distribution and not topics:
        labels = [item.get("label", "") for item in risk_distribution]
        values = [float(item.get("value", 0)) for item in risk_distribution]

        risk_figure = px.bar(
            x=labels,
            y=values,
            title="Risk Distribution",
            color_discrete_sequence=RISK_COLORS,
        )
        risk_figure.update_layout(**chart_layout())
        figures.append(("Risk Distribution", risk_figure))

    return figures
