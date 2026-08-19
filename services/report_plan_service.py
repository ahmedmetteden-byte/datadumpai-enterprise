"""
Deterministic report-planning layer.

Ranks findings by materiality, surfaces simple metric-vs-metric
relationships, and decides which metrics deserve a chart — entirely in
Python from quantitative_analysis_service.py's already-computed
MetricSeries output. No LLM call: evidence-derived ranking must be
reproducible and testable, not "LLM-felt". The resulting ReportPlan is
threaded into the report-writing prompt so the model prioritizes findings
the same way this layer already did, instead of re-deciding from scratch.

Only temporal metrics (those with a computed total_change) participate in
ranking/relationships today — categorical (non-temporal) tables like a
market-share breakdown have no percent-change magnitude to rank by. That's
a deliberate first-pass scope limit, not an oversight.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

REPORT_PLAN_ENABLED = os.getenv("REPORT_PLAN_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}

MAX_RANKED_FINDINGS = 8
MAX_CHART_REQUIREMENTS = 3
_MIN_RELATIONSHIP_GAP_POINTS = 1.0


@dataclass
class RankedFinding:
    label: str
    materiality_score: float
    direction: str  # "increase" | "decrease" | "flat"
    metric_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "materiality_score": self.materiality_score,
            "direction": self.direction,
            "metric_ref": self.metric_ref,
        }


@dataclass
class ChartRequirement:
    strategy: str  # a VisualizationStrategy value, e.g. "LINE_CHART"
    metric_title: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "metric_title": self.metric_title,
            "reason": self.reason,
        }


@dataclass
class ReportPlan:
    ranked_findings: list[RankedFinding] = field(default_factory=list)
    key_relationships: list[str] = field(default_factory=list)
    emphasis_sections: list[str] = field(default_factory=list)
    chart_requirements: list[ChartRequirement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked_findings": [f.to_dict() for f in self.ranked_findings],
            "key_relationships": list(self.key_relationships),
            "emphasis_sections": list(self.emphasis_sections),
            "chart_requirements": [c.to_dict() for c in self.chart_requirements],
        }

    def is_empty(self) -> bool:
        return not (self.ranked_findings or self.key_relationships or self.chart_requirements)


def _materiality_from_calculations(calculations: dict[str, Any]) -> tuple[float, str] | None:
    """Materiality = magnitude of total percent change. Returns None for a
    non-temporal series (no total_change was computed) — such a series
    simply doesn't participate in ranking, it isn't dropped from the
    report itself."""

    total = (calculations or {}).get("total_change")
    if not total or total.get("percent") is None:
        return None

    percent = float(total["percent"])
    direction = "increase" if percent > 0 else "decrease" if percent < 0 else "flat"
    return abs(percent), direction


def _rank_findings(metric_tables: list[dict[str, Any]]) -> list[RankedFinding]:
    findings: list[RankedFinding] = []

    for table in metric_tables:
        result = _materiality_from_calculations(table.get("calculations") or {})
        if result is None:
            continue

        magnitude, direction = result
        title = str(table.get("title") or "")
        findings.append(
            RankedFinding(
                label=title,
                materiality_score=round(magnitude, 1),
                direction=direction,
                metric_ref=title or None,
            )
        )

    findings.sort(key=lambda finding: finding.materiality_score, reverse=True)
    return findings[:MAX_RANKED_FINDINGS]


def _find_key_relationships(metric_tables: list[dict[str, Any]]) -> list[str]:
    """Simple percent-vs-percent comparisons between pairs of temporal
    metrics (e.g. "Gross Claims grew faster than Gross Premium (50.9% vs
    49.4%)"). Deliberately NOT a ratio/share calculation between metrics
    (e.g. a claims-to-premium ratio) — that's a distinct, deferred
    capability; this only compares two already-computed growth rates."""

    temporal: list[tuple[str, float]] = []
    for table in metric_tables:
        result = _materiality_from_calculations(table.get("calculations") or {})
        if result is None:
            continue
        title = str(table.get("title") or "")
        if not title:
            continue
        percent = float(table["calculations"]["total_change"]["percent"])
        temporal.append((title, percent))

    relationships: list[str] = []
    for i in range(len(temporal)):
        for j in range(i + 1, len(temporal)):
            label_a, percent_a = temporal[i]
            label_b, percent_b = temporal[j]
            gap = abs(percent_a - percent_b)
            if gap < _MIN_RELATIONSHIP_GAP_POINTS:
                continue  # not materially different — don't manufacture a relationship

            if percent_a > percent_b:
                faster, faster_pct, slower, slower_pct = label_a, percent_a, label_b, percent_b
            else:
                faster, faster_pct, slower, slower_pct = label_b, percent_b, label_a, percent_a

            relationships.append(
                f"{faster} grew faster than {slower} ({faster_pct:+.1f}% vs {slower_pct:+.1f}%)."
            )

    return relationships


def _chart_requirements(
    metric_tables: list[dict[str, Any]], ranked_findings: list[RankedFinding]
) -> list[ChartRequirement]:
    """Charts are only requested for metrics the deterministic ranking
    already decided matter most — never "because numbers exist" — capped
    at MAX_CHART_REQUIREMENTS per the "1-3 genuinely useful charts" bar."""

    by_title = {str(table.get("title") or ""): table for table in metric_tables}
    requirements: list[ChartRequirement] = []

    for finding in ranked_findings:
        table = by_title.get(finding.label)
        if not table:
            continue

        is_temporal = bool((table.get("calculations") or {}).get("period_over_period"))
        strategy = "LINE_CHART" if is_temporal else "BAR_CHART"
        requirements.append(
            ChartRequirement(
                strategy=strategy,
                metric_title=finding.label,
                reason=(
                    f"{finding.label} is among the most material findings in this report "
                    "(largest computed change)."
                ),
            )
        )
        if len(requirements) >= MAX_CHART_REQUIREMENTS:
            break

    return requirements


def build_report_plan(
    *,
    metric_tables: list[dict[str, Any]] | None = None,
    sources: list[dict[str, str]] | None = None,
    template_name: str = "",
    period_name: str = "",
) -> ReportPlan:
    """Deterministic report-planning stage — see module docstring.

    `sources`/`template_name`/`period_name` are accepted for future
    extension (e.g. source-relevance scoring) but unused today; keeping
    them in the signature now means the call site in generate() won't need
    to change shape as the plan grows.
    """

    tables = metric_tables or []
    ranked = _rank_findings(tables)

    return ReportPlan(
        ranked_findings=ranked,
        key_relationships=_find_key_relationships(tables),
        emphasis_sections=[],
        chart_requirements=_chart_requirements(tables, ranked),
    )


def render_plan_for_prompt(plan: ReportPlan) -> str:
    """Render the plan as a short internal evidence block for the report-
    writing prompt — same pattern as quantitative_analysis_service's
    format_metrics_for_evidence(): a clearly-labeled block the model is
    told to use, not repeat verbatim."""

    if plan.is_empty():
        return ""

    lines = [
        "\n\n### Report Plan (internal — use this to decide what matters "
        "most; do not repeat this block verbatim in the report)\n",
    ]

    if plan.ranked_findings:
        lines.append("Findings ranked by materiality (most important first):")
        for finding in plan.ranked_findings:
            lines.append(
                f"- {finding.label}: {finding.direction} of {finding.materiality_score}% "
                "— prioritize this in Key Findings and weigh it for the Executive Summary."
            )
        lines.append("")

    if plan.key_relationships:
        lines.append("Relationships between metrics worth noting if evidence supports it:")
        for relationship in plan.key_relationships:
            lines.append(f"- {relationship}")
        lines.append("")

    if plan.chart_requirements:
        lines.append(
            "Charts the evidence supports (do not claim any other chart exists — "
            "charts are rendered separately from this narrative):"
        )
        for chart in plan.chart_requirements:
            lines.append(f"- {chart.metric_title} ({chart.strategy}): {chart.reason}")

    return "\n".join(lines).rstrip() + "\n"
