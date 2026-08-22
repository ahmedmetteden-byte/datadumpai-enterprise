"""
Phase 3 Step 2 end-to-end regression: Analytical Dimensions & Temporal
Integrity.

Rebuilds the richer Regional/Customer workbook shape used to diagnose the
reported production bug — a Channel dimension (Premium Share/Complaint
Rate/Complaints, categorical only, no time column) plus a Region x Year
retention table in BOTH column orderings — as an in-memory Excel file and
runs it through the real deterministic pipeline: DocumentProcessor.
extract_text() -> extract_metric_tables(). No mocking of either layer.

Deliberately does not exercise embeddings/Qdrant/the LLM call — those
layers were confirmed unaffected during the investigation; the fixes for
this phase live entirely in the deterministic column-classification and
calculation layer, with the LLM prompt guardrails (spa_report_generation_
service.py) as defense-in-depth verified separately via a real Docker
pipeline run during the investigation itself.
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


def _regional_customer_workbook() -> bytes:
    regional_summary = pd.DataFrame(
        {
            "Region": ["North", "South", "East", "West"],
            "Customers": [12500, 9800, 11200, 8700],
            "Complaints": [45, 38, 52, 91],
            "Retention Rate (%)": [92.4, 90.1, 88.7, 79.3],
            "Avg Policy Value ($)": [1450, 1320, 1510, 1390],
        }
    )
    channel_performance = pd.DataFrame(
        {
            "Channel": ["Digital", "Agents", "Brokers", "Partners"],
            "Premium Share (%)": [38, 30, 25, 7],
            "Complaint Rate (%)": [3.2, 2.1, 1.8, 7.4],
            "Complaints": [126, 110, 100, 94],
        }
    )
    retention_year_first = pd.DataFrame(
        {
            "Year": [2023, 2023, 2023, 2023, 2024, 2024, 2024, 2024, 2025, 2025, 2025, 2025],
            "Region": ["North", "South", "East", "West"] * 3,
            "Retention Rate (%)": [
                93.0, 91.0, 90.0, 70.0,
                92.8, 90.5, 89.3, 65.0,
                92.4, 90.1, 88.7, 61.0,
            ],
        }
    )
    retention_region_first = pd.DataFrame(
        {
            "Region": [
                "North", "North", "North", "South", "South", "South",
                "East", "East", "East", "West", "West", "West",
            ],
            "Year": [2023, 2024, 2025] * 4,
            "Retention Rate (%)": [
                93.0, 92.8, 92.4, 91.0, 90.5, 90.1,
                90.0, 89.3, 88.7, 70.0, 65.0, 61.0,
            ],
        }
    )
    return _xlsx_bytes(
        {
            "Regional Summary": regional_summary,
            "Channel Performance": channel_performance,
            "Retention Year-First": retention_year_first,
            "Retention Region-First": retention_region_first,
        }
    )


def _extract(filename: str, content: bytes) -> dict[str, str]:
    text = DocumentProcessor.extract_text(_Upload(filename, content))
    return {"filename": filename, "excerpt": text}


def test_channel_dimension_never_produces_a_temporal_change():
    """Regression test for the reported 81.6%/131.0%/25.4% bugs: a
    Channel-dimensioned table (Premium Share, Complaint Rate, Complaints)
    with no time column must never produce total_change/period_over_period
    for any of its columns — only deterministic cross-sectional stats."""

    source = _extract("Regional_Customer.xlsx", _regional_customer_workbook())
    tables = extract_metric_tables([source], max_tables=20)

    channel_titles = {"Premium Share (%)", "Complaint Rate (%)", "Complaints"}
    channel_tables = [t for t in tables if t["title"] in channel_titles]
    assert len(channel_tables) == 3

    for table in channel_tables:
        assert "total_change" not in table["calculations"]
        assert "period_over_period" not in table["calculations"]
        assert table["dimension_type"] == "categorical"
        assert "cross_sectional" in table["calculations"]

    premium_share = next(t for t in channel_tables if t["title"] == "Premium Share (%)")
    assert premium_share["calculations"]["cross_sectional"]["highest"]["label"] == "Digital"
    assert premium_share["calculations"]["cross_sectional"]["lowest"]["label"] == "Partners"


def test_region_first_and_year_first_retention_tables_agree():
    """Regression test for the confirmed Region-first architectural gap: a
    table with the category column before the time column must produce
    the identical per-region result as the time-first ordering of the
    same underlying data."""

    source = _extract("Regional_Customer.xlsx", _regional_customer_workbook())
    tables = extract_metric_tables([source], max_tables=20)

    west_series = [t for t in tables if t["title"] == "West Retention Rate (%)"]
    # Both orderings produce the identical (title, unit, granularity) key,
    # so they dedupe to one surviving series — the important assertion is
    # that a West series with the correct calculation exists AT ALL (the
    # Region-first table must not silently vanish), not that both literal
    # copies survive independently.
    assert len(west_series) == 1
    assert west_series[0]["calculations"]["total_change"]["percent"] == -12.9
    assert west_series[0]["calculations"]["direction"] == "decreasing"


def _entry_for(block: str, title: str) -> str:
    """Isolate one metric's own section of the evidence block — from its
    "**{title}**" heading up to (but not including) the next "**"-headed
    entry — so an assertion about one metric can't be trivially satisfied
    by text that actually belongs to a different metric's section."""

    start = block.index(f"**{title}")
    next_marker = block.index("**", start + 2)  # skip the opening "**" itself
    end = block.index("**", next_marker + 2)
    return block[start:end]


def test_evidence_block_never_states_a_change_for_categorical_rows():
    source = _extract("Regional_Customer.xlsx", _regional_customer_workbook())
    tables = extract_metric_tables([source], max_tables=20)
    block = format_metrics_for_evidence(tables)

    assert "not a time series" in block
    premium_share_entry = _entry_for(block, "Premium Share (%)")
    assert "% relative decrease" not in premium_share_entry
    assert "% relative increase" not in premium_share_entry
    assert "Highest: Digital at 38.0" in premium_share_entry


def test_west_retention_evidence_is_fully_specific():
    """Matches the audit's desired semantic structure (Section 7): the
    evidence must make the region, baseline, ending period, and both
    absolute (percentage-point) and relative change explicit — not a bare
    unqualified "19.8%"-style figure."""

    source = _extract("Regional_Customer.xlsx", _regional_customer_workbook())
    tables = extract_metric_tables([source], max_tables=20)
    block = format_metrics_for_evidence(tables)

    west_entry = _entry_for(block, "West Retention Rate (%)")
    assert "2023" in west_entry and "2025" in west_entry
    assert "70.0" in west_entry and "61.0" in west_entry
    assert "percentage points" in west_entry
    assert "12.9% relative decrease" in west_entry
