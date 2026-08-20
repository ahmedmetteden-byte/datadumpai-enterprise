"""
Tests for deterministic quantitative analysis (Phase 3 Step 1): numeric
table detection in retrieved evidence, and programmatic period-over-period
/ total-change calculation — the LLM must never be trusted to invent these
figures itself.
"""

from __future__ import annotations

from services.quantitative_analysis_service import (
    extract_metric_tables,
    format_metrics_for_evidence,
)

PREMIUM_TABLE_SOURCE = {
    "filename": "Annual-Statistical-Market-Report-2024.pdf",
    "excerpt": (
        "### Revenue by Year\n\n"
        "| Year | Gross Premium | Gross Claims |\n"
        "|------|---------------:|-------------:|\n"
        "| 2022 | 789.6 | 420.0 |\n"
        "| 2023 | 1,043.1 | 421.0 |\n"
        "| 2024 | 1,558.7 | 635.5 |\n"
    ),
}


def test_computes_exact_yoy_and_total_growth_from_a_real_table():
    """Regression-style accuracy check with hand-verified expected values —
    the whole point of this service is that these numbers come from
    Python arithmetic, not an LLM estimate."""

    tables = extract_metric_tables([PREMIUM_TABLE_SOURCE])

    premium = next(t for t in tables if t["title"] == "Gross Premium")
    assert premium["source_document"] == "Annual-Statistical-Market-Report-2024.pdf"
    assert [row["value"] for row in premium["rows"]] == [789.6, 1043.1, 1558.7]

    yoy = premium["calculations"]["period_over_period"]
    assert yoy[0]["from"] == "2022" and yoy[0]["to"] == "2023"
    assert yoy[0]["absolute"] == round(1043.1 - 789.6, 2)
    assert yoy[0]["percent"] == round((1043.1 - 789.6) / 789.6 * 100, 1)
    # 32.1%, not the "~32.3%" some earlier LLM-estimated report text used —
    # this is precisely the class of small inaccuracy this feature removes.
    assert yoy[0]["percent"] == 32.1

    assert yoy[1]["percent"] == round((1558.7 - 1043.1) / 1043.1 * 100, 1)
    assert yoy[1]["percent"] == 49.4

    total = premium["calculations"]["total_change"]
    assert total["from"] == "2022" and total["to"] == "2024"
    assert total["absolute"] == round(1558.7 - 789.6, 2)
    assert total["percent"] == round((1558.7 - 789.6) / 789.6 * 100, 1)
    assert total["percent"] == 97.4


def test_extracts_a_second_independent_metric_from_the_same_table():
    tables = extract_metric_tables([PREMIUM_TABLE_SOURCE])

    claims = next(t for t in tables if t["title"] == "Gross Claims")
    assert [row["value"] for row in claims["rows"]] == [420.0, 421.0, 635.5]
    assert claims["calculations"]["total_change"]["percent"] == round(
        (635.5 - 420.0) / 420.0 * 100, 1
    )


def test_infers_currency_unit_from_header_and_cells():
    source = {
        "filename": "report.pdf",
        "excerpt": (
            "| Year | Gross Premium (₦bn) |\n"
            "|------|---------------------:|\n"
            "| 2022 | ₦789.6 |\n"
            "| 2023 | ₦1,043.1 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["unit"] == "₦ billion"


def test_skips_truncated_table_with_a_short_row():
    """Simulates retrieval clipping a table mid-row — must be skipped, not
    computed from incomplete/misaligned data."""

    source = {
        "filename": "report.pdf",
        "excerpt": (
            "| Year | Gross Premium |\n"
            "|------|---------------:|\n"
            "| 2022 | 789.6 |\n"
            "| 2023 |\n"  # truncated row — missing the value cell
            "| 2024 | 1,558.7 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables == []


def test_non_temporal_labels_produce_rows_without_fabricated_period_deltas():
    """A category-comparison table (not a time series) must not get a
    'period-over-period' framing that implies a time relationship between
    unrelated rows."""

    source = {
        "filename": "report.pdf",
        "excerpt": (
            "| Segment | Market Share |\n"
            "|---------|-------------:|\n"
            "| Life | 32.0 |\n"
            "| Non-Life | 68.0 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["calculations"] == {}
    assert [row["value"] for row in tables[0]["rows"]] == [32.0, 68.0]


def test_skips_a_table_whose_header_row_is_actually_a_data_row():
    """Report Output Quality Upgrade Step D: a real-world failure mode
    discovered when PDF-sourced tables started reaching this function —
    a chunk/retrieval boundary can split a table's real header row from
    its data rows, leaving the first surviving data row ("| 2022 | 789.6
    | 420.0 |") mistaken for the header. Parsing it as-is would title a
    metric "789.6" instead of "Gross Premium". A genuine header's
    non-label columns are metric names, never pure numbers — if every one
    of them parses as a number, the table must be skipped, not
    mislabeled."""

    source = {
        "filename": "report.pdf",
        "excerpt": (
            "| 2022 | 789.6 | 420.0 |\n"
            "| 2023 | 1,043.1 | 421.0 |\n"
            "| 2024 | 1,558.7 | 635.5 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables == []


def test_no_numeric_table_produces_no_tables_and_no_evidence_block():
    source = {
        "filename": "notes.pdf",
        "excerpt": "The working group discussed governance themes at length, with no figures cited.",
    }
    tables = extract_metric_tables([source])
    assert tables == []
    assert format_metrics_for_evidence(tables) == ""


def test_deduplicates_the_same_metric_across_multiple_source_documents():
    """The same table (with overlapping years) commonly appears in more
    than one annual report — keep the most complete series, not both."""

    shorter = {
        "filename": "Annual-Statistical-Market-Report-2023.pdf",
        "excerpt": (
            "| Year | Gross Premium |\n"
            "|------|---------------:|\n"
            "| 2022 | 789.6 |\n"
            "| 2023 | 1,043.1 |\n"
        ),
    }
    longer = {
        "filename": "Annual-Statistical-Market-Report-2024.pdf",
        "excerpt": (
            "| Year | Gross Premium |\n"
            "|------|---------------:|\n"
            "| 2022 | 789.6 |\n"
            "| 2023 | 1,043.1 |\n"
            "| 2024 | 1,558.7 |\n"
        ),
    }
    tables = extract_metric_tables([shorter, longer])

    matches = [t for t in tables if t["title"] == "Gross Premium"]
    assert len(matches) == 1
    assert len(matches[0]["rows"]) == 3
    assert matches[0]["source_document"] == "Annual-Statistical-Market-Report-2024.pdf"


def test_comma_grouped_year_labels_are_still_recognized_as_temporal():
    """Regression test: XLSX-sourced tables render integer years through
    document_processor.py's cell formatter, which comma-groups every
    numeric cell — turning "2022" into "2,022". Calculations must still
    fire for this real-world case, not silently no-op."""

    source = {
        "filename": "q4_revenue.xlsx",
        "excerpt": (
            "| Year | Gross Premium |\n"
            "|------|---------------:|\n"
            "| 2,022 | 789.6 |\n"
            "| 2,023 | 1,043.1 |\n"
            "| 2,024 | 1,558.7 |\n"
        ),
    }
    tables = extract_metric_tables([source])

    premium = next(t for t in tables if t["title"] == "Gross Premium")
    assert [row["label"] for row in premium["rows"]] == ["2022", "2023", "2024"]

    total = premium["calculations"]["total_change"]
    assert total["percent"] == 97.4
    yoy = premium["calculations"]["period_over_period"]
    assert yoy[0]["percent"] == 32.1 and yoy[1]["percent"] == 49.4


def test_evidence_block_cites_exact_computed_figures():
    tables = extract_metric_tables([PREMIUM_TABLE_SOURCE])
    block = format_metrics_for_evidence(tables)

    assert "Verified Calculations" in block
    assert "do not recompute or estimate" in block
    assert "32.1%" in block
    assert "49.4%" in block
    assert "97.4%" in block
    assert "789.6" in block
    assert "1,558.7" in block
