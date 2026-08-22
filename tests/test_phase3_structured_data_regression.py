"""
Phase 3 end-to-end regression: Structured Spreadsheet Intelligence &
Analytical Accuracy.

Rebuilds the three real-world workbook shapes from the reported
production bug (financial performance, regional/customer, risk/
operations) as in-memory Excel files and runs them through the actual
deterministic pipeline — DocumentProcessor.extract_text() ->
extract_metric_tables() — with no mocking of either layer. This is the
exact slice of the pipeline (services/document_processor.py's stats
injection, services/quantitative_analysis_service.py's column
classification/dedup/cap) identified as where all three reported bugs
originate; everything downstream (chart bridge, report writer, export)
was confirmed to be a faithful pass-through, so this is where the fix's
correctness is actually decided. Deliberately does not exercise
embeddings/Qdrant/the LLM call — those layers were confirmed unaffected,
and keeping this suite free of external services keeps it fast and
CI-safe.
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


def _financial_performance_workbook() -> bytes:
    annual_summary = pd.DataFrame(
        {
            "Year": [2023, 2024, 2025],
            "Gross Premium ($m)": [1200, 1367, 1567],
            "Gross Claims ($m)": [780, 861, 940],
            "Operating Expense ($m)": [210, 228, 245],
        }
    )
    quarterly_detail = pd.DataFrame(
        {
            "Quarter": [
                "Q1 2023", "Q2 2023", "Q3 2023", "Q4 2023",
                "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024",
                "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025",
            ],
            "Gross Premium ($m)": [280, 295, 305, 320, 320, 335, 350, 362, 370, 385, 400, 412],
        }
    )
    by_product = pd.DataFrame(
        {
            "Product Line": ["Life", "Non-Life", "Health"],
            "Gross Premium 2023 ($m)": [400, 500, 300],
            "Gross Premium 2024 ($m)": [455, 555, 357],
            "Gross Premium 2025 ($m)": [520, 630, 417],
        }
    )
    assert by_product["Gross Premium 2023 ($m)"].sum() == 1200
    assert by_product["Gross Premium 2024 ($m)"].sum() == 1367
    assert by_product["Gross Premium 2025 ($m)"].sum() == 1567

    return _xlsx_bytes(
        {
            "Annual Summary": annual_summary,
            "Quarterly Detail": quarterly_detail,
            "By Product": by_product,
        }
    )


def _regional_customer_workbook() -> bytes:
    regional = pd.DataFrame(
        {
            "Region": ["North", "South", "East", "West"],
            "Customers": [12500, 9800, 11200, 8700],
            "Complaints": [45, 38, 52, 91],
            "Retention Rate (%)": [92.4, 90.1, 88.7, 79.3],
            "Avg Policy Value ($)": [1450, 1320, 1510, 1390],
        }
    )
    return _xlsx_bytes({"Regional Summary": regional})


def _risk_operations_workbook() -> bytes:
    claims_backlog = pd.DataFrame(
        {
            "Quarter": ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"],
            "Claims Settlement Backlog (cases)": [14, 19, 27, 31],
        }
    )
    risk_indicators = pd.DataFrame(
        {
            "Period": ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"],
            "Indicator": ["Claims Backlog"] * 4,
            "Risk Level": ["Medium", "Medium", "High", "High"],
            "Value": [14, 19, 27, 31],
            "Change/Rate": ["+35.7%", "+42.1%", "+14.8%", "+121.4%"],
            "Trend": ["Increasing"] * 4,
        }
    )
    return _xlsx_bytes({"Claims Backlog": claims_backlog, "Risk Indicators": risk_indicators})


def _extract(filename: str, content: bytes) -> dict[str, str]:
    text = DocumentProcessor.extract_text(_Upload(filename, content))
    return {"filename": filename, "excerpt": text}


def test_claims_backlog_shows_correct_121_percent_never_414_percent():
    """Bug A regression: 14 -> 31 cases must compute to 121.4%, and the
    414.3%-style error (a Change/Rate column recomputed on top of
    itself) must not occur — no series may be titled "Value" or
    "Change/Rate", and no total_change anywhere may equal ~414 or land in
    the 200%+ range these bogus figures fell in."""

    source = _extract("Risk_Operations.xlsx", _risk_operations_workbook())
    tables = extract_metric_tables([source])

    titles = {t["title"] for t in tables}
    assert "Value" not in titles
    assert "Change/Rate" not in titles
    assert "Claims Backlog" in titles or "Claims Settlement Backlog (cases)" in titles

    for table in tables:
        total = (table.get("calculations") or {}).get("total_change")
        if total and total.get("percent") is not None:
            assert total["percent"] < 200, f"{table['title']!r} has implausible change {total['percent']}%"

    backlog = next(
        t for t in tables if t["title"] in ("Claims Backlog", "Claims Settlement Backlog (cases)")
    )
    assert backlog["calculations"]["total_change"]["percent"] == 121.4


def test_gross_premium_annual_change_is_30_6_percent_not_47_1_or_76_percent():
    """Bug B regression: the ANNUAL 2023->2025 change must be 30.6% —
    never substituted with the quarterly 47.1% figure (mislabeled as
    annual), and no fabricated cross-year sum (e.g. "4,134") may appear
    anywhere in the extracted text feeding the report writer."""

    source = _extract("Financial_Performance.xlsx", _financial_performance_workbook())
    text = source["excerpt"]

    assert "4,134" not in text  # the confirmed literal artifact of the sum() bug

    tables = extract_metric_tables([source], max_tables=6)
    premium_series = [t for t in tables if t["title"] == "Gross Premium ($m)"]
    assert len(premium_series) == 2  # annual AND quarterly both survive, distinct granularities

    annual = next(t for t in premium_series if len(t["rows"]) == 3)
    assert annual["calculations"]["total_change"]["percent"] == 30.6

    quarterly = next(t for t in premium_series if len(t["rows"]) == 12)
    assert quarterly["calculations"]["total_change"]["percent"] == 47.1

    block = format_metrics_for_evidence(tables)
    assert "30.6%" in block
    assert "4,134" not in block


def test_combined_three_document_evidence_has_no_generic_chart_titles():
    """Bug C regression: across all three real-world workbook shapes
    combined, no metric series may be titled with a generic raw column
    header like "Value" or "ChangeRate" — every value column must resolve
    to a real, human-meaningful metric name."""

    sources = [
        _extract("Financial_Performance.xlsx", _financial_performance_workbook()),
        _extract("Regional_Customer.xlsx", _regional_customer_workbook()),
        _extract("Risk_Operations.xlsx", _risk_operations_workbook()),
    ]
    tables = extract_metric_tables(sources, max_tables=6)

    assert tables, "expected at least one metric table across all three workbooks"
    generic_titles = {"value", "changerate", "change/rate", "change", "rate"}
    for table in tables:
        assert table["title"].strip().lower() not in generic_titles, (
            f"chart-eligible series has a generic, non-meaningful title: {table['title']!r}"
        )


def test_max_tables_cap_does_not_silently_drop_the_most_material_workbook():
    """Finding E regression: the workbook with the single most material
    metric (Claims Backlog, 121.4% change) must not be entirely crowded
    out of the capped evidence set by a different workbook's low-
    materiality, non-temporal breakdown columns, purely due to processing
    order."""

    sources = [
        _extract("Financial_Performance.xlsx", _financial_performance_workbook()),
        _extract("Regional_Customer.xlsx", _regional_customer_workbook()),
        _extract("Risk_Operations.xlsx", _risk_operations_workbook()),
    ]
    tables = extract_metric_tables(sources, max_tables=6)

    titles = {t["title"] for t in tables}
    assert "Claims Backlog" in titles or "Claims Settlement Backlog (cases)" in titles
