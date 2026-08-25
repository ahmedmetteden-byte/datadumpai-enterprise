"""
Shared Plotly chart builders for browser preview and document export.

Visualization decisions are made by services.visualization_engine. This module
turns structured visualization blocks (or legacy chart metadata) into Plotly figures.
"""

from __future__ import annotations

import re
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


def _axis_tick_format(unit: str, values: list[float]) -> dict[str, Any]:
    """Plotly tick-formatting kwargs for a value axis, derived from the
    metric's own `unit` field (never guessed from chart title text).

    Deliberately does NOT rely on a rotated axis title string to convey
    the unit — a long/redundant title (e.g. a metric name that already
    contains "($m)" combined with a separately-appended "($ million)")
    was found to overflow Kaleido's rotated-text layout and render
    corrupted in real production PDFs (confirmed by direct reproduction:
    "Total Claims Incurred ($m) ($ million)" rendered as a garbled,
    truncated "m)(" fragment). Encoding the unit into tick labels instead
    is both more robust and more readable.
    """

    unit = (unit or "").strip()
    if unit.startswith("$"):
        fmt: dict[str, Any] = {"tickprefix": "$", "tickformat": ",.0f"}
        if "billion" in unit:
            fmt["ticksuffix"] = "bn"
        elif "million" in unit:
            fmt["ticksuffix"] = "m"
        return fmt
    if unit == "%":
        # Percent-unit values are not consistently scaled upstream (a
        # column can store 0.86 or 86 depending on how the source cell
        # was formatted) — only apply the auto-multiplying ".0%" format
        # when values already look like fractions, otherwise just label
        # the existing scale rather than guessing and risking a silent
        # 100x display error.
        if values and max(abs(v) for v in values) <= 1.5:
            return {"tickformat": ".0%"}
        return {"ticksuffix": "%"}
    if values and max(abs(v) for v in values) >= 1000:
        return {"tickformat": ",.0f"}
    return {}


_MONTH_YEAR_LABEL = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|"
    r"December)\s+(\d{4})$",
    re.IGNORECASE,
)
_MONTH_ABBREVIATIONS = {
    "january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr",
    "may": "May", "june": "Jun", "july": "Jul", "august": "Aug",
    "september": "Sep", "october": "Oct", "november": "Nov", "december": "Dec",
}


def _chart_axis_label(label: str) -> str:
    """A concise x-axis tick label — "January 2026" -> "Jan 2026" — so a
    handful of period ticks don't crowd a 280px-tall chart. Only touches
    a recognized full-month-name label; anything else (a category name,
    a filename that leaked in, an already-short label) passes through
    unchanged rather than risk mangling text this function doesn't
    understand the shape of."""

    match = _MONTH_YEAR_LABEL.match(label.strip())
    if not match:
        return label
    return f"{_MONTH_ABBREVIATIONS[match.group(1).lower()]} {match.group(2)}"


def _format_value_label(unit: str, value: float) -> str:
    """Human-readable value label matching `_axis_tick_format`'s scale
    assumptions, used for on-chart data-point/bar annotations."""

    unit = (unit or "").strip()
    if unit.startswith("$"):
        if "billion" in unit:
            return f"${value:,.2f}bn"
        if "million" in unit:
            return f"${value:,.1f}m"
        return f"${value:,.0f}"
    if unit == "%":
        pct = value * 100 if abs(value) <= 1.5 else value
        return f"{pct:,.1f}%"
    if value == int(value):
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _figure_from_visualization_block(block: dict[str, Any]) -> tuple[str, go.Figure] | None:
    block_type = str(block.get("type", "")).upper()
    title = str(block.get("title", "Visualization"))
    data = block.get("data") or {}

    if block_type == "BAR_CHART":
        series = data.get("series") or []
        if not series:
            return None
        labels = [_chart_axis_label(str(item.get("label", ""))) for item in series]
        values = [float(item.get("value", 0)) for item in series]
        unit = str(block.get("unit") or "")
        x_label = str(block.get("x_label") or "Category")
        figure = px.bar(
            x=labels,
            y=values,
            labels={"x": x_label},
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
        figure.update_layout(**chart_layout())
        top = max(values) * 1.18 if values and max(values) > 0 else 1
        figure.update_traces(
            marker_line_width=0,
            text=[_format_value_label(unit, v) for v in values],
            textposition="outside",
            textfont={"size": 11, "color": "#0F172A"},
        )
        figure.update_yaxes(
            title="",
            range=[0, top],
            gridcolor="#E2E8F0",
            zeroline=False,
            **_axis_tick_format(unit, values),
        )
        figure.update_xaxes(gridcolor="#F1F5F9")
        return title, figure

    if block_type == "LINE_CHART":
        points = data.get("points")
        if points is None:
            # Legacy shape (chart data persisted before Phase 3 Step 3):
            # a list of {label, prior, current} pairs whose `label` only
            # ever captured the SECOND row of each pair — the first
            # period's own label was never stored at all, which was the
            # bug (a 3+-period series silently lost its first x-axis
            # position). Best-effort recovery for already-saved reports:
            # the first point's VALUE is still present
            # (trends[0]["prior"]) even though its label was never
            # captured — left blank rather than guessed, which is still
            # strictly better than the old behavior of silently plotting
            # it under the WRONG (second period's) label.
            trends = data.get("trends") or []
            if not trends:
                return None
            points = [{"label": "", "value": trends[0].get("prior")}] + [
                {"label": item.get("label", ""), "value": item.get("current")} for item in trends
            ]
        if not points:
            return None
        labels = [_chart_axis_label(str(p.get("label", ""))) for p in points]
        values = [float(p.get("value", 0) or 0) for p in points]
        # Defensive guard (Phase 3 Step 2, still applies to the new
        # shape): if 2+ points collapse onto the same x-axis label (e.g.
        # a categorical series ever mis-classified as temporal
        # upstream), a connected line would read as a real trend where
        # none exists. Per "a bad chart is worse than no chart," omit
        # rather than render that. Blank labels (the legacy-shape
        # recovered first point above) are excluded from this check —
        # they're a single, deliberate placeholder, not a collapse.
        real_labels = [l for l in labels if l]
        if len(real_labels) >= 2 and len(set(real_labels)) < 2:
            return None

        unit = str(block.get("unit") or "")
        value_labels = [_format_value_label(unit, v) for v in values]
        # Label only the first and last points (not every point) so the
        # chart states its own headline numbers without becoming cluttered.
        # These MUST be trace-native text (mode="...+text"), never a
        # separate `add_annotation()` call: on a category x-axis,
        # Kaleido's static-image renderer was found to silently collapse
        # every point onto the first x position — and mis-place the
        # annotation itself — the moment an annotation referencing that
        # axis is added (confirmed by direct reproduction: a single
        # `add_annotation(x="2023", ...)` call alone, with no other
        # change, turned a correct 3-point 2023/2024/2025 line into all
        # three points stacked at "2023" with "2024"/"2025" missing from
        # the axis entirely). Trace-native `text`/`textposition` has none
        # of this failure mode.
        last_idx = len(points) - 1
        point_text = [
            value_labels[i] if i in (0, last_idx) else "" for i in range(len(points))
        ]
        text_positions = [
            "top right" if i == 0 else "top left" if i == last_idx else "top center"
            for i in range(len(points))
        ]
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=labels,
                y=values,
                mode="lines+markers+text",
                name=title,
                line={"color": "#2563EB", "width": 3},
                marker={"color": "#2563EB", "size": 8, "line": {"color": "#FFFFFF", "width": 1.5}},
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.10)",
                text=point_text,
                textposition=text_positions,
                textfont={"size": 12, "color": "#1D4ED8", "family": "Inter, sans-serif"},
                customdata=value_labels,
                hovertemplate="%{x}: %{customdata}<extra></extra>",
            )
        )
        # Explicit range (rather than autorange) so "fill='tozeroy'" reads
        # as a soft shaded band under the line, clipped to the visible
        # window — not a chart squashed flat against a y=0 baseline that
        # can be far below the metric's real, meaningful range.
        lo = min(values)
        hi = max(values)
        pad = (hi - lo) * 0.15 if hi > lo else (abs(hi) * 0.1 or 1.0)
        figure.update_layout(
            **chart_layout(
                title=title,
                xaxis_title=str(block.get("x_label") or "Period"),
                margin=dict(l=20, r=50, t=40, b=20),
            ),
        )
        figure.update_yaxes(
            range=[lo - pad, hi + pad],
            gridcolor="#E2E8F0",
            zeroline=False,
            **_axis_tick_format(unit, values),
        )
        figure.update_xaxes(gridcolor="#F1F5F9")
        return title, figure

    if block_type == "PIE_CHART":
        series = data.get("series") or []
        if not series:
            return None
        labels = [_chart_axis_label(str(item.get("label", ""))) for item in series]
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
        # Every item shares one unit by construction (visualization_engine.py's
        # unit-consistency gate groups KPI candidates by unit before this
        # block is ever built), so the first item's unit applies to all.
        unit = str(items[0].get("unit") or "") if items else ""
        x_label = str(block.get("x_label") or "Metric")
        figure = px.bar(
            x=labels,
            y=values,
            labels={"x": x_label},
            title=title,
            color_discrete_sequence=CHART_COLORS,
        )
        figure.update_layout(**chart_layout())
        top = max(values) * 1.18 if values and max(values) > 0 else 1
        figure.update_traces(
            marker_line_width=0,
            text=[_format_value_label(unit, v) for v in values],
            textposition="outside",
            textfont={"size": 11, "color": "#0F172A"},
        )
        figure.update_yaxes(
            title="",
            range=[0, top],
            gridcolor="#E2E8F0",
            zeroline=False,
            **_axis_tick_format(unit, values),
        )
        figure.update_xaxes(gridcolor="#F1F5F9")
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
            labels={"x": "Risk", "y": "Severity"},
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
            labels={"x": "Party"},
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
            labels={"x": "Stakeholder"},
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
