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
    'period-over-period'/'total_change' framing that implies a time
    relationship between unrelated rows — Phase 3 Step 2: it gets
    deterministic cross-sectional stats (highest/lowest/gap) instead,
    never a fabricated "change"."""

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
    assert [row["value"] for row in tables[0]["rows"]] == [32.0, 68.0]
    calc = tables[0]["calculations"]
    assert "total_change" not in calc
    assert "period_over_period" not in calc
    assert calc["cross_sectional"]["highest"] == {"label": "Non-Life", "value": 68.0}
    assert calc["cross_sectional"]["lowest"] == {"label": "Life", "value": 32.0}
    assert tables[0]["dimension_type"] == "categorical"


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


# --- Phase 3: column-role classification (identity / value / derived-rate) ---


def test_value_column_is_titled_from_a_constant_identity_column():
    """The exact reported-bug table shape: Period | Indicator | Risk Level
    | Value | Change/Rate | Trend, with a single indicator throughout. The
    "Value" column must produce ONE series titled by the indicator name
    ("Claims Backlog"), not a series literally titled "Value"."""

    source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Period | Indicator | Risk Level | Value | Change/Rate | Trend |\n"
            "|--------|-----------|------------|------:|-------------:|-------|\n"
            "| Q1 2025 | Claims Backlog | Medium | 14 | +35.7% | Increasing |\n"
            "| Q2 2025 | Claims Backlog | Medium | 19 | +42.1% | Increasing |\n"
            "| Q3 2025 | Claims Backlog | High | 27 | +14.8% | Increasing |\n"
            "| Q4 2025 | Claims Backlog | High | 31 | +121.4% | Increasing |\n"
        ),
    }
    tables = extract_metric_tables([source])

    assert len(tables) == 1
    backlog = tables[0]
    assert backlog["title"] == "Claims Backlog"
    assert [row["value"] for row in backlog["rows"]] == [14, 19, 27, 31]

    # Real, deterministic total change from the VALUE column — 121.4%, not
    # any figure computed from the already-a-percentage Change/Rate column.
    total = backlog["calculations"]["total_change"]
    assert total["percent"] == 121.4


def test_change_rate_column_never_becomes_its_own_series():
    """Regression test for the reported 414.3% bug: a Change/Rate column
    must never be treated as an independent metric with its own
    period-over-period math computed on top of already-computed
    percentages."""

    source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Period | Indicator | Value | Change/Rate |\n"
            "|--------|-----------|------:|-------------:|\n"
            "| Q1 2025 | Claims Backlog | 14 | +35.7% |\n"
            "| Q2 2025 | Claims Backlog | 19 | +42.1% |\n"
            "| Q3 2025 | Claims Backlog | 27 | +14.8% |\n"
            "| Q4 2025 | Claims Backlog | 31 | +121.4% |\n"
        ),
    }
    tables = extract_metric_tables([source])

    assert [t["title"] for t in tables] == ["Claims Backlog"]
    assert not any(t["title"] in ("Change/Rate", "Value") for t in tables)


def test_reported_change_is_attached_as_citable_metadata_not_recomputed():
    source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Period | Indicator | Value | Change/Rate |\n"
            "|--------|-----------|------:|-------------:|\n"
            "| Q1 2025 | Claims Backlog | 14 | +35.7% |\n"
            "| Q2 2025 | Claims Backlog | 19 | +42.1% |\n"
        ),
    }
    tables = extract_metric_tables([source])
    reported = tables[0]["reported_change"]
    assert reported == [
        {"label": "Q1 2025", "reported": "+35.7%"},
        {"label": "Q2 2025", "reported": "+42.1%"},
    ]

    block = format_metrics_for_evidence(tables)
    assert "As-reported change/rate" in block
    assert "+121.4%" not in block  # not present in this fixture; sanity that we're citing verbatim
    assert "+35.7%" in block and "+42.1%" in block


def test_value_column_splits_per_indicator_when_a_table_covers_several():
    """A table can legitimately track several different indicators over
    the same periods — the Value column must split into one series per
    indicator, never one series merging unrelated indicators under a
    single generic "Value" title."""

    source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Period | Indicator | Value |\n"
            "|--------|-----------|------:|\n"
            "| Q1 2025 | Claims Backlog | 14 |\n"
            "| Q2 2025 | Claims Backlog | 19 |\n"
            "| Q1 2025 | Open Complaints | 45 |\n"
            "| Q2 2025 | Open Complaints | 52 |\n"
        ),
    }
    tables = extract_metric_tables([source])

    titles = sorted(t["title"] for t in tables)
    assert titles == ["Claims Backlog", "Open Complaints"]

    backlog = next(t for t in tables if t["title"] == "Claims Backlog")
    assert [row["value"] for row in backlog["rows"]] == [14, 19]
    complaints = next(t for t in tables if t["title"] == "Open Complaints")
    assert [row["value"] for row in complaints["rows"]] == [45, 52]


def test_retention_rate_column_is_not_misclassified_as_a_derived_rate():
    """A column whose header contains "Rate" but is itself a directly
    measured metric (not a change/delta of something else) must remain an
    independent series — only "change"/"delta"-style columns, or columns
    whose values are structurally signed deltas, are derived-rate."""

    source = {
        "filename": "regional.xlsx",
        "excerpt": (
            "| Region | Retention Rate (%) |\n"
            "|--------|--------------------:|\n"
            "| North | 92.4 |\n"
            "| South | 90.1 |\n"
            "| West | 79.3 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert len(tables) == 1
    assert tables[0]["title"] == "Retention Rate (%)"
    assert [row["value"] for row in tables[0]["rows"]] == [92.4, 90.1, 79.3]


# --- Phase 3: granularity-aware dedup (annual summary vs. quarterly detail) ---


def test_same_titled_series_at_different_granularities_are_not_merged():
    """Regression test for the reported $4,134m / 47.1%-vs-30.6% bug: an
    annual summary and a quarterly detail table sharing a column title
    must both survive as distinct series — the quarterly series must never
    silently substitute for the annual one just because it has more rows."""

    annual = {
        "filename": "financials.xlsx",
        "excerpt": (
            "### Sheet: Annual Summary\n\n"
            "| Year | Gross Premium ($m) |\n"
            "|------|--------------------:|\n"
            "| 2023 | 1,200 |\n"
            "| 2024 | 1,367 |\n"
            "| 2025 | 1,567 |\n"
        ),
    }
    quarterly = {
        "filename": "financials.xlsx",
        "excerpt": (
            "### Sheet: Quarterly Detail\n\n"
            "| Quarter | Gross Premium ($m) |\n"
            "|---------|--------------------:|\n"
            "| Q1 2023 | 280 |\n"
            "| Q2 2023 | 295 |\n"
            "| Q3 2023 | 305 |\n"
            "| Q4 2023 | 320 |\n"
            "| Q1 2024 | 320 |\n"
            "| Q2 2024 | 335 |\n"
            "| Q3 2024 | 350 |\n"
            "| Q4 2024 | 362 |\n"
            "| Q1 2025 | 370 |\n"
            "| Q2 2025 | 385 |\n"
            "| Q3 2025 | 400 |\n"
            "| Q4 2025 | 412 |\n"
        ),
    }
    tables = extract_metric_tables([annual, quarterly], max_tables=6)

    matches = [t for t in tables if t["title"] == "Gross Premium ($m)"]
    assert len(matches) == 2

    annual_series = next(t for t in matches if len(t["rows"]) == 3)
    assert annual_series["calculations"]["total_change"]["percent"] == 30.6

    quarterly_series = next(t for t in matches if len(t["rows"]) == 12)
    assert quarterly_series["calculations"]["total_change"]["percent"] == 47.1


def test_evidence_block_disambiguates_same_titled_different_granularity_series():
    """A same-titled annual + quarterly pair must be labeled distinctly in
    the evidence block, so the report writer isn't left guessing which
    same-titled figure a "2023 to 2025" framing should actually cite."""

    annual = {
        "filename": "financials.xlsx",
        "excerpt": (
            "| Year | Gross Premium ($m) |\n"
            "|------|--------------------:|\n"
            "| 2023 | 1,200 |\n"
            "| 2024 | 1,367 |\n"
            "| 2025 | 1,567 |\n"
        ),
    }
    quarterly = {
        "filename": "financials.xlsx",
        "excerpt": (
            "| Quarter | Gross Premium ($m) |\n"
            "|---------|--------------------:|\n"
            "| Q1 2023 | 280 |\n"
            "| Q2 2023 | 295 |\n"
            "| Q3 2023 | 305 |\n"
            "| Q4 2023 | 320 |\n"
            "| Q1 2024 | 320 |\n"
            "| Q2 2024 | 335 |\n"
            "| Q3 2024 | 350 |\n"
            "| Q4 2024 | 362 |\n"
            "| Q1 2025 | 370 |\n"
            "| Q2 2025 | 385 |\n"
            "| Q3 2025 | 400 |\n"
            "| Q4 2025 | 412 |\n"
        ),
    }
    tables = extract_metric_tables([annual, quarterly])
    block = format_metrics_for_evidence(tables)

    assert "Gross Premium ($m) — Annual" in block
    assert "Gross Premium ($m) — Quarterly" in block
    assert "30.6%" in block
    assert "47.1%" in block


def test_evidence_block_does_not_disambiguate_a_single_occurrence_title():
    tables = extract_metric_tables([PREMIUM_TABLE_SOURCE])
    block = format_metrics_for_evidence(tables)
    assert "Gross Premium —" not in block
    assert "**Gross Premium**" in block


def test_same_granularity_dedup_across_documents_is_unaffected():
    """Existing behavior must be preserved: the SAME granularity, same
    title, appearing in two source documents (e.g. overlapping annual
    reports) still dedupes to the single most complete series."""

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


# --- Phase 3: materiality-ranked cap ---


def test_max_tables_cap_keeps_the_most_material_series_not_the_first_encountered():
    """A low-materiality, non-temporal breakdown (no calculable change)
    from an earlier source must not crowd out a highly material, later
    source's series once the cap is reached."""

    low_materiality_source = {
        "filename": "by_product.xlsx",
        "excerpt": (
            "| Product | 2023 ($m) | 2024 ($m) | 2025 ($m) |\n"
            "|---------|----------:|----------:|----------:|\n"
            "| Life | 400 | 455 | 520 |\n"
            "| Non-Life | 500 | 555 | 630 |\n"
            "| Health | 300 | 357 | 417 |\n"
        ),
    }
    high_materiality_source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Quarter | Claims Settlement Backlog (cases) |\n"
            "|---------|------------------------------------:|\n"
            "| Q1 2025 | 14 |\n"
            "| Q2 2025 | 19 |\n"
            "| Q3 2025 | 27 |\n"
            "| Q4 2025 | 31 |\n"
        ),
    }
    tables = extract_metric_tables(
        [low_materiality_source, high_materiality_source], max_tables=3
    )

    titles = [t["title"] for t in tables]
    assert "Claims Settlement Backlog (cases)" in titles


# --- Phase 3: unchanged non-temporal / truncation behavior with the new classifier ---


def test_non_temporal_category_table_without_identity_column_still_works():
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
    assert tables[0]["title"] == "Market Share"
    assert "total_change" not in tables[0]["calculations"]
    assert "period_over_period" not in tables[0]["calculations"]


# --- Phase 3 Step 2: position-independent time-vs-category classification ---


def test_region_first_table_produces_the_same_result_as_time_first():
    """Regression test for the confirmed Region-first bug: a table ordered
    Region-then-Year must classify Year as the time axis and Region as the
    category axis regardless of column position, producing the identical
    per-region result as the Year-first ordering of the same data."""

    year_first = {
        "filename": "retention.xlsx",
        "excerpt": (
            "| Year | Region | Retention Rate (%) |\n"
            "|------|--------|--------------------:|\n"
            "| 2023 | West | 70.0 |\n"
            "| 2024 | West | 65.0 |\n"
            "| 2025 | West | 61.0 |\n"
        ),
    }
    region_first = {
        "filename": "retention.xlsx",
        "excerpt": (
            "| Region | Year | Retention Rate (%) |\n"
            "|--------|------|--------------------:|\n"
            "| West | 2023 | 70.0 |\n"
            "| West | 2024 | 65.0 |\n"
            "| West | 2025 | 61.0 |\n"
        ),
    }

    year_first_tables = extract_metric_tables([year_first])
    region_first_tables = extract_metric_tables([region_first])

    assert len(year_first_tables) == 1
    assert len(region_first_tables) == 1

    yf, rf = year_first_tables[0], region_first_tables[0]
    assert yf["title"] == rf["title"] == "West Retention Rate (%)"
    assert [r["value"] for r in yf["rows"]] == [r["value"] for r in rf["rows"]] == [70.0, 65.0, 61.0]
    assert yf["calculations"]["total_change"]["percent"] == rf["calculations"]["total_change"]["percent"]
    assert rf["calculations"]["total_change"]["percent"] == -12.9
    assert rf["category_value"] == "West"


def test_region_first_multi_region_splits_correctly_per_region():
    source = {
        "filename": "retention.xlsx",
        "excerpt": (
            "| Region | Year | Retention Rate (%) |\n"
            "|--------|------|--------------------:|\n"
            "| North | 2023 | 93.0 |\n"
            "| North | 2024 | 92.4 |\n"
            "| West | 2023 | 70.0 |\n"
            "| West | 2024 | 61.0 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    titles = {t["title"] for t in tables}
    assert titles == {"North Retention Rate (%)", "West Retention Rate (%)"}

    west = next(t for t in tables if t["title"] == "West Retention Rate (%)")
    assert west["calculations"]["total_change"]["percent"] == round((61.0 - 70.0) / 70.0 * 100, 1)


def test_channel_only_categorical_table_gets_cross_sectional_stats_not_a_change():
    """Regression test for the reported 81.6%/131.0%/25.4% bugs: a
    Channel-dimensioned table with no time column at all must never
    produce total_change/period_over_period — only cross-sectional
    highest/lowest stats."""

    source = {
        "filename": "channel_performance.xlsx",
        "excerpt": (
            "| Channel | Premium Share (%) | Complaint Rate (%) | Complaints |\n"
            "|---------|-------------------:|--------------------:|------------:|\n"
            "| Digital | 38 | 3.2 | 126 |\n"
            "| Agents | 30 | 2.1 | 110 |\n"
            "| Brokers | 25 | 1.8 | 100 |\n"
            "| Partners | 7 | 7.4 | 94 |\n"
        ),
    }
    tables = extract_metric_tables([source], max_tables=10)
    assert len(tables) == 3

    for table in tables:
        assert "total_change" not in table["calculations"]
        assert "period_over_period" not in table["calculations"]
        assert table["dimension_type"] == "categorical"

    premium_share = next(t for t in tables if t["title"] == "Premium Share (%)")
    assert premium_share["calculations"]["cross_sectional"]["highest"] == {
        "label": "Digital",
        "value": 38.0,
    }
    assert premium_share["calculations"]["cross_sectional"]["lowest"] == {
        "label": "Partners",
        "value": 7.0,
    }

    block = format_metrics_for_evidence(tables)
    assert "not a time series" in block
    assert "Highest: Digital at 38.0" in block
    assert "Lowest: Partners at 7.0" in block
    # The gap magnitude can legitimately share a number with the reported
    # bug (a cross-sectional gap and a wrongly-framed "decrease" between
    # the same two values are mathematically the same size) — what must
    # never appear is the WRONG framing: a change/increase/decrease
    # phrasing applied to these categorical rows.
    assert "% relative decrease" not in block
    assert "% relative increase" not in block
    assert "total_change" not in block
    assert "period_over_period" not in block


def test_channel_keyword_is_recognized_as_identity_even_without_repeats():
    """"Channel" was previously missing from the identity keyword list —
    confirm it is now recognized even with zero duplicate values (four
    distinct channel names, each appearing once)."""

    source = {
        "filename": "channel.xlsx",
        "excerpt": (
            "| Channel | Value |\n"
            "|---------|------:|\n"
            "| Digital | 38 |\n"
            "| Agents | 30 |\n"
            "| Brokers | 25 |\n"
            "| Partners | 7 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["title"] == "Value"
    assert tables[0]["dimension_type"] == "categorical"


def test_percentage_point_labeling_in_evidence_block():
    source = {
        "filename": "retention.xlsx",
        "excerpt": (
            "| Year | Retention Rate (%) |\n"
            "|------|--------------------:|\n"
            "| 2023 | 70.0 |\n"
            "| 2024 | 65.0 |\n"
            "| 2025 | 61.0 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    block = format_metrics_for_evidence(tables)
    assert "percentage points" in block
    assert "12.9% relative decrease" in block


def test_absolute_value_change_is_not_labeled_percentage_points():
    tables = extract_metric_tables([PREMIUM_TABLE_SOURCE])
    block = format_metrics_for_evidence(tables)
    assert "percentage points" not in block


def test_trend_direction_classification():
    increasing = {
        "filename": "a.xlsx",
        "excerpt": (
            "| Year | Metric |\n"
            "|------|-------:|\n"
            "| 2023 | 10 |\n"
            "| 2024 | 20 |\n"
            "| 2025 | 30 |\n"
        ),
    }
    decreasing = {
        "filename": "b.xlsx",
        "excerpt": (
            "| Year | Metric |\n"
            "|------|-------:|\n"
            "| 2023 | 30 |\n"
            "| 2024 | 20 |\n"
            "| 2025 | 10 |\n"
        ),
    }
    volatile = {
        "filename": "c.xlsx",
        "excerpt": (
            "| Year | Metric |\n"
            "|------|-------:|\n"
            "| 2023 | 10 |\n"
            "| 2024 | 30 |\n"
            "| 2025 | 15 |\n"
        ),
    }
    assert extract_metric_tables([increasing])[0]["calculations"]["direction"] == "increasing"
    assert extract_metric_tables([decreasing])[0]["calculations"]["direction"] == "decreasing"
    assert extract_metric_tables([volatile])[0]["calculations"]["direction"] == "volatile"


def test_retention_rate_column_with_region_column_produces_composite_titles():
    """Regression test matching the audit's Section E finding: a series
    split per category must keep the metric name in its title, not just
    the bare category value — "West Retention Rate (%)", not just
    "West"."""

    source = {
        "filename": "regional.xlsx",
        "excerpt": (
            "| Year | Region | Retention Rate (%) |\n"
            "|------|--------|--------------------:|\n"
            "| 2023 | West | 70.0 |\n"
            "| 2024 | West | 65.0 |\n"
            "| 2025 | West | 61.0 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["title"] == "West Retention Rate (%)"


def test_generic_header_still_titled_from_identity_value_alone():
    """Regression test: Step 1's "Claims Backlog" case (a generic "Value"
    header with a constant Indicator value) must still produce a bare
    identity-value title, not "Claims Backlog Value"."""

    source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Period | Indicator | Value |\n"
            "|--------|-----------|------:|\n"
            "| Q1 2025 | Claims Backlog | 14 |\n"
            "| Q2 2025 | Claims Backlog | 19 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["title"] == "Claims Backlog"


# --- Phase 3 Step 3: metric identity vs. dimension distinction ---


def test_different_metrics_in_one_table_never_get_a_cross_sectional_gap():
    """Regression test for the reported Risk Committee Score bug: a
    "Metric | Value" table with no time column must never treat distinct
    metric NAMES as if they were dimensional instances of one metric —
    each must become its own independent single-observation series, and
    no cross_sectional (highest/lowest/gap) comparison may ever be
    computed between them."""

    source = {
        "filename": "risk_committee.xlsx",
        "excerpt": (
            "| Metric | Value |\n"
            "|--------|------:|\n"
            "| Operational Resilience Score | 81 |\n"
            "| Overall Risk Score | 72 |\n"
            "| Compliance Rating | 88 |\n"
            "| Governance Score | 79 |\n"
        ),
    }
    tables = extract_metric_tables([source], max_tables=10)

    titles = {t["title"] for t in tables}
    assert titles == {
        "Operational Resilience Score",
        "Overall Risk Score",
        "Compliance Rating",
        "Governance Score",
    }
    assert "Value" not in titles

    for table in tables:
        assert table["dimension_type"] == "single_observation"
        assert table["calculations"] == {}
        assert "cross_sectional" not in table["calculations"]
        assert len(table["rows"]) == 1

    resilience = next(t for t in tables if t["title"] == "Operational Resilience Score")
    assert resilience["rows"][0]["value"] == 81.0
    assert resilience["unit"] == "score"

    block = format_metrics_for_evidence(tables)
    assert "single observation" in block
    assert "Highest:" not in block
    assert "gap of" not in block
    # The exact reported bogus figure must never appear.
    assert "12.5%" not in block


def test_metric_identity_column_with_a_single_distinct_value_is_unaffected():
    """A constant metric-identity value (Step 1's "Claims Backlog" case,
    paired with a time column) must be completely unaffected by the new
    metric-identity branch — that branch only fires when there is no
    time column AND the identity column has multiple distinct values."""

    source = {
        "filename": "risk_ops.xlsx",
        "excerpt": (
            "| Period | Indicator | Value |\n"
            "|--------|-----------|------:|\n"
            "| Q1 2025 | Claims Backlog | 14 |\n"
            "| Q2 2025 | Claims Backlog | 19 |\n"
            "| Q3 2025 | Claims Backlog | 27 |\n"
            "| Q4 2025 | Claims Backlog | 31 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["title"] == "Claims Backlog"
    assert tables[0]["dimension_type"] == "temporal"
    assert tables[0]["calculations"]["total_change"]["percent"] == 121.4


def test_dimension_column_still_gets_cross_sectional_treatment():
    """Regression test: "Channel" (a genuine dimension keyword, not a
    metric-identity keyword) must still route through the existing,
    correct cross-sectional path — Step 3's new branch must not
    over-trigger on legitimate dimensional comparisons."""

    source = {
        "filename": "channel.xlsx",
        "excerpt": (
            "| Channel | Premium Share (%) |\n"
            "|---------|-------------------:|\n"
            "| Digital | 38 |\n"
            "| Partners | 7 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    assert tables[0]["title"] == "Premium Share (%)"
    assert tables[0]["dimension_type"] == "categorical"
    assert tables[0]["calculations"]["cross_sectional"]["gap_percent"] == 81.6


def test_indicator_column_with_multiple_distinct_values_and_no_time_splits_independently():
    """"Indicator" is a metric-identity keyword too — a table listing
    several different indicators' single latest values (no time column)
    must split the same way "Metric" does, not be cross-compared."""

    source = {
        "filename": "indicators.xlsx",
        "excerpt": (
            "| Indicator | Value |\n"
            "|-----------|------:|\n"
            "| Customer Satisfaction Index | 74 |\n"
            "| Employee Engagement Index | 68 |\n"
        ),
    }
    tables = extract_metric_tables([source])
    titles = {t["title"] for t in tables}
    assert titles == {"Customer Satisfaction Index", "Employee Engagement Index"}
    for table in tables:
        assert table["dimension_type"] == "single_observation"
