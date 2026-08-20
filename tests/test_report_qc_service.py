"""
Tests for the report quality-control pass (Step F of the Premium Report
Generation Upgrade). Every check here is deterministic Python; this file
does not exercise the optional LLM-assisted check (off by default).
"""

from __future__ import annotations

from services.report_qc_service import (
    QCIssue,
    _check_chart_consistency,
    _check_citation_consistency,
    _check_document_coverage,
    _check_duplicate_content,
    _check_evidence_leaks_into_narrative,
    _check_growth_terminology,
    _check_numerical_consistency,
    _check_period_correctness,
    _check_recommendation_has_action,
    _check_risk_opportunity_formatting,
    _split_sections,
    run_qc_pass,
)

PREMIUM_TABLE = {
    "title": "Gross Premium",
    "calculations": {
        "period_over_period": [
            {"from": "2022", "to": "2023", "percent": 32.1},
            {"from": "2023", "to": "2024", "percent": 49.4},
        ],
        "total_change": {"from": "2022", "to": "2024", "percent": 97.4},
    },
}


def test_split_sections_splits_by_h2_heading():
    narrative = "## Executive Summary\nA.\n\n## Key Findings\nB.\n"
    sections = _split_sections(narrative)
    assert sections == {"Executive Summary": "A.", "Key Findings": "B."}


def test_numerical_consistency_passes_when_all_figures_cited():
    narrative = "Premiums grew 97.4% overall, with 32.1% and 49.4% year-on-year."
    issues = _check_numerical_consistency(narrative, [PREMIUM_TABLE])
    assert issues == []


def test_numerical_consistency_flags_missing_figure():
    narrative = "Premiums grew significantly, roughly doubling."
    issues = _check_numerical_consistency(narrative, [PREMIUM_TABLE])
    assert len(issues) == 3  # total_change + 2 period_over_period figures, all missing
    assert all(issue.category == "numerical_consistency" for issue in issues)
    assert all(issue.severity == "medium" for issue in issues)


def test_citation_consistency_passes_for_known_sources():
    narrative = "**Source:** report.xlsx"
    issues = _check_citation_consistency(narrative, ["report.xlsx"])
    assert issues == []


def test_citation_consistency_flags_unknown_source():
    narrative = "**Source:** made_up_file.pdf"
    issues = _check_citation_consistency(narrative, ["report.xlsx"])
    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert issues[0].category == "citation_consistency"
    assert "made_up_file.pdf" in issues[0].message


def test_citation_consistency_handles_multiple_comma_separated_sources():
    narrative = "**Source:** report.xlsx, other.pdf"
    issues = _check_citation_consistency(narrative, ["report.xlsx"])
    assert len(issues) == 1
    assert "other.pdf" in issues[0].message


def test_chart_consistency_passes_when_requirement_has_matching_block():
    requirements = [{"metric_title": "Gross Premium"}]
    visualizations = [{"title": "Gross Premium"}]
    assert _check_chart_consistency(requirements, visualizations) == []


def test_chart_consistency_flags_missing_chart():
    requirements = [{"metric_title": "Gross Premium"}]
    issues = _check_chart_consistency(requirements, [])
    assert len(issues) == 1
    assert issues[0].category == "chart_consistency"
    assert issues[0].severity == "medium"


def test_period_correctness_passes_when_no_changes_section():
    assert _check_period_correctness("## Executive Summary\nText.", None, "custom") == []


def test_period_correctness_flags_missing_previous_report():
    narrative = "## Changes Since Last Report\nNothing changed."
    issues = _check_period_correctness(narrative, None, "custom")
    assert len(issues) == 1
    assert issues[0].severity == "high"


def test_period_correctness_flags_period_mismatch():
    narrative = "## Changes Since Last Report\nNothing changed."
    previous_report = {"periodId": "quarterly"}
    issues = _check_period_correctness(narrative, previous_report, "weekly")
    assert len(issues) == 1
    assert "quarterly" in issues[0].message
    assert "weekly" in issues[0].message


def test_period_correctness_passes_when_periods_match():
    narrative = "## Changes Since Last Report\nNothing changed."
    previous_report = {"periodId": "weekly"}
    assert _check_period_correctness(narrative, previous_report, "weekly") == []


def test_duplicate_content_flags_verbatim_sentence_reuse():
    narrative = (
        "## Executive Summary\n"
        "Gross written premiums increased from 789.6 billion in 2022 to 1558.7 billion in 2024.\n\n"
        "## Key Findings\n"
        "Gross written premiums increased from 789.6 billion in 2022 to 1558.7 billion in 2024."
    )
    issues = _check_duplicate_content(narrative)
    assert any(issue.category == "duplicate_content" and "Executive Summary" in issue.message for issue in issues)


def test_duplicate_content_flags_repeated_recommendation_action():
    narrative = (
        "## Strategic Recommendations\n"
        "1. **Action:** Monitor claims trends closely.\n"
        "2. **Action:** Monitor claims trends closely.\n"
    )
    issues = _check_duplicate_content(narrative)
    assert any("Duplicate recommendation action" in issue.message for issue in issues)


def test_duplicate_content_passes_for_distinct_content():
    narrative = (
        "## Executive Summary\nGross premiums increased materially in 2024.\n\n"
        "## Key Findings\nClaims growth outpaced premium growth in the final year.\n\n"
        "## Strategic Recommendations\n"
        "1. **Action:** Review claims processing.\n"
        "2. **Action:** Expand into adjacent markets.\n"
    )
    assert _check_duplicate_content(narrative) == []


def test_growth_terminology_flags_cagr_mention():
    """Report Output Quality Upgrade Step E: a real generated report
    called a single-period 2023-to-2024 year-over-year growth figure a
    'compounded annual growth rate' — this system never computes a CAGR
    (quantitative_analysis_service.py only computes period-over-period
    and total-change deltas), so any mention of it is unverified."""

    narrative = "Premiums grew, reflecting a compounded annual growth rate of approximately 49.4%."
    issues = _check_growth_terminology(narrative)
    assert len(issues) == 1
    assert issues[0].category == "growth_terminology"
    assert issues[0].severity == "medium"


def test_growth_terminology_flags_bare_cagr_acronym():
    issues = _check_growth_terminology("The CAGR over the period was strong.")
    assert len(issues) == 1


def test_growth_terminology_passes_for_correct_yoy_wording():
    narrative = "Premiums grew 49.4% year-over-year in 2024, following 32.1% growth in 2023."
    assert _check_growth_terminology(narrative) == []


def test_risk_opportunity_formatting_passes_for_bulleted_content():
    narrative = (
        "## Risks & Issues\n"
        "- **Rising Claims Costs:** The increase poses a risk to profitability.\n"
    )
    assert _check_risk_opportunity_formatting(narrative) == []


def test_risk_opportunity_formatting_passes_for_clean_negative_statement():
    narrative = "## Opportunities\nNo opportunities were identified in the evidence reviewed.\n"
    assert _check_risk_opportunity_formatting(narrative) == []


def test_risk_opportunity_formatting_flags_unstructured_prose():
    narrative = (
        "## Opportunities\n"
        "There are several opportunities for the business including product expansion "
        "and better claims handling and improved customer service overall.\n"
    )
    issues = _check_risk_opportunity_formatting(narrative)
    assert len(issues) == 1
    assert issues[0].category == "risk_opportunity_formatting"
    assert issues[0].severity == "low"


def test_recommendation_has_action_passes_when_every_item_has_one():
    narrative = (
        "## Strategic Recommendations\n"
        "1. **Action:** Review claims processing.\n"
        "   **Rationale:** Claims rose 51.3%.\n"
        "   **Measurement:** Track claims ratio.\n"
        "2. **Action:** Expand into adjacent markets.\n"
        "   **Rationale:** Premium growth outpaces claims.\n"
        "   **Measurement:** Track new segment revenue.\n"
    )
    assert _check_recommendation_has_action(narrative) == []


def test_recommendation_has_action_flags_missing_action_clause():
    narrative = (
        "## Strategic Recommendations\n"
        "1. **Rationale:** Claims rose 51.3%.\n"
        "   **Measurement:** Track claims ratio.\n"
    )
    issues = _check_recommendation_has_action(narrative)
    assert len(issues) == 1
    assert issues[0].category == "recommendation_structure"
    assert "Recommendation #1" in issues[0].message


def test_evidence_leak_passes_for_correctly_separated_tags():
    narrative = (
        "### Gross Premium increased 97.4%\n"
        "Detail text about the finding.\n"
        "**Basis:** Source fact\n"
        "**Confidence:** High\n"
        "**Source:** report.xlsx\n"
    )
    assert _check_evidence_leaks_into_narrative(narrative) == []


def test_evidence_leak_flags_tag_run_into_preceding_prose():
    narrative = (
        "### Gross Premium increased 97.4%\n"
        "Detail text about the finding. **Basis:** Source fact\n"
    )
    issues = _check_evidence_leaks_into_narrative(narrative)
    assert len(issues) == 1
    assert issues[0].category == "evidence_leak"
    assert issues[0].location == "Basis"


def test_document_coverage_ignores_reports_where_all_documents_wasnt_requested():
    assert _check_document_coverage(None) == []
    assert _check_document_coverage({"all_documents_requested": False}) == []
    assert _check_document_coverage({}) == []


def test_document_coverage_passes_when_every_document_covered():
    coverage = {
        "all_documents_requested": True,
        "documents_in_scope": 4,
        "documents_covered": 4,
        "gaps": [],
    }
    assert _check_document_coverage(coverage) == []


def test_document_coverage_flags_a_missing_document_as_high_severity():
    """Document Coverage fix: the exact real-world regression — 4
    documents requested, only 3 covered — must surface as a high-severity
    issue, not pass silently."""

    coverage = {
        "all_documents_requested": True,
        "documents_in_scope": 4,
        "documents_covered": 3,
        "gaps": [{"filename": "Minutes - 14th Meeting.pdf", "reason": "no_matching_evidence"}],
    }
    issues = _check_document_coverage(coverage)
    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert issues[0].category == "document_coverage"
    assert "Minutes - 14th Meeting.pdf" in issues[0].message
    assert "4" in issues[0].message and "3" in issues[0].message


def test_run_qc_pass_kill_switch_short_circuits(monkeypatch):
    monkeypatch.setattr("services.report_qc_service.REPORT_QC_ENABLED", False)
    report = run_qc_pass("anything", [], metric_tables=[PREMIUM_TABLE])
    assert report.passed is True
    assert report.issues == []


def test_run_qc_pass_fails_only_on_high_severity_issues():
    narrative = "## Executive Summary\nSome narrative with no cited figures."
    report = run_qc_pass(narrative, ["report.xlsx"], metric_tables=[PREMIUM_TABLE])
    # numerical_consistency issues are "medium" severity -> report still passes.
    assert report.passed is True
    assert len(report.issues) == 3


def test_run_qc_pass_fails_on_high_severity_citation_issue():
    narrative = "**Source:** nonexistent.pdf"
    report = run_qc_pass(narrative, ["report.xlsx"])
    assert report.passed is False
    assert any(issue.severity == "high" for issue in report.issues)


def test_run_qc_pass_skips_llm_check_when_disabled_even_with_client():
    calls = []

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    calls.append(kwargs)
                    raise AssertionError("should not be called when disabled")

    run_qc_pass("## Executive Summary\nText.", ["a.pdf"], llm_client=_Client())
    assert calls == []


def test_qc_issue_to_dict():
    issue = QCIssue(severity="high", category="citation_consistency", message="msg", location="loc")
    assert issue.to_dict() == {
        "severity": "high",
        "category": "citation_consistency",
        "message": "msg",
        "location": "loc",
    }
