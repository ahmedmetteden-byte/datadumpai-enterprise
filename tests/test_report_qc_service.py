"""
Tests for the report quality-control pass (Step F of the Premium Report
Generation Upgrade). Every check here is deterministic Python; this file
does not exercise the optional LLM-assisted check (off by default).
"""

from __future__ import annotations

from services.report_qc_service import (
    QCIssue,
    apply_deterministic_corrections,
    _check_chart_consistency,
    _check_citation_consistency,
    check_direction_consistency,
    _check_document_coverage,
    _check_duplicate_content,
    _check_endpoint_value_sentiment,
    _check_evidence_leaks_into_narrative,
    _check_growth_terminology,
    _check_no_generic_metric_titles,
    _check_no_implausible_ungrounded_percentages,
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


# --- Phase 3 Step 2: cross-sectional gap citation consistency ---


def test_numerical_consistency_flags_missing_cross_sectional_gap():
    """Real-pipeline testing showed the model can correctly frame a
    categorical comparison (never claiming a temporal change) while still
    inventing its own gap magnitude instead of citing the deterministic
    one — this check catches that the correct figure never appeared."""

    table = {
        "title": "Complaints",
        "calculations": {
            "cross_sectional": {
                "highest": {"label": "Digital", "value": 126.0},
                "lowest": {"label": "Partners", "value": 94.0},
                "range": 32.0,
                "gap_percent": 25.4,
            }
        },
    }
    narrative = "Digital has more complaints than Partners, a 58.2% difference."
    issues = _check_numerical_consistency(narrative, [table])
    assert len(issues) == 1
    assert "25.4%" in issues[0].message


def test_numerical_consistency_passes_when_cross_sectional_gap_cited():
    table = {
        "title": "Complaints",
        "calculations": {
            "cross_sectional": {
                "highest": {"label": "Digital", "value": 126.0},
                "lowest": {"label": "Partners", "value": 94.0},
                "range": 32.0,
                "gap_percent": 25.4,
            }
        },
    }
    narrative = "Digital has more complaints than Partners, a gap of 25.4%."
    assert _check_numerical_consistency(narrative, [table]) == []


# --- Phase 3 Step 3: proximity check — right number, wrong claim ---


def test_numerical_consistency_flags_a_figure_cited_for_the_wrong_metric():
    """Regression test motivated by the Risk Committee Score bug: the
    figure being present SOMEWHERE in the narrative isn't enough — if it
    never appears near any word distinctive to the metric it's supposed
    to belong to, it may have been cited for an entirely different
    metric that happens to round to the same value."""

    table = {
        "title": "Operational Resilience Score",
        "calculations": {"total_change": {"from": "2024", "to": "2025", "percent": 11.1}},
    }
    narrative = "The Overall Risk Score improved by 11.1%, a positive development."
    issues = _check_numerical_consistency(narrative, [table])
    assert len(issues) == 1
    assert "may be cited for a different metric" in issues[0].message


def test_numerical_consistency_passes_when_figure_cited_near_a_synonym_of_the_title():
    """Real narrative prose rarely repeats a metric's exact multi-word
    title verbatim ("Premiums grew 97.4%" rather than "Gross Premium grew
    97.4%") — the proximity check must tolerate this, matching on any
    single distinctive word from the title, not the full title string."""

    table = {
        "title": "Gross Premium",
        "calculations": {"total_change": {"from": "2023", "to": "2025", "percent": 97.4}},
    }
    narrative = "Premiums grew 97.4% overall, reflecting strong demand."
    assert _check_numerical_consistency(narrative, [table]) == []


def test_numerical_consistency_skips_proximity_check_for_an_all_generic_title():
    """A title made up entirely of generic/stopword terms (e.g. "Total
    Score") has no distinctive word to check against — skip rather than
    risk a false positive; the generic title itself is separately flagged
    by _check_no_generic_metric_titles."""

    table = {
        "title": "Total Score",
        "calculations": {"total_change": {"from": "2024", "to": "2025", "percent": 11.1}},
    }
    narrative = "Overall performance was 11.1% higher this period."
    assert _check_numerical_consistency(narrative, [table]) == []


# --- Phase 3 Step 4, Phase A: direction/sign consistency ---

CLAIMS_TABLE = {
    "title": "Claims incurred",
    "calculations": {
        "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 7.6, "percent": 9.3},
    },
}

LOSS_RATIO_TABLE = {
    "title": "Loss ratio",
    "calculations": {
        "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 0.3, "percent": 0.5},
        "period_over_period": [
            {"from": "February 2026", "to": "March 2026", "absolute": -3.9, "percent": -5.7},
        ],
    },
}


def test_direction_consistency_flags_decrease_word_against_a_positive_change():
    """The exact production bug: a report said claims 'decreased by 9.3%'
    while the verified total change was +9.3% (an increase)."""

    narrative = "Claims incurred decreased by 9.3% between January and March 2026."
    issues = check_direction_consistency(narrative, [CLAIMS_TABLE])

    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert issues[0].category == "direction_consistency"
    assert "decrease" in issues[0].message
    assert "increase" in issues[0].message


def test_direction_consistency_passes_when_increase_word_matches_positive_change():
    narrative = "Claims incurred increased by 9.3% between January and March 2026."
    assert check_direction_consistency(narrative, [CLAIMS_TABLE]) == []


def test_direction_consistency_flags_improved_against_a_worsening_loss_ratio():
    """The second production bug: a report said the loss ratio 'improved'
    while the verified January-to-March change was +0.3 percentage
    points (a deterioration for a lower-is-better ratio metric)."""

    narrative = "The loss ratio improved from January to March 2026, moving by 0.5%."
    issues = check_direction_consistency(narrative, [LOSS_RATIO_TABLE])

    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert "improved" in issues[0].message


def test_direction_consistency_passes_when_worsened_matches_a_genuine_deterioration():
    narrative = "The loss ratio worsened from January to March 2026, moving by 0.5%."
    assert check_direction_consistency(narrative, [LOSS_RATIO_TABLE]) == []


def test_direction_consistency_passes_when_improved_correctly_describes_a_real_improvement():
    """February-to-March really IS an improvement for the loss ratio
    (-3.9 percentage points) — must not be flagged just because the
    metric is on the lower-is-better list."""

    narrative = "The loss ratio improved by 5.7% from February to March 2026."
    assert check_direction_consistency(narrative, [LOSS_RATIO_TABLE]) == []


def test_direction_consistency_ignores_sentiment_words_for_non_ratio_metrics():
    """"Improved"/"worsened" checks are scoped to the explicit
    lower-is-better ratio keyword list — a non-ratio metric (e.g. gross
    premium) must never be flagged on sentiment wording alone."""

    table = {
        "title": "Gross premium",
        "calculations": {
            "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 11.2, "percent": 8.7}
        },
    }
    narrative = "Gross premium improved by 8.7% from January to March 2026."
    assert check_direction_consistency(narrative, [table]) == []


def test_direction_consistency_skips_figures_not_near_this_metrics_title():
    """A coincidentally-matching figure belonging to a different metric
    must not trigger a direction flag — that ambiguity is already
    _check_numerical_consistency's job, not this check's."""

    narrative = "Some unrelated total decreased by 9.3% due to seasonal effects."
    assert check_direction_consistency(narrative, [CLAIMS_TABLE]) == []


def test_direction_consistency_catches_endpoint_value_contradiction_with_no_percentage():
    """A direction contradiction stated via a metric's raw endpoint
    values, with no percentage figure anywhere for the percent-proximity
    pass to anchor to — check_direction_consistency must still catch it
    via the metric's own row values."""

    table = {
        "title": "Claims incurred",
        "rows": [{"label": "January 2026", "value": 82.1}, {"label": "March 2026", "value": 89.7}],
        "calculations": {},
    }
    narrative = "Claims incurred decreased from $82.1m in January to $89.7m in March 2026."
    issues = check_direction_consistency(narrative, [table])
    assert len(issues) == 1
    assert issues[0].severity == "high"


def test_direction_consistency_does_not_bleed_across_bullet_lines():
    """Phase 3 Step 4, Phase B real E2E regression: a bulleted answer
    listing several metrics, each on its own line, must never let one
    bullet's direction word "cover for" an adjacent, unrelated bullet's
    genuinely wrong direction word — found live when a claims-backlog
    contradiction ("decreased from 418 to 431", actually an increase)
    went undetected because "increased" from a NEIGHBORING bullet about
    a different metric fell inside the same character-radius window,
    tripping the both-directions-present ambiguity guard."""

    backlog_table = {
        "title": "Claims backlog",
        "rows": [
            {"label": "January 2026", "value": 418.0},
            {"label": "March 2026", "value": 431.0},
        ],
        "calculations": {"total_change": {"from": "January 2026", "to": "March 2026", "absolute": 13.0, "percent": 3.1}},
    }
    narrative = (
        "Between January and March 2026:\n\n"
        "- **Gross premium** increased from $128.4m to $139.6m.\n"
        "- **Claims incurred** increased from $82.1m to $89.7m.\n"
        "- **Claims backlog** decreased from 418 cases to 431 cases.\n"
        "- **Customer retention** increased from 84.2% to 85.1%.\n"
    )
    issues = check_direction_consistency(narrative, [backlog_table])
    assert len(issues) == 1
    assert "Claims backlog" in issues[0].message


def test_direction_consistency_still_allows_same_bullet_compound_transition():
    """A single bullet correctly describing two real transitions of the
    SAME metric (rose then fell) must still be treated as ambiguous, not
    flagged — the line-scoping fix must not remove this existing
    protection, only stop it from reaching into OTHER lines."""

    claims_table = {
        "title": "Claims incurred",
        "rows": [
            {"label": "January 2026", "value": 82.1},
            {"label": "February 2026", "value": 91.8},
            {"label": "March 2026", "value": 89.7},
        ],
        "calculations": {},
    }
    narrative = (
        "- Claims incurred rose from $82.1m in January to $91.8m in February before "
        "declining to $89.7m in March."
    )
    assert check_direction_consistency(narrative, [claims_table]) == []


# --- Phase 3 Step 4, Phase C: generalized metric-polarity sentiment check ---

RETENTION_TABLE = {
    "title": "Customer retention",
    "calculations": {
        "total_change": {"from": "January 2026", "to": "March 2026", "absolute": -2.0, "percent": -2.4}
    },
}

UNKNOWN_METRIC_TABLE = {
    "title": "Digital Sales Share",
    "calculations": {
        "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 3.0, "percent": 12.0}
    },
}


def test_direction_consistency_flags_improved_against_a_declining_positive_metric():
    """Customer retention (POSITIVE polarity) actually decreased but is
    called "improved" — must be flagged, symmetric to the existing
    lower-is-better-ratio case but for a higher-is-better metric."""

    narrative = "Customer retention improved by 2.4% from January to March 2026."
    issues = check_direction_consistency(narrative, [RETENTION_TABLE])
    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert "improved" in issues[0].message


def test_direction_consistency_passes_when_worsened_matches_a_declining_positive_metric():
    narrative = "Customer retention worsened by 2.4% from January to March 2026."
    assert check_direction_consistency(narrative, [RETENTION_TABLE]) == []


def test_direction_consistency_flags_any_sentiment_word_for_an_unclassified_metric():
    """The core Phase C requirement: "increased" must never automatically
    become "improved". A metric with no established business polarity
    must never be described with "improved"/"worsened" at all, regardless
    of which direction the number actually moved."""

    narrative = "Digital Sales Share improved by 12.0% from January to March 2026."
    issues = check_direction_consistency(narrative, [UNKNOWN_METRIC_TABLE])
    assert len(issues) == 1
    assert "business direction is not established" in issues[0].message


def test_direction_consistency_passes_neutral_wording_for_an_unclassified_metric():
    narrative = "Digital Sales Share increased by 12.0% from January to March 2026."
    assert check_direction_consistency(narrative, [UNKNOWN_METRIC_TABLE]) == []


# --- Phase 3: safety net for the 414.3%-style bug ---


def test_implausible_percentage_passes_when_it_matches_a_verified_calculation():
    narrative = "Claims backlog rose sharply, a 121.4% increase over the period."
    table = {
        "title": "Claims Backlog",
        "calculations": {"total_change": {"from": "Q1 2025", "to": "Q4 2025", "percent": 121.4}},
    }
    issues = _check_no_implausible_ungrounded_percentages(narrative, [table])
    assert issues == []


def test_implausible_percentage_flags_an_unmatched_large_figure():
    """Regression test for the reported 414.3% bug: a large percentage
    that doesn't match any computed or as-reported figure must be flagged
    as high severity — this is exactly the failure signature Phase 3
    fixed at the extraction layer, and this check is the safety net."""

    narrative = "Claims backlog rose 414.3% over the period, a sharp deterioration."
    table = {
        "title": "Claims Backlog",
        "calculations": {"total_change": {"from": "Q1 2025", "to": "Q4 2025", "percent": 121.4}},
    }
    issues = _check_no_implausible_ungrounded_percentages(narrative, [table])
    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert issues[0].category == "implausible_percentage"
    assert "414.3" in issues[0].message


def test_implausible_percentage_ignores_small_ordinary_figures():
    narrative = "Retention held steady at 92.4%, while complaints rose 8%."
    table = {
        "title": "Claims Backlog",
        "calculations": {"total_change": {"from": "Q1 2025", "to": "Q4 2025", "percent": 121.4}},
    }
    issues = _check_no_implausible_ungrounded_percentages(narrative, [table])
    assert issues == []


def test_implausible_percentage_passes_when_matching_a_reported_change_value():
    narrative = "The final quarter showed a reported change of +240.1%, consistent with source data."
    table = {
        "title": "Claims Backlog",
        "calculations": {},
        "reported_change": [{"label": "Q4 2025", "reported": "+240.1%"}],
    }
    issues = _check_no_implausible_ungrounded_percentages(narrative, [table])
    assert issues == []


def test_implausible_percentage_skips_reports_with_no_structured_metrics():
    narrative = "Some unrelated document cites a 900% figure with no structured backing."
    issues = _check_no_implausible_ungrounded_percentages(narrative, [])
    assert issues == []


# --- Phase 3 Step 2: generic metric title detection ---


def test_generic_metric_title_flagged():
    tables = [{"title": "Total"}, {"title": "Value"}]
    issues = _check_no_generic_metric_titles(tables)
    assert len(issues) == 2
    assert all(issue.severity == "low" for issue in issues)
    assert all(issue.category == "generic_metric_title" for issue in issues)


def test_specific_metric_title_not_flagged():
    tables = [{"title": "Claims Backlog"}, {"title": "West Retention Rate (%)"}]
    assert _check_no_generic_metric_titles(tables) == []


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


def test_period_correctness_flags_changes_section_on_custom_period_even_with_a_previous_report():
    """Phase 3 Step 2 safety net: a Changes Since Last Report section must
    never appear for an ad-hoc/custom-period report, even when a
    previous report genuinely exists — every ad-hoc report shares the
    same generic period_id, so a "match" carries no real scope
    guarantee. This should be structurally impossible given
    SpaReportGenerationService's fix, but is still flagged here as a
    rollout safety net."""

    narrative = "## Changes Since Last Report\nNothing changed."
    previous_report = {"periodId": "custom"}
    issues = _check_period_correctness(narrative, previous_report, "custom")
    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert "Custom / Ad hoc" in issues[0].message


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


# --- Phase C.1: endpoint-value-anchored sentiment check (the gap that let
# "Loss ratio improved from 64.0% to 64.3%" ship uncaught in production —
# check_direction_consistency's percent-anchored sentiment pass never
# fires when no restated delta percentage appears near the sentence, only
# the two raw endpoint values) ---

LOSS_RATIO_TABLE_WITH_ROWS = {
    "title": "Loss ratio",
    "rows": [
        {"label": "January 2026", "value": 64.0},
        {"label": "February 2026", "value": 68.2},
        {"label": "March 2026", "value": 64.3},
    ],
    "calculations": {
        "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 0.3, "percent": 0.5},
        "period_over_period": [
            {"from": "January 2026", "to": "February 2026", "absolute": 4.2, "percent": 6.6},
            {"from": "February 2026", "to": "March 2026", "absolute": -3.9, "percent": -5.7},
        ],
    },
}


def test_endpoint_value_sentiment_catches_the_real_production_bug():
    """The exact real bug found in a generated Financial Analysis PDF:
    'improved' stated with only the raw endpoint values restated, no
    delta percentage — the negative-polarity loss ratio actually rose,
    a deterioration, not an improvement."""

    narrative = "The loss ratio improved from 64.0% in January to 64.3% in March."
    issues = _check_endpoint_value_sentiment(narrative, [LOSS_RATIO_TABLE_WITH_ROWS])
    assert len(issues) == 1
    assert issues[0].severity == "high"
    assert "improved" in issues[0].message
    assert "increased" in issues[0].message


def test_endpoint_value_sentiment_passes_when_correctly_describing_improvement():
    narrative = "The loss ratio improved from 68.2% in February to 64.3% in March."
    assert _check_endpoint_value_sentiment(narrative, [LOSS_RATIO_TABLE_WITH_ROWS]) == []


def test_endpoint_value_sentiment_flags_unclassified_metric():
    table = {
        "title": "Digital Sales Share",
        "rows": [{"label": "January 2026", "value": 20.0}, {"label": "March 2026", "value": 25.0}],
        "calculations": {},
    }
    narrative = "Digital Sales Share improved from 20.0 in January to 25.0 in March."
    issues = _check_endpoint_value_sentiment(narrative, [table])
    assert len(issues) == 1
    assert "not established" in issues[0].message


# --- Phase C.1: apply_deterministic_corrections — the correction half of
# Section 7's "deterministic result -> grounded narrative" requirement.
# Detecting a contradiction is not enough; it must be fixed before the
# reader sees it, not shipped with a passive diagnostic alongside it. ---


def test_corrections_fix_the_real_claims_incurred_bug():
    """The exact real bug: '...decreased by 9.3%... dropped from $82.1m
    in January to $89.7m in March' against a verified +9.3% increase."""

    narrative = (
        "Claims incurred decreased by 9.3% over the same period. Claims incurred "
        "dropped from $82.1m in January to $89.7m in March, following a peak in "
        "February at $91.8m."
    )
    corrected, remaining = apply_deterministic_corrections(narrative, [CLAIMS_TABLE])

    assert "increased by 9.3%" in corrected
    assert "decreased by 9.3%" not in corrected
    assert "rose from $82.1m" in corrected
    assert "dropped from $82.1m" not in corrected
    assert remaining == []


def test_corrections_fix_the_real_loss_ratio_bug_including_the_heading_sentence():
    """The exact real production text: a bolded finding heading and its
    explanatory sentence both wrongly say 'improved' — both must be
    corrected, not just whichever happens to be nearest the numbers."""

    narrative = (
        "Loss ratio improved from 64.0% in January to 64.3% in March, despite a "
        "temporary increase to 68.2% in February."
    )
    corrected, remaining = apply_deterministic_corrections(narrative, [LOSS_RATIO_TABLE_WITH_ROWS])

    assert "worsened" in corrected or "deteriorated" in corrected
    assert "improved from 64.0" not in corrected
    assert remaining == []


def test_corrections_fix_the_claims_backlog_period_mismatch_bug():
    """Section 5's exact scenario: a sentence must never combine one
    period pair's magnitude with a DIFFERENT period pair's direction."""

    backlog_table = {
        "title": "Claims backlog",
        "rows": [
            {"label": "January 2026", "value": 418.0},
            {"label": "February 2026", "value": 452.0},
            {"label": "March 2026", "value": 431.0},
        ],
        "calculations": {
            "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 13.0, "percent": 3.1},
            "period_over_period": [
                {"from": "January 2026", "to": "February 2026", "absolute": 34.0, "percent": 8.1},
                {"from": "February 2026", "to": "March 2026", "absolute": -21.0, "percent": -4.6},
            ],
        },
    }
    narrative = "Claims backlog decreased by 3.1% to 431 cases."
    corrected, remaining = apply_deterministic_corrections(narrative, [backlog_table])

    assert "increased by 3.1%" in corrected
    assert "decreased by 3.1%" not in corrected
    assert remaining == []


def test_corrections_leave_already_correct_narrative_unchanged():
    narrative = "Claims incurred increased by 9.3% between January and March 2026."
    corrected, remaining = apply_deterministic_corrections(narrative, [CLAIMS_TABLE])
    assert corrected == narrative
    assert remaining == []


def test_corrections_rewrite_unclassified_metric_to_neutral_wording():
    table = {
        "title": "Digital Sales Share",
        "rows": [{"label": "January 2026", "value": 20.0}, {"label": "March 2026", "value": 25.0}],
        "calculations": {
            "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 5.0, "percent": 25.0},
        },
    }
    narrative = "Digital Sales Share improved by 25.0% between January and March."
    corrected, remaining = apply_deterministic_corrections(narrative, [table])

    assert "increased by 25.0%" in corrected
    assert "improved" not in corrected
    assert remaining == []


def test_corrections_do_not_touch_unrelated_text():
    narrative = "Overall performance across the business was mixed this quarter."
    corrected, remaining = apply_deterministic_corrections(narrative, [CLAIMS_TABLE, LOSS_RATIO_TABLE_WITH_ROWS])
    assert corrected == narrative
    assert remaining == []


# --- Phase C.1: direction/sentiment word matching must be word-bounded,
# not a substring check — found via real generated output where "a need
# for operational improvements" (an unrelated noun) falsely tripped the
# sentiment word "improvement" for a nearby, correctly-worded figure ---


def test_direction_consistency_does_not_false_positive_on_a_containing_word():
    complaints_table = {
        "title": "Customer complaints",
        "calculations": {
            "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 20.0, "percent": 27.0},
        },
    }
    narrative = (
        "Customer complaints increased by 27.0% over the quarter. This aligns with the "
        "27.0% increase in customer complaints, indicating a need for operational "
        "improvements."
    )
    assert check_direction_consistency(narrative, [complaints_table]) == []


def test_corrections_do_not_misfire_on_a_containing_word():
    complaints_table = {
        "title": "Customer complaints",
        "calculations": {
            "total_change": {"from": "January 2026", "to": "March 2026", "absolute": 20.0, "percent": 27.0},
        },
    }
    narrative = (
        "Customer complaints increased by 27.0% over the quarter. This aligns with the "
        "27.0% increase in customer complaints, indicating a need for operational "
        "improvements."
    )
    corrected, remaining = apply_deterministic_corrections(narrative, [complaints_table])
    assert corrected == narrative
    assert remaining == []


def test_contains_word_matches_whole_word_not_substring():
    from services.report_qc_service import _contains_word

    assert _contains_word("a need for operational improvements", ("improvement",)) is False
    assert _contains_word("the loss ratio improved slightly", ("improved",)) is True
    assert _contains_word("this trend is increasingly common", ("increase",)) is False
    assert _contains_word("claims incurred increased sharply", ("increase",)) is False
    assert _contains_word("claims incurred increased sharply", ("increased",)) is True
