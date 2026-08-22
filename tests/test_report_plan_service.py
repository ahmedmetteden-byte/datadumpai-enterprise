"""
Tests for the deterministic report-planning layer (Step A of the Premium
Report Generation Upgrade): materiality ranking, metric-vs-metric
relationships, and chart selection — all computed from already-calculated
quantitative_analysis_service output, with no LLM call.
"""

from __future__ import annotations

from services.report_plan_service import (
    ChartRequirement,
    DashboardKPI,
    RankedFinding,
    ReportPlan,
    _chart_requirements,
    build_report_plan,
    render_plan_for_prompt,
    select_dashboard_items,
)

PREMIUM_TABLE = {
    "title": "Gross Premium",
    "source_document": "report.pdf",
    "unit": "₦ billion",
    "rows": [
        {"label": "2022", "value": 789.6},
        {"label": "2023", "value": 1043.1},
        {"label": "2024", "value": 1558.7},
    ],
    "calculations": {
        "period_over_period": [
            {"from": "2022", "to": "2023", "absolute": 253.5, "percent": 32.1},
            {"from": "2023", "to": "2024", "absolute": 515.6, "percent": 49.4},
        ],
        "total_change": {"from": "2022", "to": "2024", "absolute": 769.1, "percent": 97.4},
    },
}

CLAIMS_TABLE = {
    "title": "Gross Claims",
    "source_document": "report.pdf",
    "unit": "₦ billion",
    "rows": [
        {"label": "2022", "value": 420.0},
        {"label": "2023", "value": 421.0},
        {"label": "2024", "value": 635.5},
    ],
    "calculations": {
        "period_over_period": [
            {"from": "2022", "to": "2023", "absolute": 1.0, "percent": 0.2},
            {"from": "2023", "to": "2024", "absolute": 214.5, "percent": 50.9},
        ],
        "total_change": {"from": "2022", "to": "2024", "absolute": 215.5, "percent": 51.3},
    },
}

MARKET_SHARE_TABLE = {
    "title": "Segment Market Share",
    "source_document": "report.pdf",
    "unit": "%",
    "rows": [
        {"label": "Life", "value": 32.0},
        {"label": "Non-Life", "value": 68.0},
    ],
    "calculations": {},
}


def test_build_report_plan_is_empty_for_no_metric_tables():
    plan = build_report_plan(metric_tables=[])
    assert plan.is_empty()
    assert render_plan_for_prompt(plan) == ""


def test_ranks_findings_by_materiality_descending():
    plan = build_report_plan(metric_tables=[CLAIMS_TABLE, PREMIUM_TABLE])

    labels = [f.label for f in plan.ranked_findings]
    assert labels == ["Gross Premium", "Gross Claims"]
    assert plan.ranked_findings[0].materiality_score == 97.4
    assert plan.ranked_findings[0].direction == "increase"
    assert plan.ranked_findings[0].metric_ref == "Gross Premium"


def test_categorical_table_with_no_computed_stats_is_excluded_from_ranking():
    """MARKET_SHARE_TABLE's calculations dict is hand-crafted empty here
    (no cross_sectional key) — a categorical table only participates in
    ranking once it actually carries computed cross-sectional stats (see
    test_categorical_table_with_cross_sectional_stats_is_ranked below);
    an empty calculations dict simply has nothing to rank on."""

    plan = build_report_plan(metric_tables=[MARKET_SHARE_TABLE, PREMIUM_TABLE])

    labels = [f.label for f in plan.ranked_findings]
    assert labels == ["Gross Premium"]


def test_categorical_table_with_cross_sectional_stats_is_ranked():
    """Phase 3 Step 2: a categorical table WITH real cross-sectional stats
    (as produced by quantitative_analysis_service's
    _compute_cross_sectional_stats) now participates in ranking via its
    gap magnitude — closing the gap the previous test's sibling used to
    flag as "the public API can't reach it yet"."""

    channel_table = {
        "title": "Premium Share (%)",
        "source_document": "report.pdf",
        "unit": "%",
        "rows": [
            {"label": "Digital", "value": 38.0},
            {"label": "Partners", "value": 7.0},
        ],
        "calculations": {
            "cross_sectional": {
                "highest": {"label": "Digital", "value": 38.0},
                "lowest": {"label": "Partners", "value": 7.0},
                "range": 31.0,
                "gap_percent": 81.6,
            }
        },
    }
    plan = build_report_plan(metric_tables=[channel_table, PREMIUM_TABLE])

    finding = next(f for f in plan.ranked_findings if f.label == "Premium Share (%)")
    assert finding.materiality_score == 81.6
    assert finding.direction == "flat"
    assert finding.kind == "categorical"

    assert len(plan.chart_requirements) >= 1
    chart = next(c for c in plan.chart_requirements if c.metric_title == "Premium Share (%)")
    assert chart.strategy == "BAR_CHART"
    assert "cross-sectional gap" in chart.reason

    block = render_plan_for_prompt(plan)
    assert "cross-sectional comparison, not a change over time" in block


def test_caps_ranked_findings_at_max():
    tables = [
        {**PREMIUM_TABLE, "title": f"Metric {i}",
         "calculations": {"total_change": {"percent": float(i)}}}
        for i in range(1, 12)
    ]
    plan = build_report_plan(metric_tables=tables)
    assert len(plan.ranked_findings) == 8


def test_finds_key_relationship_between_two_metrics_with_a_real_gap():
    plan = build_report_plan(metric_tables=[PREMIUM_TABLE, CLAIMS_TABLE])

    assert len(plan.key_relationships) == 1
    relationship = plan.key_relationships[0]
    assert "Gross Premium grew faster than Gross Claims" in relationship
    assert "+97.4%" in relationship
    assert "+51.3%" in relationship


def test_no_relationship_manufactured_when_gap_is_negligible():
    almost_identical = {
        **CLAIMS_TABLE,
        "title": "Almost Identical",
        "calculations": {
            "period_over_period": [],
            "total_change": {"percent": 97.9},
        },
    }
    plan = build_report_plan(metric_tables=[PREMIUM_TABLE, almost_identical])
    assert plan.key_relationships == []


def test_chart_requirements_follow_ranked_findings_and_are_capped():
    tables = [
        {**PREMIUM_TABLE, "title": f"Metric {i}",
         "calculations": {
             "period_over_period": [{"percent": float(i)}],
             "total_change": {"percent": float(100 - i)},
         }}
        for i in range(1, 6)
    ]
    plan = build_report_plan(metric_tables=tables)

    assert len(plan.chart_requirements) == 3
    assert all(c.strategy == "LINE_CHART" for c in plan.chart_requirements)
    # Highest materiality (smallest i, since percent = 100 - i) charted first.
    assert plan.chart_requirements[0].metric_title == "Metric 1"


def test_chart_requirements_use_bar_chart_for_categorical_ranked_findings():
    """_chart_requirements() must choose BAR_CHART for a non-temporal
    metric's ranked finding — exercised directly here against a
    hand-built RankedFinding; see
    test_categorical_table_with_cross_sectional_stats_is_ranked for the
    full build_report_plan() path that now reaches this branch too."""

    ranked = [RankedFinding(label="Segment Market Share", materiality_score=10, direction="increase")]
    requirements = _chart_requirements([MARKET_SHARE_TABLE], ranked)

    assert len(requirements) == 1
    assert requirements[0].strategy == "BAR_CHART"
    assert requirements[0].metric_title == "Segment Market Share"


def test_render_plan_for_prompt_includes_all_sections_and_marks_internal():
    plan = ReportPlan(
        ranked_findings=[
            RankedFinding(label="Gross Premium", materiality_score=97.4, direction="increase")
        ],
        key_relationships=["Gross Claims grew faster than Gross Premium (+51.3% vs +97.4%)."],
        chart_requirements=[
            ChartRequirement(strategy="LINE_CHART", metric_title="Gross Premium", reason="test reason")
        ],
    )

    block = render_plan_for_prompt(plan)

    assert "Report Plan (internal" in block
    assert "Gross Premium: increase of 97.4%" in block
    assert "Gross Claims grew faster than Gross Premium" in block
    assert "Gross Premium (LINE_CHART): test reason" in block


def test_report_plan_to_dict_round_trips_all_fields():
    plan = build_report_plan(metric_tables=[PREMIUM_TABLE, CLAIMS_TABLE])
    payload = plan.to_dict()

    assert set(payload.keys()) == {
        "ranked_findings",
        "key_relationships",
        "emphasis_sections",
        "chart_requirements",
    }
    assert payload["ranked_findings"][0]["label"] == "Gross Premium"
    assert payload["chart_requirements"][0]["strategy"] == "LINE_CHART"


def test_select_dashboard_items_prioritizes_ranked_temporal_findings():
    plan = build_report_plan(metric_tables=[CLAIMS_TABLE, PREMIUM_TABLE])
    selection = select_dashboard_items(plan, [CLAIMS_TABLE, PREMIUM_TABLE])

    labels = [kpi.label for kpi in selection.kpis]
    assert labels == ["Gross Premium", "Gross Claims"]
    assert selection.kpis[0].value == 1558.7
    assert selection.kpis[0].unit == "₦ billion"
    assert selection.kpis[0].total_change_percent == 97.4
    assert selection.kpis[0].direction == "increase"


def test_select_dashboard_items_fills_remaining_slots_with_categorical_metrics():
    plan = build_report_plan(metric_tables=[PREMIUM_TABLE, MARKET_SHARE_TABLE])
    selection = select_dashboard_items(plan, [PREMIUM_TABLE, MARKET_SHARE_TABLE])

    labels = [kpi.label for kpi in selection.kpis]
    assert labels == ["Gross Premium", "Segment Market Share"]
    share_kpi = selection.kpis[1]
    assert share_kpi.value == 68.0  # last row (Non-Life)
    assert share_kpi.total_change_percent is None
    assert share_kpi.direction == "flat"


def test_select_dashboard_items_caps_at_max_kpis():
    tables = [
        {**PREMIUM_TABLE, "title": f"Metric {i}",
         "calculations": {
             "period_over_period": [{"percent": float(i)}],
             "total_change": {"percent": float(100 - i)},
         }}
        for i in range(1, 8)
    ]
    plan = build_report_plan(metric_tables=tables)
    selection = select_dashboard_items(plan, tables)

    assert len(selection.kpis) == 4


def test_select_dashboard_items_reuses_plans_chart_requirements_unchanged():
    plan = build_report_plan(metric_tables=[PREMIUM_TABLE, CLAIMS_TABLE])
    selection = select_dashboard_items(plan, [PREMIUM_TABLE, CLAIMS_TABLE])

    assert selection.chart_requirements == plan.chart_requirements


def test_select_dashboard_items_empty_for_no_tables():
    plan = build_report_plan(metric_tables=[])
    selection = select_dashboard_items(plan, [])
    assert selection.is_empty()


def test_dashboard_kpi_to_dict_round_trips():
    kpi = DashboardKPI(
        label="Gross Premium", value=1558.7, unit="₦ billion",
        total_change_percent=97.4, direction="increase",
    )
    assert kpi.to_dict() == {
        "label": "Gross Premium",
        "value": 1558.7,
        "unit": "₦ billion",
        "total_change_percent": 97.4,
        "direction": "increase",
    }
