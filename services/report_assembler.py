"""
Assemble AI narrative output with canonical structured report data.
"""

from __future__ import annotations

import json

from models.report_data import ReportData
from services.report_chart_data import strip_chart_data


def format_chart_block(chart_data: dict) -> str:
    return f"<!-- REPORT_CHARTS\n{json.dumps(chart_data, indent=2, sort_keys=True)}\n-->"


def canonical_metrics_prompt(
    report_data: ReportData,
    *,
    include_theme_metrics: bool = True,
) -> str:
    """Prompt section that binds the LLM to canonical quantitative values."""

    charts = dict(report_data.charts)
    metrics = dict(report_data.metrics)

    if not include_theme_metrics:
        charts.pop("topics", None)
        charts.pop("trends", None)
        metrics.pop("theme_totals", None)
        metrics.pop("top_themes", None)

    payload = {
        "metrics": metrics,
        "kpis": report_data.kpis,
        "charts": charts,
    }

    theme_guidance = (
        "Use these exact figures when citing counts, percentages, health score, or theme frequency."
        if include_theme_metrics
        else "Use these exact figures when citing counts, percentages, or health score. Do not create theme frequency sections."
    )

    return f"""
CANONICAL REPORT METRICS (authoritative — do not change these values)
The application renders charts and quantitative tables from this data.
{theme_guidance}
Never invent, estimate, or output a REPORT_CHARTS block.

```json
{json.dumps(payload, indent=2, sort_keys=True)}
```
"""


def assemble_report_text(
    narrative: str,
    report_data: ReportData,
    *,
    include_charts: bool,
) -> str:
    """Strip any LLM chart metadata and attach canonical chart data."""

    body = strip_chart_data(narrative).strip()

    if not include_charts or not report_data.charts:
        return body

    return f"{body}\n\n{format_chart_block(report_data.charts)}"
