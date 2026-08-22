"""
Bridges quantitative_analysis_service.py's calculated MetricSeries output
into visualization_engine.py's VisualizationBlock chart data.

Chart generation used to work by re-parsing the already-rendered narrative
text via regex (services/visualization_engine.py's _financial_series() /
_table_financial_series()) — disconnected from the deterministic
calculations quantitative_analysis_service.py already computed. This
module closes that gap: charts for the metrics Step A's ReportPlan
decided matter most are now built directly from real rows and real units,
never invented from text and never generated "because numbers exist".

The regex-based fallback in visualization_engine.py stays in place
unchanged — it's still needed for reports with no usable metric tables.
"""

from __future__ import annotations

import os
from typing import Any

from services.visualization_engine import VisualizationBlock, VisualizationStrategy

REPORT_CHART_METRIC_BRIDGE_ENABLED = os.getenv(
    "REPORT_CHART_METRIC_BRIDGE_ENABLED", "true"
).strip().lower() not in {"0", "false", "no"}


def metric_series_to_chart_data(series: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one quantitative_analysis_service MetricSeries dict into
    VisualizationBlock-shaped chart data.

    Temporal series (has period_over_period calculations) become a
    LINE_CHART: one continuous point per row — {label, value} for every
    row in the series, in order — so a 3+-period series gets one line
    with every period as its own x-axis position. (Phase 3 Step 3: this
    replaces an earlier "Previous vs Current" pairwise design that only
    ever labeled a trend point from zip(rows, rows[1:])'s SECOND row,
    silently dropping the first period from the x-axis entirely for any
    series with 3+ rows — confirmed by direct reproduction: a 2023/2024/
    2025 series rendered with only "2024"/"2025" on the axis, 2023's
    value plotted one position to the right of where it belonged.)

    Categorical (non-temporal) series become a BAR_CHART, one bar per row.

    Returns None for a series with fewer than 2 rows — nothing to chart.
    """

    rows = series.get("rows") or []
    if len(rows) < 2:
        return None

    is_temporal = bool((series.get("calculations") or {}).get("period_over_period"))

    if is_temporal:
        points = [
            {"label": str(row.get("label", "")), "value": row.get("value")} for row in rows
        ]
        return {"type": "LINE_CHART", "data": {"points": points}}

    bar_series = [
        {"label": str(row.get("label", "")), "value": row.get("value")} for row in rows
    ]
    return {"type": "BAR_CHART", "data": {"series": bar_series}}


def select_chart_candidates(
    metric_tables: list[dict[str, Any]],
    chart_requirements: list[dict[str, Any]],
) -> list[VisualizationBlock]:
    """Build VisualizationBlocks for exactly the metrics Step A's
    ReportPlan already decided deserve a chart (chart_requirements,
    already capped and materiality-ranked) — never for every metric that
    happens to exist. Skips a requirement if its metric table can no
    longer be found or has too little data to chart."""

    if not REPORT_CHART_METRIC_BRIDGE_ENABLED:
        return []

    by_title = {str(table.get("title") or ""): table for table in metric_tables}
    blocks: list[VisualizationBlock] = []

    for index, requirement in enumerate(chart_requirements, start=1):
        title = str(requirement.get("metric_title") or "")
        table = by_title.get(title)
        if not table:
            continue

        chart_data = metric_series_to_chart_data(table)
        if not chart_data:
            continue

        unit = str(table.get("unit") or "")
        is_temporal = chart_data["type"] == "LINE_CHART"
        blocks.append(
            VisualizationBlock(
                title=title,
                type=VisualizationStrategy(chart_data["type"]),
                description=str(requirement.get("reason") or f"{title} over the reporting period."),
                data=chart_data["data"],
                priority=index,
                decision_question=f"How has {title} changed?",
                unit=unit,
                x_label="Period" if is_temporal else "Category",
                y_label=f"{title} ({unit})" if unit else title,
            )
        )

    return blocks
