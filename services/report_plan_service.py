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

from services.quantitative_analysis_service import classify_metric_polarity

REPORT_PLAN_ENABLED = os.getenv("REPORT_PLAN_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}

MAX_RANKED_FINDINGS = 8
MAX_CHART_REQUIREMENTS = 3
_MIN_RELATIONSHIP_GAP_POINTS = 1.0

# Report-type-aware materiality weighting: which polarity a template cares
# about most gets a ranking boost, so e.g. a Risk Assessment leads with its
# worst-pressure findings even when a larger-magnitude but unrelated
# positive metric exists elsewhere in the same evidence. This is a ranking
# *weight*, not a filter — every finding still competes on its own
# magnitude, so a template never hides a metric outside its focus, it just
# doesn't get to crowd out what the report type exists to surface.
_POLARITY_EMPHASIS_BOOST = 1.5
TEMPLATE_POLARITY_EMPHASIS: dict[str, str] = {
    "risk_assessment": "negative",
    "financial_analysis": "positive",
}

# Which findings-derived section each template asks the writer to foreground.
# Rendered into the prompt as guidance, not a hard requirement — the model
# still writes what the evidence supports.
TEMPLATE_EMPHASIS_SECTIONS: dict[str, list[str]] = {
    "executive_summary": ["key_findings"],
    "board_report": ["risks_issues", "strategic_recommendations"],
    "management_report": ["detailed_analysis", "strategic_recommendations"],
    "financial_analysis": ["detailed_analysis"],
    "risk_assessment": ["risks_issues"],
    "full_report": [],
}


@dataclass
class RankedFinding:
    label: str
    materiality_score: float
    direction: str  # "increase" | "decrease" | "flat"
    metric_ref: str | None = None
    kind: str = "temporal"  # "temporal" | "categorical" — Phase 3 Step 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "materiality_score": self.materiality_score,
            "direction": self.direction,
            "metric_ref": self.metric_ref,
            "kind": self.kind,
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
        return not (
            self.ranked_findings
            or self.key_relationships
            or self.chart_requirements
            or self.emphasis_sections
        )


def _materiality_from_calculations(calculations: dict[str, Any]) -> tuple[float, str] | None:
    """Materiality = magnitude of total percent change. Returns None for a
    non-temporal series (no total_change was computed) — such a series
    simply doesn't participate in growth-rate relationship comparisons
    (_find_key_relationships below), which are meaningless for a
    categorical spread. Kept temporal-only deliberately — see
    _ranking_score for the broader function used for materiality
    ranking/chart selection, which does cover categorical findings."""

    total = (calculations or {}).get("total_change")
    if not total or total.get("percent") is None:
        return None

    percent = float(total["percent"])
    direction = "increase" if percent > 0 else "decrease" if percent < 0 else "flat"
    return abs(percent), direction


def _ranking_score(calculations: dict[str, Any]) -> tuple[float, str, str] | None:
    """(magnitude, direction, kind) for materiality ranking / chart
    selection — covers BOTH a temporal total-change magnitude and a
    categorical cross-sectional gap magnitude (Phase 3 Step 2), so a wide
    cross-sectional spread ("Digital has the highest Premium Share at
    38%, Partners the lowest at 7%") can compete fairly for Key
    Findings/chart placement alongside a genuine temporal change — never
    conflated with one, since `kind` stays "categorical" throughout and a
    categorical finding's `direction` is always "flat" (no time-based
    increase/decrease is implied)."""

    total = (calculations or {}).get("total_change")
    if total and total.get("percent") is not None:
        percent = float(total["percent"])
        direction = "increase" if percent > 0 else "decrease" if percent < 0 else "flat"
        return abs(percent), direction, "temporal"

    cross_sectional = (calculations or {}).get("cross_sectional")
    if cross_sectional and cross_sectional.get("gap_percent") is not None:
        return abs(float(cross_sectional["gap_percent"])), "flat", "categorical"

    return None


def _emphasis_weight(table: dict[str, Any], template_id: str) -> float:
    """A ranking-only boost for findings matching the polarity a report
    type cares about most — never changes a finding's displayed
    materiality_score, only where it lands in sort order (and therefore
    whether it's ranked highly enough to win a chart slot)."""

    target_polarity = TEMPLATE_POLARITY_EMPHASIS.get(template_id)
    if not target_polarity:
        return 1.0

    title = str(table.get("title") or "")
    dimension_type = str(table.get("dimension_type") or "temporal")
    polarity = classify_metric_polarity(title, dimension_type=dimension_type)
    return _POLARITY_EMPHASIS_BOOST if polarity == target_polarity else 1.0


def _rank_findings(
    metric_tables: list[dict[str, Any]], *, template_id: str = ""
) -> list[RankedFinding]:
    weighted: list[tuple[float, RankedFinding]] = []

    for table in metric_tables:
        result = _ranking_score(table.get("calculations") or {})
        if result is None:
            continue

        magnitude, direction, kind = result
        title = str(table.get("title") or "")
        weight = _emphasis_weight(table, template_id)
        weighted.append(
            (
                magnitude * weight,
                RankedFinding(
                    label=title,
                    materiality_score=round(magnitude, 1),
                    direction=direction,
                    metric_ref=title or None,
                    kind=kind,
                ),
            )
        )

    weighted.sort(key=lambda item: item[0], reverse=True)
    return [finding for _, finding in weighted[:MAX_RANKED_FINDINGS]]


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
        if finding.kind == "categorical":
            reason = (
                f"{finding.label} shows the widest spread across categories in this report "
                "(largest computed cross-sectional gap)."
            )
        else:
            reason = (
                f"{finding.label} is among the most material findings in this report "
                "(largest computed change)."
            )
        requirements.append(
            ChartRequirement(
                strategy=strategy,
                metric_title=finding.label,
                reason=reason,
            )
        )
        if len(requirements) >= MAX_CHART_REQUIREMENTS:
            break

    return requirements


def build_report_plan(
    *,
    metric_tables: list[dict[str, Any]] | None = None,
    sources: list[dict[str, str]] | None = None,
    template_id: str = "",
    template_name: str = "",
    period_name: str = "",
) -> ReportPlan:
    """Deterministic report-planning stage — see module docstring.

    `template_id` drives two report-type-aware behaviors: a materiality
    ranking boost via TEMPLATE_POLARITY_EMPHASIS (e.g. Risk Assessment
    ranks negative-pressure findings higher, so it leads with and charts
    its worst pressure points even when a larger positive metric exists
    elsewhere) and the `emphasis_sections` hint via
    TEMPLATE_EMPHASIS_SECTIONS, rendered into the prompt so the writer
    knows which section this report type exists to foreground. Neither
    ever hides or fabricates a finding — only where it lands in ranking.

    `sources`/`period_name` are accepted for future extension (e.g.
    source-relevance scoring) but unused today; keeping them in the
    signature now means the call site in generate() won't need to change
    shape as the plan grows.
    """

    tables = metric_tables or []
    ranked = _rank_findings(tables, template_id=template_id)

    return ReportPlan(
        ranked_findings=ranked,
        key_relationships=_find_key_relationships(tables),
        emphasis_sections=list(TEMPLATE_EMPHASIS_SECTIONS.get(template_id, [])),
        chart_requirements=_chart_requirements(tables, ranked),
    )


MAX_DASHBOARD_KPIS = 4


@dataclass
class DashboardKPI:
    label: str
    value: float
    unit: str
    total_change_percent: float | None = None
    direction: str = "flat"  # "increase" | "decrease" | "flat"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "total_change_percent": self.total_change_percent,
            "direction": self.direction,
        }


@dataclass
class DashboardSelection:
    kpis: list[DashboardKPI] = field(default_factory=list)
    chart_requirements: list[ChartRequirement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kpis": [kpi.to_dict() for kpi in self.kpis],
            "chart_requirements": [c.to_dict() for c in self.chart_requirements],
        }

    def is_empty(self) -> bool:
        return not (self.kpis or self.chart_requirements)


def _latest_row_value(table: dict[str, Any]) -> float | None:
    rows = table.get("rows") or []
    if not rows:
        return None
    try:
        return float(rows[-1]["value"])
    except (KeyError, TypeError, ValueError):
        return None


def select_dashboard_items(
    plan: ReportPlan, metric_tables: list[dict[str, Any]]
) -> DashboardSelection:
    """Deterministically choose which metrics belong on the executive
    dashboard: the materiality-ranked temporal findings first (already
    computed by build_report_plan, in ranked order), then any remaining
    categorical (non-temporal) metrics to round out the picture — e.g. a
    market-share breakdown alongside growth KPIs — up to
    MAX_DASHBOARD_KPIS total. Chart selection reuses the plan's
    already-capped chart_requirements unchanged; this only adds KPI-card
    selection on top, for a real Step D chart-rendering pipeline to
    consume — see the Premium Report Generation Upgrade plan's Step D."""

    tables = metric_tables or []
    by_title = {str(table.get("title") or ""): table for table in tables}
    kpis: list[DashboardKPI] = []
    used_titles: set[str] = set()

    for finding in plan.ranked_findings:
        if len(kpis) >= MAX_DASHBOARD_KPIS:
            break
        table = by_title.get(finding.label)
        if not table:
            continue
        value = _latest_row_value(table)
        if value is None:
            continue
        total = (table.get("calculations") or {}).get("total_change") or {}
        kpis.append(
            DashboardKPI(
                label=finding.label,
                value=value,
                unit=str(table.get("unit") or ""),
                total_change_percent=total.get("percent"),
                direction=finding.direction,
            )
        )
        used_titles.add(finding.label)

    for table in tables:
        if len(kpis) >= MAX_DASHBOARD_KPIS:
            break
        title = str(table.get("title") or "")
        # A table with a computed total_change is temporal and is only
        # ever added via ranked_findings above. A categorical table now
        # always carries SOME calculations (cross-sectional stats, Phase
        # 3 Step 2) — checking for total_change specifically (rather than
        # "calculations is non-empty") is what still lets a categorical
        # table land in this "round out the picture" pass when it wasn't
        # already added via ranked_findings.
        if not title or title in used_titles or (table.get("calculations") or {}).get("total_change"):
            continue

        value = _latest_row_value(table)
        if value is None:
            continue
        kpis.append(
            DashboardKPI(label=title, value=value, unit=str(table.get("unit") or ""))
        )
        used_titles.add(title)

    return DashboardSelection(kpis=kpis, chart_requirements=list(plan.chart_requirements))


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

    if plan.emphasis_sections:
        section_labels = ", ".join(plan.emphasis_sections)
        lines.append(
            f"This report type should give the most weight to: {section_labels}. "
            "Still write every section the evidence supports — this only guides which "
            "section carries the report's main analytical weight.\n"
        )

    if plan.ranked_findings:
        lines.append("Findings ranked by materiality (most important first):")
        for finding in plan.ranked_findings:
            if finding.kind == "categorical":
                lines.append(
                    f"- {finding.label}: a {finding.materiality_score}% gap across categories "
                    "(highest vs. lowest) — this is a cross-sectional comparison, not a change "
                    "over time; describe which category is highest/lowest, never as an "
                    "increase/decrease."
                )
            else:
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
