"""Tests for AI Workspace conversational routing."""

from __future__ import annotations

from ui.ai_workspace import parse_prompt_intent


def test_parse_prompt_intent_maps_executive_report():
    report_type, instruction = parse_prompt_intent("Generate an executive report from these files.")
    assert report_type == "Executive Summary"
    assert "executive report" in instruction.lower()


def test_parse_prompt_intent_maps_me_framework():
    report_type, _ = parse_prompt_intent("Build a monitoring and evaluation framework.")
    assert report_type == "Strategic Planning Report"


def test_parse_prompt_intent_maps_compare_request():
    report_type, _ = parse_prompt_intent("Compare these two reports.")
    assert report_type == "Full Report"


def test_parse_prompt_intent_maps_kpi_extraction():
    report_type, _ = parse_prompt_intent("Extract all KPIs from these files.")
    assert report_type == "Management Report"


def test_parse_prompt_intent_returns_none_for_unknown_request():
    report_type, instruction = parse_prompt_intent("Draft a creative poem about the moon.")
    assert report_type is None
    assert instruction
