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


@dataclass
class MetricSeries:
    title: str
    source_document: str
    unit: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    calculations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source_document": self.source_document,
            "unit": self.unit,
            "rows": self.rows,
            "calculations": self.calculations,
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

    series_list: list[MetricSeries] = []

    for col_index in range(1, len(header)):
        column_header = header[col_index].strip()
        if not column_header:
            continue

        parsed_rows: list[dict[str, Any]] = []
        for row in data_rows:
            if len(row) <= col_index:
                continue
            label = _normalize_temporal_label(row[0].strip())
            value = _parse_numeric_cell(row[col_index])
            if not label or value is None:
                continue
            parsed_rows.append({"label": label, "value": value})

        # Require every data row to have parsed as numeric in this column —
        # a partially-numeric column is more likely a label/notes column
        # than a real metric, and a truncated table (retrieval clipping cut
        # a row mid-way) should be skipped rather than computed from
        # incomplete data.
        if len(parsed_rows) < 2 or len(parsed_rows) != len(data_rows):
            continue

        unit = _infer_unit(column_header, [row[col_index] for row in data_rows if len(row) > col_index])
        calculations = _compute_calculations(parsed_rows) if temporal else {}

        series_list.append(
            MetricSeries(
                title=column_header,
                source_document=source_document,
                unit=unit,
                rows=parsed_rows,
                calculations=calculations,
            )
        )

    return series_list


def extract_metric_tables(
    sources: list[dict[str, str]], *, max_tables: int = 6
) -> list[dict[str, Any]]:
    """Detect numeric tables in retrieved source excerpts and compute
    deterministic period-over-period / total-change metrics for each.

    Returns a list of MetricSeries dicts, deduplicated by normalized title
    + unit (keeping whichever candidate has the most rows — the most
    complete time series — since the same table often appears, with
    overlapping years, across multiple source documents), capped to
    max_tables to bound prompt size.
    """

    candidates: list[MetricSeries] = []

    for source in sources:
        filename = str(source.get("filename") or "")
        text = str(source.get("excerpt") or "")

        for block in parse_markdown_blocks(text):
            if block.block_type != "table":
                continue
            candidates.extend(_extract_from_table(block.rows, source_document=filename))

    best_by_key: dict[tuple[str, str], MetricSeries] = {}
    for series in candidates:
        key = (series.title.strip().lower(), series.unit)
        existing = best_by_key.get(key)
        if existing is None or len(series.rows) > len(existing.rows):
            best_by_key[key] = series

    deduped = list(best_by_key.values())[:max_tables]
    return [series.to_dict() for series in deduped]


def format_metrics_for_evidence(tables: list[dict[str, Any]]) -> str:
    """Render extracted metric tables as a clearly-labeled evidence block
    for the report-writing prompt — the same "here is a distinct,
    trustworthy block of extra context" pattern already used for the
    previous-report comparison block."""

    if not tables:
        return ""

    lines = [
        "\n\n### Verified Calculations (computed programmatically — do not "
        "recompute or estimate these figures, cite them exactly as given)\n"
    ]

    for table in tables:
        unit_suffix = f" ({table['unit']})" if table.get("unit") else ""
        lines.append(f"**{table['title']}{unit_suffix}** — source: {table['source_document']}")
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

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
