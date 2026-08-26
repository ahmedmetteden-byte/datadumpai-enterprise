"""
Golden-baseline regression harness for report generation (Premium Report
Generation Upgrade, Step A onward).

No such fixture existed in the repo before this — this is the "generate
the same baseline report, compare it against the existing behavior" gate
the upgrade's phased plan calls for after every step. It runs
SpaReportGenerationService.generate() end-to-end against a fixed,
hand-verified evidence fixture with a fake LLM (tests/fixtures/fake_llm.py)
and asserts STRUCTURAL invariants — never exact prose text, which would
break on every prompt wording tweak. Bump expectations here only when a
step intentionally changes structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.report_data import ReportData
from services.project_service import ProjectService
from services.spa_report_generation_service import (
    TEMPLATE_AUDIENCE_PURPOSE,
    TEMPLATE_RECOMMENDATION_STYLE,
    TEMPLATE_SECTIONS,
    SpaReportGenerationService,
)
from services.usage_service import UsageService
from tests.fixtures.fake_llm import fake_openai_client

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "report_baseline" / "annual_statistical_market_report.md"
)

EXPECTED_SECTION_ORDER = [
    "## Executive Summary",
    "## Key Findings",
    "## Detailed Analysis",
    "## Risks & Issues",
    "## Opportunities",
    "## Strategic Recommendations",
    "## Conclusion",
]

CANNED_REPORT = "\n\n".join(
    [
        "## Executive Summary\nPremiums grew materially in 2024.",
        "## Key Findings\n### Premium growth accelerated\nDetail.\n**Confidence:** High — verified calculations.\n**Source:** annual_statistical_market_report.md",
        "## Detailed Analysis\nGrowth was broad-based.",
        "## Risks & Issues\nClaims growth outpaced premium growth in the final year.",
        "## Opportunities\nNone material beyond continued expansion.",
        "## Strategic Recommendations\n1. Monitor claims trend.",
        "## Conclusion\nMomentum should be sustained.",
    ]
)


def _fixture_sources() -> list[dict[str, str]]:
    return [
        {
            "filename": FIXTURE_PATH.name,
            "excerpt": FIXTURE_PATH.read_text(encoding="utf-8"),
        }
    ]


def _generate_with_fake_llm(
    project,
    *,
    monkeypatch,
    report_plan_enabled: bool | None = None,
    template_id: str = "executive_summary",
):
    if report_plan_enabled is not None:
        monkeypatch.setattr(
            "services.spa_report_generation_service.REPORT_PLAN_ENABLED",
            report_plan_enabled,
        )

    svc = SpaReportGenerationService()
    client, completions = fake_openai_client(CANNED_REPORT)
    svc._client = client
    monkeypatch.setattr(svc, "_gather_sources", lambda *a, **kw: _fixture_sources())

    captured: dict[str, ReportData] = {}

    from services import report_service as report_service_module

    original_save_report = report_service_module.ReportService.save_report

    def _spy_save_report(*args, **kwargs):
        if "report" in kwargs and isinstance(kwargs["report"], ReportData):
            captured["report"] = kwargs["report"]
        return original_save_report(*args, **kwargs)

    monkeypatch.setattr(report_service_module.ReportService, "save_report", _spy_save_report)

    record = svc.generate(
        workspace_id=project["id"],
        project=project,
        template_id=template_id,
        period_id="annual",
    )

    prompt = completions.calls[0]["messages"][1]["content"]
    return record, prompt, captured.get("report")


def test_baseline_report_has_expected_section_order(
    isolated_env, project_service: ProjectService, monkeypatch
):
    project = project_service.create_project("Baseline Regression Project")

    record, _prompt, _report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    positions = [record["content"].index(section) for section in EXPECTED_SECTION_ORDER]
    assert positions == sorted(positions), "Section order regressed"
    assert record["sourceDocuments"] == [FIXTURE_PATH.name]


def test_baseline_prompt_includes_verified_calculations_and_report_plan(
    isolated_env, project_service: ProjectService, monkeypatch
):
    project = project_service.create_project("Baseline Plan Project")

    _record, prompt, report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    assert "### Verified Calculations" in prompt
    assert "97.4%" in prompt  # Gross Premium total change, hand-verified

    assert "### Report Plan (internal" in prompt
    # Gross Premium (97.4%) must outrank Gross Claims (51.3%) in the plan.
    premium_index = prompt.index("Gross Premium: increase of 97.4%")
    claims_index = prompt.index("Gross Claims: increase of 51.3%")
    assert premium_index < claims_index
    assert "Gross Premium grew faster than Gross Claims" in prompt

    assert report is not None
    plan = report.metadata.get("report_plan")
    assert plan is not None
    assert plan["ranked_findings"][0]["label"] == "Gross Premium"
    assert plan["chart_requirements"][0]["metric_title"] == "Gross Premium"


def test_baseline_report_plan_kill_switch_restores_prior_prompt(
    isolated_env, project_service: ProjectService, monkeypatch
):
    project = project_service.create_project("Baseline Kill Switch Project")

    _record, prompt, report = _generate_with_fake_llm(
        project, monkeypatch=monkeypatch, report_plan_enabled=False
    )

    assert "### Report Plan (internal" not in prompt
    # Everything else Step 1 already relies on must be untouched.
    assert "### Verified Calculations" in prompt
    assert report is not None
    assert "report_plan" not in report.metadata
    assert "dashboard_selection" not in report.metadata


def test_baseline_dashboard_selection_is_computed_and_stored(
    isolated_env, project_service: ProjectService, monkeypatch
):
    project = project_service.create_project("Baseline Dashboard Project")

    _record, _prompt, report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    assert report is not None
    selection = report.metadata.get("dashboard_selection")
    assert selection is not None
    assert selection["kpis"][0]["label"] == "Gross Premium"
    assert selection["kpis"][0]["total_change_percent"] == 97.4
    assert len(selection["kpis"]) <= 4
    assert selection["chart_requirements"] == report.metadata["report_plan"]["chart_requirements"]


def test_baseline_metric_derived_chart_survives_markdown_round_trip_and_exports(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """Step D: a chart built from quantitative_analysis_service's
    calculated MetricSeries must round-trip through to_markdown() ->
    saved content -> report_data_from_markdown() with correct, non-generic
    axis labels intact, and produce a real chart image on export - proving
    the fix reaches actual saved/exported reports, not just apply_
    visualizations()'s in-memory return value."""

    from services.export_chart_blocks import get_export_chart_images
    from services.report_chart_export import is_chart_export_available
    from services.report_document import report_data_from_markdown

    project = project_service.create_project("Baseline Chart Round Trip Project")

    # Charts are only generated for analytical report types on a plan that
    # includes "Professional charts & trend analysis" (see
    # ANALYTICAL_TEMPLATE_IDS / PlanService.include_professional_charts in
    # spa_report_generation_service.py) — this test is about chart
    # persistence round-tripping, not plan gating, so it needs a plan and
    # template that actually produce charts.
    UsageService().set_plan("professional")
    record, _prompt, _report = _generate_with_fake_llm(
        project, monkeypatch=monkeypatch, template_id="financial_analysis"
    )

    reconstructed = report_data_from_markdown(
        record["content"], report_type="Financial Analysis", title=record["name"]
    )
    visualizations = reconstructed.charts.get("visualizations") or []
    premium_blocks = [v for v in visualizations if v.get("title") == "Gross Premium"]

    assert premium_blocks, f"no Gross Premium chart block in {visualizations}"
    block = premium_blocks[0]
    assert block["type"] == "LINE_CHART"
    assert block["x_label"] == "Period"
    assert block["y_label"] not in ("Value", "y", "")
    # Phase 3 Step 3: LINE_CHART data is now one continuous point per row
    # (not "Previous vs Current" pairs, which silently dropped the first
    # period's own label for any 3+-row series) — every period must be
    # its own x-axis position, with the correct value attached to it.
    points = block["data"]["points"]
    assert points[-1]["value"] == 1558.7
    assert len(points) >= 3
    assert len({p["label"] for p in points}) == len(points)

    is_chart_export_available.cache_clear()
    if is_chart_export_available():
        chart_export = get_export_chart_images(reconstructed.charts)
        assert chart_export.images
        assert chart_export.images[0][1].startswith(b"\x89PNG")


def test_starter_plan_gets_no_charts_on_analytical_report(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """"Professional charts & trend analysis" is a Professional+ pricing
    bullet — a Starter-plan account generating the same analytical report
    type (financial_analysis) must not get chart blocks, even though the
    report type itself (Financial Analysis) is available on Starter."""

    from services.report_document import report_data_from_markdown

    project = project_service.create_project("Starter No Charts Project")

    UsageService().set_plan("starter")
    record, _prompt, _report = _generate_with_fake_llm(
        project, monkeypatch=monkeypatch, template_id="financial_analysis"
    )

    reconstructed = report_data_from_markdown(
        record["content"], report_type="Financial Analysis", title=record["name"]
    )
    assert not (reconstructed.charts.get("visualizations") or [])


WRONG_DIRECTION_REPORT = "\n\n".join(
    [
        "## Executive Summary\nGross Premium decreased by 97.4% between 2022 and 2024.",
        "## Key Findings\n### Gross Premium fell sharply\nGross Premium decreased by 97.4% "
        "over the period.\n**Confidence:** High — verified calculations.\n**Source:** "
        "annual_statistical_market_report.md",
        "## Detailed Analysis\nGrowth was broad-based.",
        "## Risks & Issues\nClaims growth outpaced premium growth in the final year.",
        "## Opportunities\nNone material beyond continued expansion.",
        "## Strategic Recommendations\n1. Monitor claims trend.",
        "## Conclusion\nMomentum should be sustained.",
    ]
)


def test_generate_auto_corrects_a_direction_contradiction_before_saving(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """Phase C.1 end-to-end: generate() must not merely flag a direction
    contradiction in qc_report metadata — it must correct the narrative
    itself before the report is saved. Gross Premium's verified total
    change is a +97.4% INCREASE; the canned LLM output here wrongly says
    'decreased' twice (Executive Summary and Key Findings)."""

    project = project_service.create_project("Auto-Correction Project")

    svc = SpaReportGenerationService()
    client, _completions = fake_openai_client(WRONG_DIRECTION_REPORT)
    svc._client = client
    monkeypatch.setattr(svc, "_gather_sources", lambda *a, **kw: _fixture_sources())

    record = svc.generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="annual",
    )

    assert "increased by 97.4%" in record["content"]
    assert "decreased by 97.4%" not in record["content"]
    assert record["reportData"]["metadata"].get("narrative_auto_corrected") is True

    qc_report = record["reportData"]["metadata"].get("qc_report")
    if qc_report is not None:
        assert not any(
            issue["category"] == "direction_consistency" for issue in qc_report["issues"]
        )


def test_baseline_qc_pass_flags_uncited_figures_without_blocking_generation(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """Step F: the canned test report never cites the computed percentages
    verbatim, so the QC pass must flag numerical-consistency issues - but
    since those are medium severity, generation must still succeed and
    the report must still be saved."""

    project = project_service.create_project("Baseline QC Project")

    record, _prompt, report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    assert record is not None  # generation was not blocked
    assert report is not None
    qc_report = report.metadata.get("qc_report")
    assert qc_report is not None
    assert qc_report["passed"] is True  # only medium-severity issues
    assert any(issue["category"] == "numerical_consistency" for issue in qc_report["issues"])


def test_baseline_qc_pass_kill_switch_omits_qc_report(
    isolated_env, project_service: ProjectService, monkeypatch
):
    monkeypatch.setattr("services.report_qc_service.REPORT_QC_ENABLED", False)
    project = project_service.create_project("Baseline QC Disabled Project")

    _record, _prompt, report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    assert report is not None
    assert "qc_report" not in report.metadata


# --- Phase 3 Step 4, Phase C: report types must be genuinely differentiated
# in what the writer prompt actually asks for — not just in the section
# headings the fake LLM happens to echo back. These assert against the real
# prompt text sent to the model, for every report type. ---

_SECTION_MARKER_PHRASE = {
    "executive_summary": "a board member could read alone and understand the whole",
    "key_findings": "as sub-headings, drawing across the full set of documents",
    "detailed_analysis": "The narrative connective tissue between findings",
    "risks_issues": "Concrete risks or open problems surfaced by the evidence",
    "opportunities": "Positive openings, efficiencies, or strategic options",
    "strategic_recommendations": "A markdown numbered list of specific, actionable next steps",
    "conclusion": "closing the report and restating what should happen next",
}
_ALL_STRUCTURAL_SECTIONS = set(_SECTION_MARKER_PHRASE)


@pytest.mark.parametrize("template_id", sorted(TEMPLATE_SECTIONS))
def test_prompt_requests_exactly_this_templates_sections_and_no_others(
    isolated_env, project_service: ProjectService, monkeypatch, template_id
):
    project = project_service.create_project(f"Section Differentiation {template_id}")

    _record, prompt, _report = _generate_with_fake_llm(
        project, monkeypatch=monkeypatch, template_id=template_id
    )

    expected_sections = set(TEMPLATE_SECTIONS[template_id])
    for section_id, phrase in _SECTION_MARKER_PHRASE.items():
        if section_id in expected_sections:
            assert phrase in prompt, f"{template_id} is missing its {section_id} instructions"
        else:
            assert phrase not in prompt, f"{template_id} unexpectedly requests {section_id}"


@pytest.mark.parametrize("template_id", sorted(TEMPLATE_SECTIONS))
def test_prompt_includes_this_templates_audience_purpose_and_recommendation_style(
    isolated_env, project_service: ProjectService, monkeypatch, template_id
):
    """Structural section lists alone don't prove differentiation — the
    prompt must also tell the model WHO it's writing for and WHAT KIND of
    recommendation this report type calls for, per template_id."""

    project = project_service.create_project(f"Audience Differentiation {template_id}")

    _record, prompt, _report = _generate_with_fake_llm(
        project, monkeypatch=monkeypatch, template_id=template_id
    )

    assert TEMPLATE_AUDIENCE_PURPOSE[template_id].strip() in prompt
    assert TEMPLATE_RECOMMENDATION_STYLE[template_id].strip() in prompt

    # Every OTHER template's audience/recommendation text must be absent —
    # differentiation, not just presence of some guidance.
    for other_id in TEMPLATE_SECTIONS:
        if other_id == template_id:
            continue
        if TEMPLATE_AUDIENCE_PURPOSE[other_id] != TEMPLATE_AUDIENCE_PURPOSE[template_id]:
            assert TEMPLATE_AUDIENCE_PURPOSE[other_id].strip() not in prompt
        if TEMPLATE_RECOMMENDATION_STYLE[other_id] != TEMPLATE_RECOMMENDATION_STYLE[template_id]:
            assert TEMPLATE_RECOMMENDATION_STYLE[other_id].strip() not in prompt


def test_prompt_carries_the_shared_business_direction_polarity_requirement(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """The polarity/business-direction instruction is shared across every
    report type (it's about not inventing improved/deteriorated language),
    unlike the per-template audience/recommendation guidance above."""

    project = project_service.create_project("Polarity Requirement Project")

    _record, prompt, _report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    assert "'Business direction' line" in prompt
    assert "never as having improved, worsened" in prompt


def test_generate_persists_full_report_data_for_export_time_reuse(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """Phase C.1: the record generate() returns (and persists) must carry
    the full ReportData — metrics["tables"], charts, metadata["report_plan"]
    — under "reportData", not just the narrower SPA display fields. Without
    this, export_report() had nothing but bare markdown text to work with,
    silently losing deterministic chart/metric data at export time."""

    project = project_service.create_project("Export Persistence Project")

    record, _prompt, report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    assert "reportData" in record
    stored = record["reportData"]
    assert stored["metrics"]["tables"], "expected the deterministic metric tables to be persisted"
    assert stored["metrics"]["tables"][0]["title"] == "Gross Premium"
    assert stored["metadata"]["report_plan"]["ranked_findings"][0]["label"] == "Gross Premium"

    # And a fresh reconstruction from that stored payload must round-trip
    # the metrics — this is exactly what export_report() now does.
    from models.report_data import ReportData
    from services.report_document import report_data_from_markdown

    reloaded = report_data_from_markdown(
        record["content"],
        report_type=record["reportType"],
        title=record["name"],
        source_documents=record["sourceDocuments"],
        stored=ReportData.from_dict(stored),
    )
    assert reloaded.metrics.get("tables"), "metrics must survive the export-time reload"
    assert reloaded.metrics["tables"][0]["title"] == "Gross Premium"
