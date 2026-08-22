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

# A column whose header names a grouping dimension (an "Indicator" a row
# describes, a "Region", a "Product") identifies WHAT a row's value is
# about — it is never itself a metric, and should instead become the title
# of the metric derived from a sibling value column.
_IDENTITY_COLUMN_KEYWORDS = (
    "indicator",
    "category",
    "segment",
    "product",
    "region",
    "type",
    "name",
    "label",
    "group",
    "metric",
    "class",
    "line",
)

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
    generalized beyond a fixed keyword list via a cardinality heuristic:
    a grouping dimension's values commonly repeat across rows (unlike free
    narrative/notes text, where every row tends to differ)."""

    if any(keyword in header.lower() for keyword in _IDENTITY_COLUMN_KEYWORDS):
        return True
    values = [cell.strip() for cell in raw_cells if cell.strip()]
    if len(values) < 2:
        return False
    return len(set(values)) < len(values)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source_document": self.source_document,
            "unit": self.unit,
            "rows": self.rows,
            "calculations": self.calculations,
            "reported_change": self.reported_change,
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
    }


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

    labels = [_normalize_temporal_label(row[0].strip()) for row in data_rows if row]
    temporal = labels and sum(1 for label in labels if _looks_temporal(label)) >= max(
        2, len(labels) - 1
    )

    # Pass 1: classify each non-label column. An identity column (e.g.
    # "Indicator") names what a row's value is about and becomes a title
    # source, never a metric itself. A derived-rate column (e.g.
    # "Change/Rate") describes another column's movement and must never
    # become an independent metric with its own period-over-period math
    # computed on top of already-computed percentages.
    identity_col: int | None = None
    value_cols: list[int] = []
    derived_rate_cols: list[int] = []

    for col_index in range(1, len(header)):
        column_header = header[col_index].strip()
        if not column_header:
            continue
        raw_cells = [row[col_index] for row in data_rows if len(row) > col_index]
        if len(raw_cells) != len(data_rows):
            continue

        if all(_parse_numeric_cell(cell) is not None for cell in raw_cells):
            if _is_derived_rate_column(column_header, raw_cells):
                derived_rate_cols.append(col_index)
            else:
                value_cols.append(col_index)
        elif identity_col is None and _is_identity_column(column_header, raw_cells):
            identity_col = col_index

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
            if len(row) <= col_index:
                continue
            label = _normalize_temporal_label(row[0].strip())
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
        )

        if row_identities and len(set(aligned_identities)) > 1:
            # Multiple distinct indicators share this column — split into
            # one series per indicator rather than one misleadingly-merged
            # series spanning unrelated things under a generic title.
            groups: dict[str, list[dict[str, Any]]] = {}
            for identity, prow in zip(aligned_identities, parsed_rows):
                groups.setdefault(identity, []).append(prow)
            for identity, group_rows in groups.items():
                if len(group_rows) < 2:
                    continue
                group_temporal = temporal and all(_looks_temporal(r["label"]) for r in group_rows)
                series_list.append(
                    MetricSeries(
                        title=identity or column_header,
                        source_document=source_document,
                        unit=unit,
                        rows=group_rows,
                        calculations=_compute_calculations(group_rows) if group_temporal else {},
                        reported_change=reported_change_by_group.get(identity, []),
                    )
                )
        else:
            # No identity column, or a single constant indicator value
            # across the whole table — use that value as the series title
            # instead of a generic column header like "Value".
            title = aligned_identities[0] if aligned_identities and aligned_identities[0] else column_header
            series_list.append(
                MetricSeries(
                    title=title,
                    source_document=source_document,
                    unit=unit,
                    rows=parsed_rows,
                    calculations=_compute_calculations(parsed_rows) if temporal else {},
                    reported_change=reported_change_by_group.get(
                        aligned_identities[0] if aligned_identities else "", []
                    ),
                )
            )

    return series_list


def _reported_change_by_identity(
    *,
    data_rows: list[list[str]],
    derived_rate_cols: list[int],
    row_identities: list[str],
) -> dict[str, list[dict[str, str]]]:
    """Group each derived-rate column's raw (as-reported) values by the
    identity value of the row they belong to, so a value series can cite
    its reported change without any of it being recomputed."""

    by_group: dict[str, list[dict[str, str]]] = {}
    for rate_col in derived_rate_cols:
        for row_i, row in enumerate(data_rows):
            if len(row) <= rate_col:
                continue
            raw = row[rate_col].strip()
            if not raw:
                continue
            group_key = row_identities[row_i] if row_identities else ""
            by_group.setdefault(group_key, []).append(
                {"label": _normalize_temporal_label(row[0].strip()), "reported": raw}
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
        lines.append(f"**{display_title}{unit_suffix}** — source: {table['source_document']}")
        for row in table["rows"]:
            lines.append(f"- {row['label']}: {row['value']:,}")

        calculations = table.get("calculations") or {}
        for change in calculations.get("period_over_period", []):
            if change["percent"] is None:
                continue
            direction = "increase" if change["percent"] >= 0 else "decrease"
            lines.append(
                f"- {change['from']} → {change['to']}: "
                f"{abs(change['percent'])}% {direction} "
                f"({change['absolute']:+,})"
            )

        total = calculations.get("total_change")
        if total and total["percent"] is not None:
            direction = "increase" if total["percent"] >= 0 else "decrease"
            lines.append(
                f"- {total['from']} → {total['to']} total: "
                f"{abs(total['percent'])}% {direction} "
                f"({total['absolute']:+,})"
            )

        reported_change = table.get("reported_change") or []
        if reported_change:
            cited = "; ".join(f"{item['label']}: {item['reported']}" for item in reported_change)
            lines.append(f"- As-reported change/rate (already a change — do not recompute): {cited}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
