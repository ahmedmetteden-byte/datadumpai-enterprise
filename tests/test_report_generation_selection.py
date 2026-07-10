"""Tests for report document selection helpers."""

from __future__ import annotations

from ui.report_generation import _coerce_multiselect_values


def test_coerce_multiselect_values_handles_list():
    available = ["alpha.txt", "beta.txt", "gamma.txt"]

    assert _coerce_multiselect_values(
        ["alpha.txt", "beta.txt"],
        available,
    ) == ["alpha.txt", "beta.txt"]


def test_coerce_multiselect_values_handles_single_string():
    available = ["alpha.txt", "beta.txt"]

    assert _coerce_multiselect_values("alpha.txt", available) == ["alpha.txt"]


def test_coerce_multiselect_values_does_not_iterate_string_characters():
    available = ["alpha.txt", "beta.txt"]

    assert _coerce_multiselect_values("missing.pdf", available) == []


def test_coerce_multiselect_values_filters_unknown_items():
    available = ["alpha.txt", "beta.txt"]

    assert _coerce_multiselect_values(
        ["alpha.txt", "removed.txt"],
        available,
    ) == ["alpha.txt"]
