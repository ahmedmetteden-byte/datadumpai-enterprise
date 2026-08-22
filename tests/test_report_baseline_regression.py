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

from models.report_data import ReportData
from services.project_service import ProjectService
from services.spa_report_generation_service import SpaReportGenerationService
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
    project, *, monkeypatch, report_plan_enabled: bool | None = None
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
        template_id="executive_summary",
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

    record, _prompt, _report = _generate_with_fake_llm(project, monkeypatch=monkeypatch)

    reconstructed = report_data_from_markdown(
        record["content"], report_type="Executive Summary", title=record["name"]
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
