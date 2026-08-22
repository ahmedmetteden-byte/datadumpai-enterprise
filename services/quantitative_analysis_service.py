"""
Deterministic quantitative analysis over retrieved evidence.

Detects numeric tables in already-retrieved source excerpts and computes
period-over-period / total change programmatically, so the report writer
interprets already-calculated numbers instead of estimating them from
prose. See services/visualization_engine.py's _table_financial_series()
for the sibling implementation this mirrors (same table-parsing primitive,
same numeric-cell-parsing approach, different purpose: chart data there,
narrative evidence here).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.report_markdown_renderer import parse_markdown_blocks

_METRIC_COLUMN_KEYWORDS = (
    "revenue",
    "expense",
    "cost",
    "profit",
    "margin",
    "growth",
    "sales",
    "amount",
    "value",
    "total",
    "premium",
    "claim",
    "share",
    "count",
)

_UNIT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"₦|naira|ngn", re.IGNORECASE), "₦"),
    (re.compile(r"\$|usd\b", re.IGNORECASE), "$"),
    (re.compile(r"€|eur\b", re.IGNORECASE), "€"),
    (re.compile(r"£|gbp\b", re.IGNORECASE), "£"),
)

_TEMPORAL_YEAR = re.compile(r"^(19|20)\d{2}$")
_TEMPORAL_QUARTER = re.compile(r"^q[1-4]\s*'?\d{2,4}$", re.IGNORECASE)
_TEMPORAL_MONTH_YEAR = re.compile(
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{2,4}$",
    re.IGNORECASE,
)

# A column whose header names something OTHER than a value identifies
# WHAT a row's value is about, rather than being a metric itself. But
# "identifies what a row is about" splits into two semantically opposite
# cases, both handled by _is_identity_column() below but requiring
# different downstream treatment (Phase 3 Step 3, _identity_column_kind):
#
# - DIMENSION: the column's values are INSTANCES of one shared,
#   externally-named metric (Region="West", Channel="Digital") — a
#   sibling value column names the metric; the identity column names
#   WHICH population/segment/product it was measured for. Comparing two
#   instances (highest/lowest/gap) is valid: they measure the same thing.
# - METRIC IDENTITY: the column's values ARE distinct metric identities
#   themselves ("Operational Resilience Score", "Overall Risk Score") —
#   there is no single shared metric; each row is its own, independent,
#   non-comparable measurement. Comparing two rows as "highest/lowest" is
#   as invalid as claiming one caused a change in the other — they don't
#   measure the same thing at all.
_DIMENSION_KEYWORDS = (
    "category",
    "segment",
    "product",
    "region",
    "type",
    "class",
    "line",
    "channel",
    "branch",
    "unit",
    "department",
    "risk",
    "group",
)
_METRIC_IDENTITY_KEYWORDS = (
    "indicator",
    "metric",
    "name",
    "label",
)
_IDENTITY_COLUMN_KEYWORDS = _DIMENSION_KEYWORDS + _METRIC_IDENTITY_KEYWORDS

# A column whose header names a change/delta ("Change/Rate", "YoY Delta")
# describes the MOVEMENT of another column's value — it is not an
# independent metric, and must never have period-over-period/total-change
# computed on top of it (that would be a percent-change-of-a-percent).
# Deliberately excludes the bare word "rate" — "Retention Rate (%)" or
# "Growth Rate" are themselves independently-measured metrics, not a
# derived description of another column.
_DERIVED_RATE_COLUMN_KEYWORDS = (
    "change",
    "delta",
    "variance",
    "yoy",
    "mom",
    "qoq",
    "vs prior",
    "vs previous",
)

_SIGNED_CELL = re.compile(r"^[+-]\s*[\d.,]")


def _parse_numeric_cell(cell: str) -> float | None:
    cleaned = re.sub(r"[₦$€£,%\s]", "", cell)
    cleaned = re.sub(r"(?i:million|billion|bn|thousand|k)$", "", cleaned)
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _infer_unit(header: str, sample_cells: list[str]) -> str:
    haystack = header + " " + " ".join(sample_cells)

    for pattern, symbol in _UNIT_PATTERNS:
        if pattern.search(haystack):
            for scale_word in ("billion", "bn"):
                if re.search(scale_word, haystack, re.IGNORECASE):
                    return f"{symbol} billion"
            for scale_word in ("million", "m"):
                if re.search(rf"\b{scale_word}\b", haystack, re.IGNORECASE):
                    return f"{symbol} million"
            return symbol

    if "%" in haystack:
        return "%"

    # Checked last, only after currency/percent detection fails, so it
    # never overrides an existing correct unit (e.g. "Retention Rate (%)"
    # still correctly resolves to "%" above, never "score"). A purely
    # dimensionless "score"/"rating" column (e.g. a Risk Committee
    # scorecard) currently has no unit at all otherwise — a labeling
    # clarity nicety, not a correctness fix.
    if re.search(r"\bscore\b|\brating\b", haystack, re.IGNORECASE):
        return "score"

    return ""


def _looks_temporal(label: str) -> bool:
    stripped = label.strip()
    return bool(
        _TEMPORAL_YEAR.match(stripped)
        or _TEMPORAL_QUARTER.match(stripped)
        or _TEMPORAL_MONTH_YEAR.match(stripped)
    )


def _normalize_temporal_label(label: str) -> str:
    """A year can arrive comma-grouped (e.g. "2,022") because upstream
    tabular rendering (document_processor.py's cell formatter) applies
    thousands-separator formatting to every numeric cell, including a
    year/period column. Strip the comma when doing so reveals a valid
    temporal label, so "2,022" is recognized as the year 2022 instead of
    silently failing _looks_temporal() and disabling all calculations for
    the table. Leave genuinely non-temporal labels (which may legitimately
    contain a comma) untouched."""

    stripped = label.strip()
    if "," not in stripped:
        return stripped
    without_commas = stripped.replace(",", "")
    return without_commas if _looks_temporal(without_commas) else stripped


def _is_identity_column(header: str, raw_cells: list[str]) -> bool:
    """A non-numeric column that names what each row is about (an
    "Indicator", "Region", "Product"...). Detected by header keyword, and
    generalized beyond a fixed keyword list via two cardinality heuristics:
    a grouping dimension's values commonly repeat across rows (unlike free
    narrative/notes text, where every row tends to differ); and, even
    without a repeat, a small bounded set of distinct non-numeric values
    (e.g. four channel names, each appearing once in a cross-sectional
    table) plausibly names a category axis rather than unique per-row
    prose. The second heuristic is deliberately conservative (small
    distinct-count ceiling, minimum row count) to avoid mistaking a short
    free-text notes column for a dimension."""

    if any(keyword in header.lower() for keyword in _IDENTITY_COLUMN_KEYWORDS):
        return True
    values = [cell.strip() for cell in raw_cells if cell.strip()]
    if len(values) < 2:
        return False
    distinct = len(set(values))
    if distinct < len(values):
        return True
    return len(values) >= 3 and distinct <= 8


def _identity_column_kind(header: str) -> str:
    """Sub-classifies an already-detected identity column as "dimension"
    (values are instances of one shared, externally-named metric) or
    "metric_identity" (values ARE distinct, non-comparable metric
    identities — see the _DIMENSION_KEYWORDS/_METRIC_IDENTITY_KEYWORDS
    comment above). A metric-identity keyword match takes priority since
    it is the narrower, more specific signal; the structural (non-
    keyword) cardinality fallback in _is_identity_column() defaults to
    "dimension" here — real-world tables where a column holds genuinely
    different metric names essentially always use one of the
    metric-identity header words, so the ambiguous, keyword-free case
    defaults to the already-proven-correct dimension behavior."""

    header_lower = header.lower()
    if any(keyword in header_lower for keyword in _METRIC_IDENTITY_KEYWORDS):
        return "metric_identity"
    return "dimension"


def _select_identity_column(
    candidates: list[int], header: list[str], data_rows: list[list[str]]
) -> int | None:
    """When multiple columns could each serve as the identity/category
    axis, pick the one that actually identifies WHAT is being measured —
    not simply whichever comes first by position (Phase 3 incident fix).

    Confirmed via the real "Executive Risk Summary" sheet (Year | Owner |
    Indicator | Score | Assessment | Interpretation): "Owner" (constant
    "Risk Committee" on every row) and "Indicator" (three genuinely
    different metric names) both qualify as identity columns, but only
    "Indicator" is the semantically correct one. Picking the first by
    position selected "Owner" — constant, so it never triggers the
    per-category split at all — which is exactly how three unrelated
    metrics ("Overall risk score", "Operational resilience score",
    "Customer confidence indicator") ended up treated as one 3-point
    "Risk Committee Score" time series.

    Preference order: a metric_identity-kind column (its values ARE
    distinct metric identities) beats a dimension-kind column, since a
    metric-identity column is the more specific, narrower signal, and
    picking the "wrong kind" is what caused the incident. Within the same
    kind, more distinct values wins as a tiebreaker — a constant column
    provides no grouping/labeling value at all. Ties beyond that resolve
    to whichever candidate appears first (Python's max() is stable),
    matching the previous, simpler behavior for the common case where
    only one real candidate exists.
    """

    if not candidates:
        return None

    def _score(col_index: int) -> tuple[int, int]:
        kind = _identity_column_kind(header[col_index].strip())
        values = [
            row[col_index].strip()
            for row in data_rows
            if len(row) > col_index and row[col_index].strip()
        ]
        distinct = len(set(values))
        kind_rank = 1 if kind == "metric_identity" else 0
        return (kind_rank, distinct)

    return max(candidates, key=_score)


def _is_derived_rate_column(header: str, raw_cells: list[str]) -> bool:
    """A numeric-parseable column that describes another column's change
    rather than being an independent metric — detected by header keyword,
    or structurally: change/delta values are conventionally written with
    an explicit sign ("+35.7%"), which a first-class measured value
    (a price, a count, a rate) essentially never is."""

    if any(keyword in header.lower() for keyword in _DERIVED_RATE_COLUMN_KEYWORDS):
        return True
    values = [cell.strip() for cell in raw_cells if cell.strip()]
    if not values:
        return False
    signed = sum(1 for cell in values if _SIGNED_CELL.match(cell))
    return signed > len(values) / 2


def _infer_granularity(rows: list[dict[str, Any]]) -> str:
    """Coarse time granularity of a series' row labels, used to keep
    same-titled series at different granularities (e.g. an annual summary
    vs. a quarterly detail sheet) from being silently substituted for one
    another during dedup — "more rows" means "finer-grained," not
    "more authoritative."""

    labels = [row["label"] for row in rows]
    if labels and all(_TEMPORAL_QUARTER.match(label) for label in labels):
        return "quarterly"
    if labels and all(_TEMPORAL_MONTH_YEAR.match(label) for label in labels):
        return "monthly"
    if labels and all(_TEMPORAL_YEAR.match(label) for label in labels):
        return "annual"
    return "other"


@dataclass
class MetricSeries:
    title: str
    source_document: str
    unit: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    calculations: dict[str, Any] = field(default_factory=dict)
    reported_change: list[dict[str, str]] = field(default_factory=list)
    # Phase 3 Step 2: explicit dimension metadata, so downstream consumers
    # (chart bridge, evidence rendering) never have to re-derive "is this
    # temporal or categorical" from calculations' shape alone.
    dimension_type: str = "temporal"  # "temporal" | "categorical" | "temporal_by_category"
    category_value: str | None = None
    metric_group: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source_document": self.source_document,
            "unit": self.unit,
            "rows": self.rows,
            "calculations": self.calculations,
            "reported_change": self.reported_change,
            "dimension_type": self.dimension_type,
            "category_value": self.category_value,
            "metric_group": self.metric_group,
        }


def _compute_calculations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Absolute/percent change between adjacent rows and start-to-end —
    only meaningful when row labels are temporal (see _looks_temporal),
    since "period-over-period" implies a time order between rows."""

    if len(rows) < 2:
        return {}

    period_over_period: list[dict[str, Any]] = []
    for prior, current in zip(rows, rows[1:]):
        prior_value = prior["value"]
        current_value = current["value"]
        absolute = current_value - prior_value
        percent = (absolute / prior_value * 100) if prior_value else None
        period_over_period.append(
            {
                "from": prior["label"],
                "to": current["label"],
                "absolute": round(absolute, 2),
                "percent": round(percent, 1) if percent is not None else None,
            }
        )

    first, last = rows[0], rows[-1]
    total_absolute = last["value"] - first["value"]
    total_percent = (total_absolute / first["value"] * 100) if first["value"] else None

    return {
        "period_over_period": period_over_period,
        "total_change": {
            "from": first["label"],
            "to": last["label"],
            "absolute": round(total_absolute, 2),
            "percent": round(total_percent, 1) if total_percent is not None else None,
        },
        "direction": _trend_direction(period_over_period),
    }


def _trend_direction(period_over_period: list[dict[str, Any]]) -> str:
    """Qualitative shape of a temporal series, derived purely from the
    sign pattern of already-computed period-over-period deltas — no new
    data source, just a label for numbers that exist already."""

    percents = [c["percent"] for c in period_over_period if c["percent"] is not None]
    if not percents:
        return "stable"
    if all(abs(p) < 1.0 for p in percents):
        return "stable"
    if all(p > 0 for p in percents):
        return "increasing"
    if all(p < 0 for p in percents):
        return "decreasing"
    return "volatile"


def _compute_cross_sectional_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic highest/lowest/range/gap for a CATEGORICAL (non-
    temporal) comparison — the cross-sectional counterpart to
    _compute_calculations(). Gives the report writer genuine Verified-
    Calculations content for "which category is highest/lowest" instead
    of leaving it to infer a (potentially fabricated) change from bare,
    unflagged rows. Never computes a "change" — categories have no
    inherent order, so there is no "first" or "last" to diff."""

    if len(rows) < 2:
        return {}

    highest = max(rows, key=lambda r: r["value"])
    lowest = min(rows, key=lambda r: r["value"])
    value_range = round(highest["value"] - lowest["value"], 2)
    gap_percent = round(value_range / highest["value"] * 100, 1) if highest["value"] else None

    return {
        "cross_sectional": {
            "highest": {"label": highest["label"], "value": highest["value"]},
            "lowest": {"label": lowest["label"], "value": lowest["value"]},
            "range": value_range,
            "gap_percent": gap_percent,
        }
    }


_GENERIC_VALUE_HEADERS = {"value", "amount", "total", "figure", "sum", "count", "number"}


def _compose_category_title(category_value: str, column_header: str) -> str:
    """When a value column is split per category, title the resulting
    series from the category value alone if the column header is a
    generic placeholder ("Value", "Total"...) — matching Step 1's "Claims
    Backlog" case, where the header carried no real information — or as
    "{category} {header}" when the header names a real metric (e.g. "West
    Retention Rate (%)"), so the metric identity survives alongside the
    dimension instead of being silently dropped."""

    if not category_value:
        return column_header
    if column_header.strip().lower() in _GENERIC_VALUE_HEADERS:
        return category_value
    return f"{category_value} {column_header}"


def _classify_column(column_header: str, raw_cells: list[str]) -> str:
    """Column-position-independent role classification: "temporal" (row
    labels are years/quarters/months — reuses _looks_temporal, no longer
    hardcoded to column 0), "identity" (a category-naming column),
    "derived_rate", "value", or "narrative" (ignored). This is what makes
    a `Region | Year | Retention Rate` table (category-first) work
    identically to a `Year | Region | Retention Rate` table (time-first)
    — previously only the second ordering worked, since temporality was
    only ever checked against column 0."""

    # Temporal is checked first, directly against the (possibly non-
    # numeric) string label — "Q1 2025" and "Jan 2024" are temporal but
    # not numeric-parseable, so gating this behind a numeric check first
    # (as an earlier draft of this function did) would silently stop
    # recognizing quarter/month-year columns as temporal at all.
    normalized = [_normalize_temporal_label(cell.strip()) for cell in raw_cells]
    temporal_count = sum(1 for label in normalized if _looks_temporal(label))
    looks_temporal_enough = bool(normalized) and temporal_count >= max(2, len(normalized) - 1)
    if looks_temporal_enough:
        # A period column must actually vary to be a real time axis
        # (Phase 3 incident fix): a real workbook's "Executive Risk
        # Summary" sheet has Year=2025 for every row — every cell matches
        # the temporal regex, but there is no second period to compare
        # against. Without this check, that column was still treated as
        # a valid 3-point time series, and _compute_calculations()
        # computed a "period-over-period" change between two rows that
        # share the IDENTICAL period label — confirmed to produce exactly
        # the reported "Risk Committee Score decreased by 12.5%"
        # fabrication. A genuine 2+-period series (even a single
        # Previous-vs-Current transition) always has at least 2 distinct
        # labels, so this never affects a real time series.
        if len(set(normalized)) >= 2:
            return "temporal"
        # Every cell looks like a period/date but never actually varies.
        # It is still fundamentally a period-shaped column, not a real
        # measurement — it must NOT fall through to the numeric/"value"
        # check below just because "2025" happens to parse as a number,
        # or its constant year gets charted as if it were a measured
        # metric (confirmed: this exact fallthrough produced a spurious
        # "Overall risk score = 2025" series during the incident fix).
        return "narrative"

    if all(_parse_numeric_cell(cell) is not None for cell in raw_cells):
        if _is_derived_rate_column(column_header, raw_cells):
            return "derived_rate"
        return "value"
    if _is_identity_column(column_header, raw_cells):
        return "identity"
    return "narrative"


def _extract_from_table(rows: list[list[str]], *, source_document: str) -> list[MetricSeries]:
    if len(rows) < 3:
        # Need a header row plus at least 2 data rows to compute a change.
        return []

    header = rows[0]
    data_rows = rows[1:]
    if len(header) < 2:
        return []

    # A genuine header's non-label columns are metric names ("Gross
    # Premium"), never pure numbers. If every one of them parses as a
    # number, this "header" is almost certainly a data row — most likely
    # a real table whose actual header row was separated from its data by
    # a chunk/retrieval boundary upstream, leaving the first surviving row
    # mistaken for the header. Parsing it anyway produces a chart/finding
    # titled with a raw figure (e.g. "420.0") instead of a metric name, so
    # this table is skipped entirely rather than mislabeled.
    if all(_parse_numeric_cell(cell) is not None for cell in header[1:]):
        return []

    # Pass 1: classify EVERY column (including column 0 — no longer a
    # hardcoded assumption that the first column is always the time/label
    # axis). A column with a misaligned row count (truncated table) is
    # treated as narrative/ignored rather than guessed at.
    col_roles: dict[int, str] = {}
    for col_index in range(len(header)):
        column_header = header[col_index].strip()
        raw_cells = [row[col_index] for row in data_rows if len(row) > col_index]
        if not column_header or len(raw_cells) != len(data_rows):
            col_roles[col_index] = "narrative"
            continue
        col_roles[col_index] = _classify_column(column_header, raw_cells)

    time_col = next((i for i in range(len(header)) if col_roles.get(i) == "temporal"), None)
    identity_candidates = [
        i for i in range(len(header)) if col_roles.get(i) == "identity" and i != time_col
    ]
    identity_col = _select_identity_column(identity_candidates, header, data_rows)
    # Whichever column carries the row's "what period/category is this"
    # label — the time column when one exists (wherever it sits), else
    # the identity column, else column 0 as a safe default for tables
    # with neither a recognizable time nor category axis.
    label_col = time_col if time_col is not None else (identity_col if identity_col is not None else 0)
    temporal = time_col is not None
    identity_kind = (
        _identity_column_kind(header[identity_col].strip()) if identity_col is not None else "dimension"
    )

    value_cols = [
        i
        for i in range(len(header))
        if col_roles.get(i) == "value" and i not in (time_col, identity_col, label_col)
    ]
    derived_rate_cols = [i for i in range(len(header)) if col_roles.get(i) == "derived_rate"]

    row_identities: list[str] = []
    if identity_col is not None:
        row_identities = [
            row[identity_col].strip() if len(row) > identity_col else "" for row in data_rows
        ]

    series_list: list[MetricSeries] = []

    for col_index in value_cols:
        column_header = header[col_index].strip()

        parsed_rows: list[dict[str, Any]] = []
        aligned_identities: list[str] = []
        for row_i, row in enumerate(data_rows):
            if len(row) <= col_index or len(row) <= label_col:
                continue
            label = _normalize_temporal_label(row[label_col].strip())
            value = _parse_numeric_cell(row[col_index])
            if not label or value is None:
                continue
            parsed_rows.append({"label": label, "value": value})
            aligned_identities.append(row_identities[row_i] if row_identities else "")

        # Require every data row to have parsed as numeric in this column —
        # a partially-numeric column is more likely a label/notes column
        # than a real metric, and a truncated table (retrieval clipping cut
        # a row mid-way) should be skipped rather than computed from
        # incomplete data.
        if len(parsed_rows) < 2 or len(parsed_rows) != len(data_rows):
            continue

        raw_value_cells = [row[col_index] for row in data_rows if len(row) > col_index]
        unit = _infer_unit(column_header, raw_value_cells)

        reported_change_by_group = _reported_change_by_identity(
            data_rows=data_rows,
            derived_rate_cols=derived_rate_cols,
            row_identities=row_identities,
            label_col=label_col,
        )

        if temporal and row_identities and len(set(aligned_identities)) > 1:
            # Time column found AND multiple distinct categories share it
            # (e.g. Region x Year retention) — split into one temporal
            # series per category rather than one series that jumbles
            # every region's years together in row order.
            groups: dict[str, list[dict[str, Any]]] = {}
            for identity, prow in zip(aligned_identities, parsed_rows):
                groups.setdefault(identity, []).append(prow)
            for identity, group_rows in groups.items():
                if len(group_rows) < 2:
                    continue
                group_temporal = all(_looks_temporal(r["label"]) for r in group_rows)
                series_list.append(
                    MetricSeries(
                        title=_compose_category_title(identity, column_header),
                        source_document=source_document,
                        unit=unit,
                        rows=group_rows,
                        calculations=_compute_calculations(group_rows) if group_temporal else {},
                        reported_change=reported_change_by_group.get(identity, []),
                        dimension_type="temporal_by_category",
                        category_value=identity or None,
                        metric_group=column_header,
                    )
                )
        elif temporal:
            # Time column found, no category split needed (no identity
            # column, or a single constant category value across the
            # whole table, e.g. Step 1's "Claims Backlog" case) — one
            # temporal series, titled from the constant category value if
            # present, else the column header.
            title = _compose_category_title(
                aligned_identities[0] if aligned_identities else "", column_header
            )
            series_list.append(
                MetricSeries(
                    title=title,
                    source_document=source_document,
                    unit=unit,
                    rows=parsed_rows,
                    calculations=_compute_calculations(parsed_rows),
                    reported_change=reported_change_by_group.get(
                        aligned_identities[0] if aligned_identities else "", []
                    ),
                    dimension_type="temporal",
                    category_value=(aligned_identities[0] if aligned_identities else None) or None,
                    metric_group=column_header,
                )
            )
        elif identity_kind == "metric_identity" and row_identities and len(set(aligned_identities)) > 1:
            # No time column, AND the identity column's values are
            # themselves distinct metric identities (e.g. "Metric":
            # "Operational Resilience Score", "Overall Risk Score") —
            # NOT instances of one shared, comparable metric. Each row is
            # its own independent, non-comparable single observation.
            # Never compute cross-sectional stats here: "highest/lowest/
            # gap" between two genuinely different metrics is exactly as
            # invalid as claiming a change between them — they don't
            # measure the same thing at all.
            for identity, prow in zip(aligned_identities, parsed_rows):
                # The value column's own header is typically generic
                # ("Value") in this shape — the score/rating language
                # lives in the metric's own name instead (e.g.
                # "Operational Resilience Score"), so _infer_unit()'s
                # header/cell check won't see it. A direct check here is
                # more targeted than widening _infer_unit()'s signature
                # for this one narrow case.
                row_unit = unit or ("score" if re.search(r"\bscore\b|\brating\b", identity, re.IGNORECASE) else "")
                series_list.append(
                    MetricSeries(
                        title=identity or column_header,
                        source_document=source_document,
                        unit=row_unit,
                        rows=[prow],
                        calculations={},
                        reported_change=reported_change_by_group.get(identity, []),
                        dimension_type="single_observation",
                        category_value=None,
                        metric_group=None,
                    )
                )
        else:
            # No time column anywhere in this table — a purely categorical
            # comparison (e.g. Channel x Premium Share). Never compute a
            # period-over-period/total-change here: categories have no
            # inherent order, so there is no "before" and "after" to diff.
            # Cross-sectional stats (highest/lowest/gap) give the report
            # writer real Verified-Calculations content instead.
            series_list.append(
                MetricSeries(
                    title=column_header,
                    source_document=source_document,
                    unit=unit,
                    rows=parsed_rows,
                    calculations=_compute_cross_sectional_stats(parsed_rows),
                    reported_change=[],
                    dimension_type="categorical",
                    category_value=None,
                    metric_group=column_header,
                )
            )

    return series_list


def _reported_change_by_identity(
    *,
    data_rows: list[list[str]],
    derived_rate_cols: list[int],
    row_identities: list[str],
    label_col: int = 0,
) -> dict[str, list[dict[str, str]]]:
    """Group each derived-rate column's raw (as-reported) values by the
    identity value of the row they belong to, so a value series can cite
    its reported change without any of it being recomputed."""

    by_group: dict[str, list[dict[str, str]]] = {}
    for rate_col in derived_rate_cols:
        for row_i, row in enumerate(data_rows):
            if len(row) <= rate_col or len(row) <= label_col:
                continue
            raw = row[rate_col].strip()
            if not raw:
                continue
            group_key = row_identities[row_i] if row_identities else ""
            by_group.setdefault(group_key, []).append(
                {"label": _normalize_temporal_label(row[label_col].strip()), "reported": raw}
            )
    return by_group


def extract_metric_tables(
    sources: list[dict[str, str]], *, max_tables: int = 6
) -> list[dict[str, Any]]:
    """Detect numeric tables in retrieved source excerpts and compute
    deterministic period-over-period / total-change metrics for each.

    Returns a list of MetricSeries dicts, deduplicated by normalized title
    + unit + granularity (keeping whichever candidate has the most rows —
    the most complete time series — since the same table often appears,
    with overlapping years, across multiple source documents), capped to
    max_tables by materiality (largest total-change first) to bound prompt
    size without letting an early-encountered, low-significance table
    crowd out a more materially important one from a later source.
    """

    candidates: list[MetricSeries] = []

    for source in sources:
        filename = str(source.get("filename") or "")
        text = str(source.get("excerpt") or "")

        for block in parse_markdown_blocks(text):
            if block.block_type != "table":
                continue
            candidates.extend(_extract_from_table(block.rows, source_document=filename))

    best_by_key: dict[tuple[str, str, str], MetricSeries] = {}
    for series in candidates:
        # Granularity is part of the key: a same-titled annual series and
        # quarterly series describe the same metric at different
        # resolutions and must never silently substitute for one another
        # (a 12-row quarterly series is not "more complete" than a 3-row
        # annual one — it's a different question).
        key = (series.title.strip().lower(), series.unit, _infer_granularity(series.rows))
        existing = best_by_key.get(key)
        if existing is None or len(series.rows) > len(existing.rows):
            best_by_key[key] = series

    ranked = sorted(best_by_key.values(), key=_materiality_score, reverse=True)
    deduped = ranked[:max_tables]
    return [series.to_dict() for series in deduped]


def _materiality_score(series: MetricSeries) -> float:
    """How significant a series' computed total change is, used to rank
    which candidates survive the max_tables cap. A series with no
    calculable change (e.g. a non-temporal category breakdown) ranks
    lowest, rather than crowding out a genuinely significant metric purely
    by virtue of having been encountered first."""

    total = series.calculations.get("total_change") if series.calculations else None
    percent = total.get("percent") if total else None
    return abs(percent) if percent is not None else -1.0


def format_metrics_for_evidence(tables: list[dict[str, Any]]) -> str:
    """Render extracted metric tables as a clearly-labeled evidence block
    for the report-writing prompt — the same "here is a distinct,
    trustworthy block of extra context" pattern already used for the
    previous-report comparison block.

    When the same metric title appears more than once — e.g. an annual
    summary and a quarterly detail sheet both kept as distinct series (see
    extract_metric_tables' granularity-aware dedup) — each occurrence is
    disambiguated with its granularity so the report writer can tell them
    apart, rather than being left to guess which same-titled figure a
    given period phrasing ("2023 to 2025") should actually cite."""

    if not tables:
        return ""

    title_counts: dict[str, int] = {}
    for table in tables:
        key = str(table.get("title") or "").strip().lower()
        title_counts[key] = title_counts.get(key, 0) + 1

    lines = [
        "\n\n### Verified Calculations (computed programmatically — do not "
        "recompute or estimate these figures, cite them exactly as given)\n"
    ]

    for table in tables:
        unit_suffix = f" ({table['unit']})" if table.get("unit") else ""
        display_title = str(table.get("title") or "")
        key = display_title.strip().lower()
        if title_counts.get(key, 0) > 1:
            granularity = _infer_granularity(table.get("rows") or [])
            if granularity != "other":
                display_title = f"{display_title} — {granularity.capitalize()}"
        unit = str(table.get("unit") or "")
        absolute_unit = "percentage points" if unit == "%" else unit

        def _absolute_label(value: float) -> str:
            return f"{value:+,} {absolute_unit}" if absolute_unit else f"{value:+,}"

        lines.append(f"**{display_title}{unit_suffix}** — source: {table['source_document']}")

        dimension_type = str(table.get("dimension_type") or "")
        if dimension_type == "categorical":
            lines.append(
                "_(categorical comparison across "
                f"{', '.join(row['label'] for row in table['rows'])} — not a time series; "
                "do not describe these values as a change/increase/decrease.)_"
            )
        elif dimension_type == "single_observation":
            lines.append(
                "_(single observation — no prior period or comparable baseline exists; "
                "describe as a fact, never as an improvement, increase, decrease, or other "
                "directional change.)_"
            )

        for row in table["rows"]:
            lines.append(f"- {row['label']}: {row['value']:,}")

        calculations = table.get("calculations") or {}
        for change in calculations.get("period_over_period", []):
            if change["percent"] is None:
                continue
            direction = "increase" if change["percent"] >= 0 else "decrease"
            lines.append(
                f"- {change['from']} → {change['to']}: "
                f"{abs(change['percent'])}% relative {direction} "
                f"({_absolute_label(change['absolute'])})"
            )

        total = calculations.get("total_change")
        if total and total["percent"] is not None:
            direction = "increase" if total["percent"] >= 0 else "decrease"
            lines.append(
                f"- {total['from']} → {total['to']} total: "
                f"{abs(total['percent'])}% relative {direction} "
                f"({_absolute_label(total['absolute'])})"
            )

        cross_sectional = calculations.get("cross_sectional")
        if cross_sectional:
            highest = cross_sectional["highest"]
            lowest = cross_sectional["lowest"]
            gap_note = f" — a gap of {_absolute_label(cross_sectional['range'])}"
            if cross_sectional.get("gap_percent") is not None:
                gap_note += f" ({cross_sectional['gap_percent']}% of the highest)"
            lines.append(
                f"- Highest: {highest['label']} at {highest['value']:,}; "
                f"Lowest: {lowest['label']} at {lowest['value']:,}{gap_note}"
            )

        reported_change = table.get("reported_change") or []
        if reported_change:
            cited = "; ".join(f"{item['label']}: {item['reported']}" for item in reported_change)
            lines.append(f"- As-reported change/rate (already a change — do not recompute): {cited}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
