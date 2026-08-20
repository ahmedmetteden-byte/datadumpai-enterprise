"""
Tests for report_document_parser.py's SPA-format compatibility (Step G of
the Premium Report Generation Upgrade): top_risks()/top_opportunities()
must find real content in an SPA report's own top-level sections, not
only the legacy Executive Intelligence Dashboard's nested subsections.
"""

from __future__ import annotations

from services.report_document_parser import (
    is_available,
    parse_intelligence_report,
    strategic_recommendation,
    top_opportunities,
    top_risks,
)

SPA_REPORT = """
## Executive Summary
Gross premiums increased 97.4% from 2022 to 2024.

## Key Findings

### Gross Premium increased 97.4%
Detail text.
**Basis:** Calculated result
**Confidence:** High — verified calculations.
**Source:** report.xlsx

## Detailed Analysis
Growth was broad-based across the period.

## Risks & Issues
- **Rising Claims Costs:** The significant increase in Gross Claims in 2024 poses a risk to profitability.
- **Market Volatility:** Continued growth in premiums may not be sustainable if market conditions shift.

## Opportunities
- **Enhanced Claims Management:** The disparity in growth rates presents an opportunity to refine claims management processes.
- **Market Expansion:** The strong growth in premiums suggests an opportunity to explore new markets.

## Strategic Recommendations
1. **Action:** Conduct a comprehensive review of claims management processes.
   **Rationale:** The 51.3% increase in Gross Claims suggests inefficiencies.
   **Measurement:** Track the ratio of Gross Claims to Gross Premium.
2. **Action:** Explore new market segments.
   **Rationale:** The disparity in growth rates indicates untapped potential.
   **Measurement:** Evaluate new segments based on premium growth metrics.

## Conclusion
Momentum should be sustained.
"""


def test_top_risks_finds_spa_top_level_risks_section():
    parsed = parse_intelligence_report(SPA_REPORT, source_documents=["report.xlsx"])
    risks = top_risks(parsed)

    assert len(risks) == 2
    assert risks[0]["title"] == "Rising Claims Costs"
    assert "profitability" in risks[0]["detail"]
    assert risks[1]["title"] == "Market Volatility"


def test_top_opportunities_finds_spa_top_level_opportunities_section():
    parsed = parse_intelligence_report(SPA_REPORT, source_documents=["report.xlsx"])
    opportunities = top_opportunities(parsed)

    assert len(opportunities) == 2
    assert "Enhanced Claims Management" in opportunities[0]
    assert "Market Expansion" in opportunities[1]


def test_strategic_recommendation_extracts_action_clause_from_spa_format():
    parsed = parse_intelligence_report(SPA_REPORT, source_documents=["report.xlsx"])
    recommendation = strategic_recommendation(parsed)

    assert "Conduct a comprehensive review of claims management processes" in recommendation
    assert "Rationale" not in recommendation  # only the Action clause, not the whole item


def test_top_risks_returns_empty_for_report_with_no_risks_section():
    minimal = "## Executive Summary\nNo risks or opportunities sections here.\n"
    parsed = parse_intelligence_report(minimal)
    assert top_risks(parsed) == []
    assert top_opportunities(parsed) == []


def test_dashboard_nested_risks_still_take_priority_over_spa_fallback():
    """Legacy intelligence-format reports must keep working exactly as
    before — the SPA fallback only kicks in when no dashboard section (or
    an empty one) exists."""

    legacy = """
## Executive Intelligence Dashboard

### Top Risks
- 🔴 **Claims** — Settlement delays continue

## Risks & Issues
- **Should not be used:** This top-level section must be ignored since the dashboard already has risks.
"""
    parsed = parse_intelligence_report(legacy)
    risks = top_risks(parsed)

    assert len(risks) == 1
    assert risks[0]["title"] == "Claims"


def test_top_opportunities_falls_back_to_prose_sentences_when_not_bulleted():
    """Report Output Quality Upgrade Step B: the LLM sometimes writes
    Opportunities as flowing prose instead of markdown bullets. Before this
    fix, top_opportunities() found zero bullets and the dashboard claimed
    'no opportunities identified' while the body genuinely discussed real
    ones — the exact contradiction seen in a real reviewed report."""

    report = """
## Executive Summary
Gross premiums increased 97.4% from 2022 to 2024.

## Opportunities
The sustained growth in premiums and claims presents opportunities for insurers to
enhance their product offerings and expand market reach. Additionally, the
integration of technology can further streamline operations and improve customer
engagement.

## Conclusion
Momentum should be sustained.
"""
    parsed = parse_intelligence_report(report)
    opportunities = top_opportunities(parsed)

    assert len(opportunities) == 2
    assert "enhance their product offerings" in opportunities[0]
    assert "integration of technology" in opportunities[1]


def test_top_risks_prose_fallback_does_not_fabricate_a_risk_from_a_negative_statement():
    """A genuine 'no risks found' prose sentence must not be turned into a
    fake single risk item — the fallback only kicks in for real content."""

    report = """
## Executive Summary
Gross premiums increased 97.4% from 2022 to 2024.

## Risks & Issues
No material risks or open problems were identified in the evidence provided, though
continued monitoring of claims trends is advised.

## Conclusion
Momentum should be sustained.
"""
    parsed = parse_intelligence_report(report)

    assert top_risks(parsed) == []


def test_is_available_rejects_placeholder_values():
    assert is_available("—") is False
    assert is_available("") is False
    assert is_available(None) is False
    assert is_available("High") is True
    assert is_available(42) is True
