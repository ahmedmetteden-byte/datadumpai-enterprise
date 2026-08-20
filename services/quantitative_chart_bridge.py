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
    LINE_CHART: each adjacent row pair becomes one {label, prior, current}
    trend point, using the exact same pairing quantitative_analysis_service
    used to compute period_over_period — so the chart and the "Verified
    Calculations" evidence block can never disagree.

    Categorical (non-temporal) series become a BAR_CHART, one bar per row.

    Returns None for a series with fewer than 2 rows — nothing to chart.
    """

    rows = series.get("rows") or []
    if len(rows) < 2:
        return None

    is_temporal = bool((series.get("calculations") or {}).get("period_over_period"))

    if is_temporal:
        trends = [
            {
                "label": str(current.get("label", "")),
                "prior": prior.get("value"),
                "current": current.get("value"),
            }
            for prior, current in zip(rows, rows[1:])
        ]
        return {"type": "LINE_CHART", "data": {"trends": trends}}

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
