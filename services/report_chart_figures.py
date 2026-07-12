"""
Shared Plotly chart builders for browser preview and document export.

Visualization decisions are made by services.visualization_engine. This module
turns structured visualization blocks (or legacy chart metadata) into Plotly figures.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go

CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#1D4ED8", "#1E40AF"]
RISK_COLORS = ["#DC2626", "#F97316", "#F59E0B"]
VISUAL_SUMMARY_HEADINGS = {
    "visual summary",
    "visual analytics",
    "executive dashboard",
}


def has_chart_visuals(chart_data: dict[str, Any] | None) -> bool:
    if not chart_data:
        return False

    if chart_data.get("visualizations"):
        return True

    if chart_data.get("_suppress_theme_charts"):
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


def _figure_from_visualization_block(block: dict[str, Any]) -> tuple[str, go.Figure] | None:
    block_type = str(block.get("type", "")).upper()
    title = str(block.get("title", "Visualization"))
    data = block.get("data") or {}

    if block_type == "BAR_CHART":
        series = data.get("series") or []
        if not series:
            return None
        labels = [item.get("label", "") for item in series]
        values = [float(item.get("value", 0)) for item in series]
        figure = px.bar(
            x=labels,
            y=values,
            labels={"x": "Metric", "y": "Value"},
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
        figure.update_layout(**chart_layout())
        figure.update_traces(marker_line_width=0)
        return title, figure

    if block_type == "LINE_CHART":
        trends = data.get("trends") or []
        if not trends:
            return None
        labels = [item.get("label", "") for item in trends]
        prior = [float(item.get("prior", 0)) for item in trends]
        current = [float(item.get("current", 0)) for item in trends]
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=labels,
                y=prior,
                mode="lines+markers",
                name="Previous",
                line={"color": "#94A3B8", "width": 2},
            )
        )
        figure.add_trace(
            go.Scatter(
                x=labels,
                y=current,
                mode="lines+markers",
                name="Current",
                line={"color": "#2563EB", "width": 3},
            )
        )
        figure.update_layout(
            **chart_layout(title=title),
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        )
        return title, figure

    if block_type == "PIE_CHART":
        series = data.get("series") or []
        if not series:
            return None
        labels = [item.get("label", "") for item in series]
        values = [float(item.get("value", 0)) for item in series]
        figure = px.pie(
            names=labels,
            values=values,
            title=title,
            color_discrete_sequence=CHART_COLORS,
            hole=0.42,
        )
        figure.update_layout(**chart_layout())
        return title, figure

    if block_type == "KPI_CARDS":
        items = data.get("items") or []
        if not items:
            return None
        labels = [item.get("label", "") for item in items]
        values = [float(item.get("value", 0) or 0) for item in items]
        figure = px.bar(
            x=labels,
            y=values,
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
        figure.update_layout(**chart_layout())
        figure.update_traces(marker_line_width=0)
        return title, figure

    if block_type == "TIMELINE":
        events = data.get("events") or []
        if not events:
            return None
        labels = [event.get("label", "") for event in events]
        positions = list(range(len(labels)))
        figure = go.Figure(
            go.Scatter(
                x=positions,
                y=[1] * len(labels),
                mode="markers+text",
                text=[event.get("date", "") for event in events],
                textposition="top center",
                marker={"size": 14, "color": CHART_COLORS[0]},
                hovertext=labels,
                hoverinfo="text",
            )
        )
        figure.update_layout(
            **chart_layout(title=title, height=220),
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return title, figure

    if block_type == "RISK_MATRIX":
        rows = data.get("rows") or []
        if not rows:
            return None
        labels = [row.get("risk", "") for row in rows]
        severity = [float(row.get("severity", 0)) for row in rows]
        figure = px.bar(
            x=labels,
            y=severity,
            title=title,
            color_discrete_sequence=RISK_COLORS,
        )
        figure.update_layout(**chart_layout())
        return title, figure

    if block_type == "DECISION_MATRIX":
        rows = data.get("rows") or []
        if not rows:
            return None
        labels = [row.get("party", "") for row in rows]
        values = [1.0] * len(labels)
        figure = px.bar(
            x=labels,
            y=values,
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
        figure.update_layout(**chart_layout(), showlegend=False)
        figure.update_yaxes(visible=False)
        return title, figure

    if block_type == "ORGANIZATIONAL_FLOW":
        nodes = data.get("nodes") or []
        if not nodes:
            return None
        labels = [node.get("label", "") for node in nodes]
        figure = px.bar(
            x=labels,
            y=[1.0] * len(labels),
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
        figure.update_layout(**chart_layout(), showlegend=False)
        figure.update_yaxes(visible=False)
        return title, figure

    return None


def build_figures_from_visualizations(
    visualizations: list[dict[str, Any]],
) -> list[tuple[str, go.Figure]]:
    figures: list[tuple[str, go.Figure]] = []

    for block in sorted(visualizations, key=lambda item: item.get("priority", 99)):
        rendered = _figure_from_visualization_block(block)
        if rendered:
            figures.append(rendered)

    return figures


def _build_legacy_theme_figures(chart_data: dict[str, Any]) -> list[tuple[str, go.Figure]]:
    """Legacy path for stored reports that predate the visualization engine."""

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


def build_report_chart_figures(chart_data: dict[str, Any]) -> list[tuple[str, go.Figure]]:
    """Build Plotly figures from visualization blocks or legacy chart metadata."""

    if not has_chart_visuals(chart_data):
        return []

    visualizations = chart_data.get("visualizations") or []
    if visualizations:
        return build_figures_from_visualizations(visualizations)

    return _build_legacy_theme_figures(chart_data)
