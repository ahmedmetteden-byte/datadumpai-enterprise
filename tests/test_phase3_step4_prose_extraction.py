"""
Phase 3 Step 4, Phase A: cross-document prose metric extraction.

Regression tests for the deterministic foundation fix — real DataDumpAI
source documents (Word-doc "Key Findings" bullets, one data point per
metric per document) previously produced NO Verified Calculations block
at all, because extract_metric_tables() only recognized markdown pipe
tables. These tests use the actual prose shape of the three real monthly
report fixtures that exposed the bug (see PROJECT context: January/
February/March 2026 monthly reports), not markdown tables, to prove the
fix reaches the real-world document shape it was built for.

Ground truth (verified by hand against the source documents):

  Gross premium:      128.4 -> 134.7 -> 139.6   (Jan -> Mar: +8.7%)
  Claims incurred:      82.1 ->  91.8 ->  89.7   (Jan -> Mar: +9.3%, Feb peak)
  Loss ratio:            64.0 ->  68.2 ->  64.3   (Jan->Feb +4.2pp, Feb->Mar -3.9pp, Jan->Mar +0.3pp)
  Customer retention:    84.2 ->  83.6 ->  85.1   (Jan -> Mar: +0.9pp, Feb trough)
  Customer complaints:     74 ->    89 ->    94   (Jan -> Mar: +27.0%)
  Claims backlog:         418 ->   452 ->   431   (Jan -> Mar: +3.1%, Feb peak)
"""

from __future__ import annotations

import pytest

from services.quantitative_analysis_service import extract_metric_tables

JANUARY_TEXT = """January 2026 Monthly Business Report
Reporting period: January 2026
Executive Summary
January closed with steady commercial activity and improving customer engagement. Gross premium reached $128.4m, up 6.2% from December, while claims incurred were $82.1m, up 3.4%. The stronger premium growth compared with claims was a positive early indicator for the month.
Key Findings
Gross premium: $128.4m, +6.2% month-on-month.
Claims incurred: $82.1m, +3.4% month-on-month.
Loss ratio: 64.0%, down from 65.7% in December.
Customer retention: 84.2%, up from 82.9%.
Claims backlog: 418 cases, down from 447.
Risks & Issues
The claims backlog remains material despite the January reduction. The Northern region recorded the highest backlog at 126 cases. Customer complaints also increased to 74 during the month, requiring monitoring.
Opportunities
Digital sales accounted for 31% of new premium and had the highest retention rate at 88.1%. Management could investigate the practices associated with this channel's stronger retention.
Recommendations
Maintain focus on reducing the claims backlog; investigate the Northern region's backlog concentration; review the causes of the increase in complaints; and assess whether successful digital-channel practices can be replicated elsewhere."""

FEBRUARY_TEXT = """February 2026 Monthly Business Report
Reporting period: February 2026
Executive Summary
February delivered further premium growth, although claims increased faster than premium. Gross premium reached $134.7m, while claims incurred rose to $91.8m. Retention remained strong overall, but the claims trend warrants management attention.
Key Findings
Gross premium: $134.7m, +4.9% month-on-month.
Claims incurred: $91.8m, +11.8% month-on-month.
Loss ratio: 68.2%, up from 64.0% in January.
Customer retention: 83.6%, down from 84.2%.
Claims backlog: 452 cases, up from 418.
Risks & Issues
Claims growth materially outpaced premium growth in February. The Western region recorded 141 outstanding claims, the highest regional backlog. Complaints increased to 89, while retention declined modestly.
Opportunities
Digital remained the strongest retention channel at 87.5%. Corporate accounts also produced 18% of new premium while maintaining an 85.9% retention rate.
Recommendations
Prioritize claims processing capacity in the Western region; investigate the February increase in claims frequency; monitor retention by channel; and examine whether the digital and corporate channels can support further quality growth."""

MARCH_TEXT = """March 2026 Monthly Business Report
Reporting period: March 2026
Executive Summary
March showed a mixed performance. Gross premium increased to $139.6m, while claims moderated to $89.7m. The loss ratio improved from February, and the claims backlog declined, although customer complaints remained elevated.
Key Findings
Gross premium: $139.6m, +3.6% month-on-month.
Claims incurred: $89.7m, -2.3% month-on-month.
Loss ratio: 64.3%, down from 68.2% in February.
Customer retention: 85.1%, up from 83.6%.
Claims backlog: 431 cases, down from 452.
Risks & Issues
Customer complaints remained high at 94 despite the improvement in retention. The Western region continued to have the largest claims backlog at 133 cases. Management should determine whether the backlog is concentrated in specific products or claim types.
Opportunities
Digital retention increased to 89.0%, the highest reported channel rate. Small-business accounts also showed improved retention at 84.8%. These results provide useful areas for further investigation.
Recommendations
Continue the claims-backlog reduction programme; investigate the persistent Western-region concentration; analyze complaint drivers by product and channel; and identify practices associated with the strongest retention performance."""


def _three_month_sources() -> list[dict[str, str]]:
    return [
        {"filename": "January_2026_Monthly_Report.docx", "excerpt": JANUARY_TEXT},
        {"filename": "February_2026_Monthly_Report.docx", "excerpt": FEBRUARY_TEXT},
        {"filename": "March_2026_Monthly_Report.docx", "excerpt": MARCH_TEXT},
    ]


def _tables_by_title(tables: list[dict]) -> dict[str, dict]:
    return {str(t["title"]).strip().lower(): t for t in tables}


def test_extract_metric_tables_finds_no_markdown_tables_in_real_source_shape():
    """Sanity check confirming the bug's premise: these fixtures contain
    zero markdown tables, only prose — exercising the OLD table-only path
    alone must return nothing for any of the three documents."""

    from services.report_markdown_renderer import parse_markdown_blocks

    for text in (JANUARY_TEXT, FEBRUARY_TEXT, MARCH_TEXT):
        assert not any(block.block_type == "table" for block in parse_markdown_blocks(text))


def test_gross_premium_percentage_change_across_three_documents():
    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    by_title = _tables_by_title(tables)
    premium = by_title["gross premium"]

    assert [row["value"] for row in premium["rows"]] == [128.4, 134.7, 139.6]
    total = premium["calculations"]["total_change"]
    assert total["from"] == "January 2026"
    assert total["to"] == "March 2026"
    assert total["percent"] == pytest.approx(8.7, abs=0.05)


def test_claims_incurred_percentage_change_and_february_peak():
    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    claims = _tables_by_title(tables)["claims incurred"]

    total = claims["calculations"]["total_change"]
    assert total["percent"] == pytest.approx(9.3, abs=0.05)

    peak = claims["calculations"]["peak"]
    assert peak["label"] == "February 2026"
    assert peak["value"] == 91.8
    assert claims["calculations"]["recovered_after_peak"] is True

    period_over_period = claims["calculations"]["period_over_period"]
    assert period_over_period[0]["percent"] == pytest.approx(11.8, abs=0.05)  # Jan -> Feb
    assert period_over_period[1]["percent"] == pytest.approx(-2.3, abs=0.05)  # Feb -> Mar


def test_loss_ratio_distinguishes_percentage_point_change_from_percentage_change():
    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    loss_ratio = _tables_by_title(tables)["loss ratio"]
    calculations = loss_ratio["calculations"]

    period_over_period = calculations["period_over_period"]
    jan_to_feb, feb_to_mar = period_over_period[0], period_over_period[1]

    # Percentage-POINT change (absolute) — the figure the audit's ground
    # truth is expressed in.
    assert jan_to_feb["absolute"] == pytest.approx(4.2, abs=0.05)
    assert feb_to_mar["absolute"] == pytest.approx(-3.9, abs=0.05)
    assert calculations["total_change"]["absolute"] == pytest.approx(0.3, abs=0.05)

    # Percentage (relative) change is a DIFFERENT number from the
    # percentage-point change for a "%"-unit metric — must never collapse
    # to the same figure.
    assert jan_to_feb["percent"] != pytest.approx(jan_to_feb["absolute"], abs=0.01)

    from services.quantitative_analysis_service import format_metrics_for_evidence

    rendered = format_metrics_for_evidence(tables)
    assert "percentage points" in rendered
    assert "+4.2 percentage points" in rendered
    assert "-3.9 percentage points" in rendered
    assert "+0.3 percentage points" in rendered


def test_loss_ratio_february_recognized_as_peak_recovering_by_march():
    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    loss_ratio = _tables_by_title(tables)["loss ratio"]
    calculations = loss_ratio["calculations"]

    assert calculations["peak"]["label"] == "February 2026"
    assert calculations["peak"]["value"] == 68.2
    assert calculations["recovered_after_peak"] is True


def test_customer_retention_percentage_point_change_and_february_trough():
    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    retention = _tables_by_title(tables)["customer retention"]
    calculations = retention["calculations"]

    assert calculations["total_change"]["absolute"] == pytest.approx(0.9, abs=0.05)

    trough = calculations["trough"]
    assert trough["label"] == "February 2026"
    assert trough["value"] == 83.6
    assert calculations["recovered_after_trough"] is True


def test_customer_complaints_percentage_change_via_narrative_verb_pattern():
    """Complaints figures are NOT stated as "Label: value" anywhere in
    the real source documents — they only appear in narrative sentences
    ("Customer complaints also increased to 74 during the month."),
    exercising the narrative-verb extraction path specifically, not the
    colon-based "Label:" path the other five metrics use."""

    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    complaints = _tables_by_title(tables)["customer complaints"]

    rows_by_period = {row["label"]: row["value"] for row in complaints["rows"]}
    assert rows_by_period["January 2026"] == 74.0
    assert rows_by_period["March 2026"] == 94.0

    total = complaints["calculations"]["total_change"]
    assert total["percent"] == pytest.approx(27.0, abs=0.5)


def test_claims_backlog_percentage_change_and_february_peak():
    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    backlog = _tables_by_title(tables)["claims backlog"]
    calculations = backlog["calculations"]

    assert calculations["total_change"]["percent"] == pytest.approx(3.1, abs=0.1)
    assert calculations["peak"]["label"] == "February 2026"
    assert calculations["peak"]["value"] == 452.0
    assert calculations["recovered_after_peak"] is True


def test_does_not_merge_differently_labeled_complaints_mentions():
    """February's document says "Complaints increased to 89" (not
    "Customer complaints") — this must NOT be silently folded into the
    "Customer complaints" series just because the labels are related;
    exact-match normalization means it simply doesn't join that series."""

    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    by_title = _tables_by_title(tables)

    complaints = by_title["customer complaints"]
    periods = {row["label"] for row in complaints["rows"]}
    assert "February 2026" not in periods
    assert periods == {"January 2026", "March 2026"}

    # The standalone "Complaints" (February-only) observation must not
    # have formed its OWN series either — a single document contributes
    # only one point, never enough for a temporal series on its own.
    assert "complaints" not in by_title


def test_document_coverage_all_three_documents_contribute_metrics():
    """No single document should be silently excluded from the
    deterministic evidence — every one of the three source documents
    must contribute to at least one metric series."""

    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    contributing_documents: set[str] = set()
    for table in tables:
        for filename in str(table["source_document"]).split(", "):
            contributing_documents.add(filename)

    assert contributing_documents == {
        "January_2026_Monthly_Report.docx",
        "February_2026_Monthly_Report.docx",
        "March_2026_Monthly_Report.docx",
    }


def test_prose_extraction_uses_period_date_metadata_when_available():
    """period_date is the highest-priority ordering signal — when set,
    it must be used even if it contradicts the "Reporting period:" text
    or upload order, and the resulting row label reflects it."""

    sources = [
        {"filename": "doc_a.docx", "excerpt": "Reporting period: January 2026\nGross margin: 40%."},
        {"filename": "doc_b.docx", "excerpt": "Reporting period: February 2026\nGross margin: 45%."},
    ]
    document_periods = {
        "doc_a.docx": {"period_date": "2026-01-15", "uploaded_at": "2026-06-01T00:00:00Z"},
        "doc_b.docx": {"period_date": "2026-02-15", "uploaded_at": "2026-05-01T00:00:00Z"},
    }

    tables = extract_metric_tables(sources, document_periods=document_periods)
    margin = _tables_by_title(tables)["gross margin"]
    labels_in_order = [row["label"] for row in margin["rows"]]
    # Ordered by period_date (Jan before Feb), not by the later
    # uploaded_at for doc_a (which would reverse the order if used).
    assert labels_in_order == ["January 2026", "February 2026"]


def test_prose_extraction_falls_back_to_reporting_period_text_for_legacy_documents():
    """No period_date at all — falls back to the document's own
    "Reporting period: <text>" line for both ordering and the display
    label."""

    sources = [
        {"filename": "legacy_jan.docx", "excerpt": "Reporting period: January 2026\nOccupancy rate: 70%."},
        {"filename": "legacy_mar.docx", "excerpt": "Reporting period: March 2026\nOccupancy rate: 82%."},
    ]

    tables = extract_metric_tables(sources, document_periods={})
    occupancy = _tables_by_title(tables)["occupancy rate"]
    labels_in_order = [row["label"] for row in occupancy["rows"]]
    assert labels_in_order == ["January 2026", "March 2026"]


def test_prose_extraction_rejects_runaway_reporting_period_match():
    """Confirmed in a real production export: when a source document's
    paragraph breaks collapse during text extraction, "Reporting period:"
    runs straight into the next heading and body text with no period
    between them, and _REPORTING_PERIOD_PATTERN — which only stops at a
    literal "." or newline — captured the entire following paragraph and
    shipped it verbatim as a chart axis label. The display label must fall
    back to the clean uploaded_at-derived month instead of that runaway
    text, while ordering still works."""

    sources = [
        {
            "filename": "legacy_jan.docx",
            "excerpt": (
                "Reporting period: January 2026 Executive Summary January closed with "
                "steady commercial activity and improving customer engagement. "
                "Occupancy rate: 70%."
            ),
        },
        {
            "filename": "legacy_mar.docx",
            "excerpt": (
                "Reporting period: March 2026 Executive Summary March showed a mixed "
                "performance. Occupancy rate: 82%."
            ),
        },
    ]
    document_periods = {
        "legacy_jan.docx": {"uploaded_at": "2026-01-15T00:00:00Z"},
        "legacy_mar.docx": {"uploaded_at": "2026-03-15T00:00:00Z"},
    }

    tables = extract_metric_tables(sources, document_periods=document_periods)
    occupancy = _tables_by_title(tables)["occupancy rate"]
    labels_in_order = [row["label"] for row in occupancy["rows"]]
    assert labels_in_order == ["January 2026", "March 2026"]


def test_prose_extraction_falls_back_to_uploaded_at_for_legacy_documents_without_period_text():
    """No period_date AND no "Reporting period:" line at all — the
    lowest-priority fallback (uploaded_at) still allows ordering rather
    than excluding the document outright."""

    sources = [
        {"filename": "older.docx", "excerpt": "Attrition rate: 5%."},
        {"filename": "newer.docx", "excerpt": "Attrition rate: 8%."},
    ]
    document_periods = {
        "older.docx": {"period_date": None, "uploaded_at": "2026-01-01T00:00:00Z"},
        "newer.docx": {"period_date": None, "uploaded_at": "2026-03-01T00:00:00Z"},
    }

    tables = extract_metric_tables(sources, document_periods=document_periods)
    attrition = _tables_by_title(tables)["attrition rate"]
    assert [row["value"] for row in attrition["rows"]] == [5.0, 8.0]


def test_document_with_no_ordering_signal_is_excluded_rather_than_guessed():
    """No period_date, no "Reporting period:" text, no uploaded_at at
    all — must be excluded from cross-document aggregation entirely
    rather than assigning it an arbitrary position in the series."""

    sources = [
        {"filename": "known.docx", "excerpt": "Reporting period: January 2026\nDefault rate: 2%."},
        {"filename": "unknown.docx", "excerpt": "Default rate: 9%."},
    ]
    document_periods = {"known.docx": {}, "unknown.docx": {}}

    tables = extract_metric_tables(sources, document_periods=document_periods)
    # Only one document had any ordering signal — not enough points to
    # form a 2+-period series, so no "Default rate" series should exist.
    by_title = _tables_by_title(tables)
    assert "default rate" not in by_title


def test_mixed_units_under_the_same_label_are_not_aggregated():
    """The same label reported with two different units across documents
    (a count in one, a percentage in another) must never be silently
    combined into one series — that would compare incompatible things."""

    sources = [
        {"filename": "a.docx", "excerpt": "Reporting period: January 2026\nOpen cases: 12."},
        {"filename": "b.docx", "excerpt": "Reporting period: February 2026\nOpen cases: 40%."},
    ]

    tables = extract_metric_tables(sources, document_periods={})
    by_title = _tables_by_title(tables)
    assert "open cases" not in by_title


def test_kill_switch_disables_prose_cross_document_extraction(monkeypatch):
    monkeypatch.setattr(
        "services.quantitative_analysis_service.QUANT_PROSE_EXTRACTION_ENABLED", False
    )

    tables = extract_metric_tables(_three_month_sources(), document_periods={})
    assert tables == []


def test_omitting_document_periods_argument_keeps_prior_behavior_unchanged():
    """Backward compatibility: a caller that doesn't pass the new
    document_periods argument at all must see no prose-derived series —
    matching every pre-existing call site's behavior before this phase."""

    tables = extract_metric_tables(_three_month_sources())
    assert tables == []
