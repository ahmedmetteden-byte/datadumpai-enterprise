"""
Permanent regression fixture for the production incident where a real
customer workbook (not a synthetic recreation) still produced "Risk
Committee Score decreased by 12.5%" — a fabricated change between two
genuinely different metrics — despite Phase 3 Steps 1-3 already being
deployed.

Root cause (confirmed by reading the ACTUAL production Excel files,
DataDumpAI_Test_0{1,2,3}_*.xlsx, not a guessed recreation):

The real "Executive Risk Summary" sheet is shaped
    Year | Owner | Indicator | Score | Assessment | Interpretation
with Year=2025 on every row (no real time axis) and BOTH "Owner"
(constant "Risk Committee") and "Indicator" (three distinct metric
names) independently qualifying as identity columns. The pre-incident
code:
  1. Treated the constant "Year" column as a valid 3-point time series,
     since its temporal-regex check never required the values to
     actually differ.
  2. Picked "Owner" over "Indicator" as the identity column purely
     because it appeared first by column position, never reaching the
     metric-identity split logic (which requires the identity column to
     have 2+ distinct values — "Owner" has exactly 1).

The same root cause independently caused a second, quieter bug: the real
"Channel Performance" sheet (also Year=2025 on every row) lost ALL FOUR
of its metrics (Premium Share %, Retention Rate, Complaints, Complaint
Rate) from Verified Calculations entirely, since each channel ended up
with exactly one row per group under the wrongly-selected time axis.

These exact real sheet shapes are captured here permanently so this
class of bug — a same-valued "period" column plus multiple candidate
identity columns — cannot silently return.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from services.document_processor import DocumentProcessor
from services.quantitative_analysis_service import extract_metric_tables, format_metrics_for_evidence


class _Upload(BytesIO):
    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name


def _xlsx_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


def _real_risk_operations_workbook() -> bytes:
    """Matches the actual DataDumpAI_Test_03_Risk_Operations.xlsx
    structure exactly, verified by reading the real file directly."""

    risk_indicators = pd.DataFrame(
        {
            "Period": [
                "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025",
                "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025",
                "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025",
            ],
            "Domain": ["Claims"] * 4 + ["Capital"] * 4 + ["Technology"] * 4,
            "Indicator": (
                ["Claims settlement backlog"] * 4
                + ["Capital adequacy ratio"] * 4
                + ["Digital adoption"] * 4
            ),
            "Risk Level": [
                "High", "High", "Critical", "Critical",
                "Medium", "Medium", "High", "High",
                "Low", "Low", "Low", "Low",
            ],
            "Value": [14, 19, 27, 31, 162, 154, 148, 146, 52, 59, 66, 72],
            "Change/Rate": [9.2, 11.8, 16.4, 18.1, 0, 0, 0, 0, 0, 0, 0, 0],
            "Trend": (
                ["Rising"] * 4 + ["Stable", "Falling", "Falling", "Falling"] + ["Rising"] * 4
            ),
            "Management Note": [
                "West region accounts for 46% of overdue cases",
                "Backlog increased despite additional claims staff",
                "West remains highest; Health also deteriorating",
                "Escalations and complaints increased",
                "Above internal minimum of 145%",
                "Buffer narrowing",
                "Near internal early-warning threshold",
                "Only 1 percentage point above threshold",
                "Mobile self-service adoption growing",
                "Digital claims pilot launched",
                "Pilot reduced average handling time",
                "Digital channel has lowest complaint rate",
            ],
        }
    )
    executive_risk_summary = pd.DataFrame(
        {
            "Year": [2025, 2025, 2025],
            "Owner": ["Risk Committee", "Risk Committee", "Risk Committee"],
            "Indicator": [
                "Overall risk score",
                "Operational resilience score",
                "Customer confidence indicator",
            ],
            "Score": [72, 81, 63],
            "Assessment": ["High", "Medium", "High"],
            "Interpretation": [
                "Driven by claims backlog, capital buffer compression and West-region complaints",
                "Technology controls improved, but claims operations remain a bottleneck",
                "Complaints and retention diverge materially in West",
            ],
        }
    )
    return _xlsx_bytes(
        {
            "Risk Indicators": risk_indicators,
            "Executive Risk Summary": executive_risk_summary,
        }
    )


def _real_regional_customer_workbook() -> bytes:
    """Matches the actual DataDumpAI_Test_02_Regional_Customer.xlsx
    "Channel Performance" sheet exactly."""

    channel_performance = pd.DataFrame(
        {
            "Year": [2025, 2025, 2025, 2025],
            "Channel": ["Direct Digital", "Agents", "Brokers", "Partners"],
            "Premium Share %": [38, 34, 21, 7],
            "Retention Rate": [0.86, 0.78, 0.81, 0.69],
            "Complaints": [122, 285, 194, 91],
            "Complaint Rate": [4.2, 7.9, 6.4, 9.7],
        }
    )
    return _xlsx_bytes({"Channel Performance": channel_performance})


def _extract(filename: str, content: bytes) -> dict[str, str]:
    text = DocumentProcessor.extract_text(_Upload(filename, content))
    return {"filename": filename, "excerpt": text}


# --- Executive Risk Summary: the exact reported incident ---


def test_three_risk_committee_metrics_remain_distinct_single_observations():
    """The core regression test for this incident: Overall risk score
    (72), Operational resilience score (81), and Customer confidence
    indicator (63) must each become their own independent
    single-observation series — never one series comparing them to each
    other, and never any "Risk Committee Score" composite title."""

    source = _extract("Risk_Operations.xlsx", _real_risk_operations_workbook())
    tables = extract_metric_tables([source], max_tables=20)

    by_title = {t["title"]: t for t in tables}

    assert "Risk Committee Score" not in by_title, (
        "the exact fabricated composite title from the incident must never appear"
    )

    for title, expected_value in (
        ("Overall risk score", 72.0),
        ("Operational resilience score", 81.0),
        ("Customer confidence indicator", 63.0),
    ):
        assert title in by_title, f"expected {title!r} as its own series"
        series = by_title[title]
        assert series["dimension_type"] == "single_observation"
        assert len(series["rows"]) == 1
        assert series["rows"][0]["value"] == expected_value
        # No change/gap of any kind may ever be computed for a
        # single-observation metric.
        assert series["calculations"] == {}


def test_no_change_is_ever_computed_between_the_three_risk_scores():
    """Even indirectly: no series anywhere in the extraction may show a
    total_change or period_over_period whose absolute value matches the
    fabricated 12.5% (or any other cross-score delta)."""

    source = _extract("Risk_Operations.xlsx", _real_risk_operations_workbook())
    tables = extract_metric_tables([source], max_tables=20)

    for table in tables:
        calc = table.get("calculations") or {}
        assert "total_change" not in calc or table["title"] not in (
            "Overall risk score",
            "Operational resilience score",
            "Customer confidence indicator",
            "Risk Committee Score",
        )

    block = format_metrics_for_evidence(tables)
    assert "12.5%" not in block
    assert "Risk Committee Score" not in block
    assert "single observation" in block


def test_year_column_with_no_variation_is_never_treated_as_a_time_series():
    """Direct regression test for the explicit scenario requested: a
    table where Year=2025 for every row, with multiple distinct
    Indicator values, must be classified as a metric-identity/
    categorical structure, never a time series."""

    source = {
        "filename": "scorecard.xlsx",
        "excerpt": (
            "| Year | Indicator | Score |\n"
            "|------|-----------|------:|\n"
            "| 2025 | Overall risk score | 72 |\n"
            "| 2025 | Operational resilience score | 81 |\n"
            "| 2025 | Customer confidence indicator | 63 |\n"
        ),
    }
    tables = extract_metric_tables([source], max_tables=20)

    assert len(tables) == 3
    for table in tables:
        assert table["dimension_type"] == "single_observation"
        assert "total_change" not in (table.get("calculations") or {})
        assert "period_over_period" not in (table.get("calculations") or {})
        assert "cross_sectional" not in (table.get("calculations") or {})


def test_owner_column_does_not_win_over_indicator_despite_appearing_first():
    """Direct regression test for the identity-column-selection bug:
    "Owner" (constant, appears before "Indicator" in column order) must
    not be selected as the identity column merely because of its
    position — "Indicator" (metric_identity kind, actually varies) must
    win."""

    source = _extract("Risk_Operations.xlsx", _real_risk_operations_workbook())
    tables = extract_metric_tables([source], max_tables=20)
    titles = {t["title"] for t in tables}

    assert "Risk Committee" not in titles
    assert {
        "Overall risk score",
        "Operational resilience score",
        "Customer confidence indicator",
    } <= titles


def test_claims_backlog_and_digital_adoption_get_correct_metric_identities():
    """The Risk Indicators sheet has the SAME "which identity column
    wins" question (Domain vs. Indicator) — Claims settlement backlog
    and Digital adoption must be titled by their real Indicator name, not
    collapsed under their generic Domain value ("Claims"/"Technology")."""

    source = _extract("Risk_Operations.xlsx", _real_risk_operations_workbook())
    tables = extract_metric_tables([source], max_tables=20)
    titles = {t["title"] for t in tables}

    assert "Claims settlement backlog" in titles
    assert "Digital adoption" in titles
    assert "Capital adequacy ratio" in titles
    # The generic Domain values must never become series titles on their own.
    assert "Claims" not in titles
    assert "Technology" not in titles
    assert "Capital" not in titles

    backlog = next(t for t in tables if t["title"] == "Claims settlement backlog")
    assert backlog["calculations"]["total_change"]["percent"] == 121.4


# --- Channel Performance: the same root cause, different symptom ---


def test_channel_performance_produces_real_cross_sectional_findings():
    """Regression test for the quieter, second symptom of the same root
    cause: the real Channel Performance sheet (also Year=2025 constant)
    must produce genuine deterministic cross-sectional findings for all
    four metrics, not silently lose them because each channel ends up
    with only one row under a wrongly-selected time axis."""

    source = _extract("Regional_Customer.xlsx", _real_regional_customer_workbook())
    tables = extract_metric_tables([source], max_tables=20)
    by_title = {t["title"]: t for t in tables}

    for metric in ("Premium Share %", "Retention Rate", "Complaints", "Complaint Rate"):
        assert metric in by_title, f"expected a categorical series for {metric!r}"
        series = by_title[metric]
        assert series["dimension_type"] == "categorical"
        assert "cross_sectional" in series["calculations"]

    retention = by_title["Retention Rate"]
    cross = retention["calculations"]["cross_sectional"]
    assert cross["highest"]["label"] == "Direct Digital"
    assert cross["highest"]["value"] == 0.86


def test_direct_digital_retention_is_never_framed_as_an_improvement():
    """Direct Digital's 86% retention must be represented in the
    evidence as the highest among channels (a cross-sectional fact),
    never with change/improvement language, since there is no prior
    Direct Digital retention observation anywhere in the evidence."""

    source = _extract("Regional_Customer.xlsx", _real_regional_customer_workbook())
    tables = extract_metric_tables([source], max_tables=20)
    block = format_metrics_for_evidence(tables)

    retention_entry_start = block.index("**Retention Rate**")
    next_marker = block.index("**", retention_entry_start + 2)
    entry_end = block.index("**", next_marker + 2)
    retention_entry = block[retention_entry_start:entry_end]

    assert "not a time series" in retention_entry
    assert "% relative increase" not in retention_entry
    assert "% relative decrease" not in retention_entry
    assert "Highest: Direct Digital at 0.86" in retention_entry
